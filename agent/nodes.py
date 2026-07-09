# agent/nodes.py

import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from agent.state import GraphState

load_dotenv()

# Load LLM once at module level — not inside each function.
# GPT-4o-mini is fast, cheap, and more than capable for code review.
# If you don't have OpenAI billing, swap to Groq:
#   from langchain_groq import ChatGroq
#   llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)


# ── Shared helper ─────────────────────────────────────────────────────────────
def call_agent(prompt: str, agent_name: str) -> list:
    """
    Call the LLM with a prompt and parse the JSON response.
    Returns a list of finding dicts.

    Every agent uses this same pattern:
    1. Send the diff + instructions to the LLM
    2. LLM returns structured JSON findings
    3. We parse and return the list

    Using a shared helper means all 4 agents have identical
    error handling — if any one fails, it returns an empty
    list rather than crashing the whole graph.
    """
    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()

        # Strip markdown code fences if LLM wraps output in ```json ... ```
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        findings = json.loads(raw)

        # Ensure we always return a list — LLM sometimes returns a dict
        if isinstance(findings, dict):
            findings = [findings]

        print(f"[{agent_name}] Found {len(findings)} issue(s)")
        return findings

    except json.JSONDecodeError:
        print(f"[{agent_name}] JSON parse failed — returning empty findings")
        return []
    except Exception as e:
        print(f"[{agent_name}] Error: {e}")
        return []


# ── Node 1: Ingest diff ───────────────────────────────────────────────────────
def ingest_diff(state: GraphState) -> dict:
    """
    Fetches the PR diff from GitHub and validates it.
    This is the only node that makes external API calls.
    All agents downstream work from state["raw_diff"] only.
    """
    from tools.github import fetch_pr_diff

    print(f"\n[ingest_diff] Fetching diff from: {state['pr_url']}")

    try:
        raw_diff, metadata = fetch_pr_diff(state["pr_url"])
    except ValueError as e:
        return {"error": str(e)}

    print(f"[ingest_diff] Fetched {len(raw_diff)} chars")
    print(f"[ingest_diff] PR: '{metadata['title']}' by {metadata['author']}")
    print(f"[ingest_diff] {metadata['files_changed']} files, "
          f"+{metadata['additions']} -{metadata['deletions']}")

    return {
        "raw_diff":          raw_diff,
        "pr_metadata":       metadata,
        "retry_count":       0,
        "error":             "",
        "security_findings": [],
        "perf_findings":     [],
        "test_findings":     [],
        "style_findings":    [],
    }


# ── Node 2: Security agent ────────────────────────────────────────────────────
def security_agent(state: GraphState) -> dict:
    """
    Scans the diff for security vulnerabilities.

    Focuses on OWASP Top 10 patterns:
    - SQL injection, XSS, hardcoded secrets
    - Missing authentication/authorization checks
    - Insecure deserialization, path traversal
    - Use of dangerous functions (eval, exec, pickle.loads)

    Why a separate security agent? Security issues have different
    severity semantics than style issues — a critical SQL injection
    should always appear first regardless of line order.
    """
    print("\n[security_agent] Analyzing for security vulnerabilities...")

    diff = state["raw_diff"]

    prompt = f"""You are a security code reviewer specializing in OWASP Top 10 vulnerabilities.

Analyze this git diff for security issues. Look for:
- SQL injection (string concatenation in queries)
- XSS (unsanitized user input in HTML output)
- Hardcoded secrets, API keys, passwords, or tokens
- Missing authentication or authorization checks
- Use of dangerous functions: eval(), exec(), pickle.loads(), deserialize()
- Path traversal vulnerabilities
- Insecure direct object references
- Command injection
- Insecure cryptography (MD5, SHA1 for passwords, weak random)

GIT DIFF:
{diff}

Return a JSON array of findings. Each finding must have exactly these fields:
- "severity": one of "critical", "high", "medium", "low"
- "file": filename from the diff (e.g. "src/auth.js")
- "line": approximate line number (integer, use 0 if unclear)
- "issue": one sentence describing the vulnerability
- "fix": one concrete sentence describing how to fix it
- "category": the vulnerability type (e.g. "SQL Injection", "XSS", "Hardcoded Secret")

If no security issues are found, return an empty array: []
Return ONLY the JSON array. No explanation, no markdown, no backticks."""

    findings = call_agent(prompt, "security_agent")

    # Tag each finding with its source agent for the synthesizer
    for f in findings:
        f["agent"] = "security"

    return {"security_findings": findings}


# ── Node 3: Performance agent ─────────────────────────────────────────────────
def perf_agent(state: GraphState) -> dict:
    """
    Scans the diff for performance anti-patterns.

    Focuses on algorithmic complexity and common runtime issues:
    - O(n²) nested loops that could be O(n) with a set/map
    - N+1 query patterns (database calls inside loops)
    - Unnecessary re-computation (missing memoization)
    - Synchronous blocking calls in async contexts
    - Large object copies where references would suffice
    - Missing indexes implied by query patterns

    Performance issues are often invisible until production scale,
    which is exactly when they become expensive to fix.
    """
    print("\n[perf_agent] Analyzing for performance issues...")

    diff = state["raw_diff"]

    prompt = f"""You are a performance-focused code reviewer.

Analyze this git diff for performance anti-patterns. Look for:
- O(n²) or worse algorithms where a more efficient approach exists
- Database queries inside loops (N+1 query problem)
- Unnecessary re-computation that could be cached or memoized
- Large data copies where references or generators would be more efficient
- Blocking synchronous operations in async/concurrent code
- Missing early returns that cause unnecessary computation
- Repeated string concatenation instead of join() or StringBuilder
- Creating objects in tight loops that could be pre-allocated

GIT DIFF:
{diff}

Return a JSON array of findings. Each finding must have exactly these fields:
- "severity": one of "critical", "high", "medium", "low"
- "file": filename from the diff
- "line": approximate line number (integer, use 0 if unclear)
- "issue": one sentence describing the performance problem
- "fix": one concrete sentence describing the optimization
- "category": the type (e.g. "N+1 Query", "O(n²) Algorithm", "Unnecessary Copy")

If no performance issues are found, return an empty array: []
Return ONLY the JSON array. No explanation, no markdown, no backticks."""

    findings = call_agent(prompt, "perf_agent")

    for f in findings:
        f["agent"] = "performance"

    return {"perf_findings": findings}


# ── Node 4: Test coverage agent ───────────────────────────────────────────────
def test_agent(state: GraphState) -> dict:
    """
    Identifies untested code paths in the diff.

    Rather than measuring coverage percentages, this agent
    looks at what NEW code was added and whether corresponding
    tests were added or are obviously missing.

    It also checks for test quality issues — tests that can't
    fail, tests that don't assert anything, or tests that only
    test the happy path without edge cases.
    """
    print("\n[test_agent] Analyzing test coverage...")

    diff = state["raw_diff"]

    prompt = f"""You are a test coverage reviewer.

Analyze this git diff and identify missing or inadequate test coverage. Look for:
- New functions or methods added without corresponding test cases
- New branches (if/else, try/catch, switch) not covered by tests
- Edge cases that are obviously missing: empty inputs, null/None values, 
  boundary values, negative numbers, empty collections
- Error paths that have no test coverage
- Tests that exist but cannot fail (always-true assertions)
- Tests that don't actually assert anything meaningful
- Happy-path-only tests missing failure scenarios

GIT DIFF:
{diff}

Return a JSON array of findings. Each finding must have exactly these fields:
- "severity": one of "critical", "high", "medium", "low"  
- "file": filename from the diff
- "line": approximate line number (integer, use 0 if unclear)
- "issue": one sentence describing what is not tested
- "fix": one concrete sentence suggesting what test to add
- "category": e.g. "Missing Test", "Missing Edge Case", "Untested Error Path"

If test coverage looks adequate, return an empty array: []
Return ONLY the JSON array. No explanation, no markdown, no backticks."""

    findings = call_agent(prompt, "test_agent")

    for f in findings:
        f["agent"] = "testing"

    return {"test_findings": findings}


# ── Node 5: Style agent ───────────────────────────────────────────────────────
def style_agent(state: GraphState) -> dict:
    """
    Reviews code style, naming, and maintainability.

    This agent catches the issues that make code hard to read
    and maintain over time — not bugs, but the things that slow
    down every engineer who touches the code in the future.

    Deliberately kept at lower severity than security/perf
    since style issues rarely block production but do compound
    into technical debt.
    """
    print("\n[style_agent] Analyzing style and maintainability...")

    diff = state["raw_diff"]

    prompt = f"""You are a code style and maintainability reviewer.

Analyze this git diff for style and maintainability issues. Look for:
- Functions longer than 30 lines that should be broken down
- Misleading variable or function names (name doesn't match behavior)
- Missing or inadequate comments on complex logic
- Deeply nested code (more than 3 levels) that could be flattened
- Magic numbers or strings that should be named constants
- Duplicated code that should be extracted into a shared function
- Dead code (unreachable branches, unused variables/imports)
- Inconsistent naming conventions within the same file
- Boolean parameters that make call sites confusing (use named enums)
- TODO/FIXME comments left in production code

GIT DIFF:
{diff}

Return a JSON array of findings. Each finding must have exactly these fields:
- "severity": one of "critical", "high", "medium", "low"
- "file": filename from the diff
- "line": approximate line number (integer, use 0 if unclear)
- "issue": one sentence describing the style problem
- "fix": one concrete sentence describing the improvement
- "category": e.g. "Naming", "Magic Number", "Dead Code", "Long Function"

If style looks good, return an empty array: []
Return ONLY the JSON array. No explanation, no markdown, no backticks."""

    findings = call_agent(prompt, "style_agent")

    for f in findings:
        f["agent"] = "style"

    return {"style_findings": findings}


# ── Node 6: Synthesize ────────────────────────────────────────────────────────
def synthesize(state: GraphState) -> dict:
    """
    Merges all agent findings into a final ranked report.

    LangGraph guarantees this node only runs after ALL four
    parallel agents have completed — the fan-in ensures we
    always have the complete picture before synthesizing.

    Findings are sorted by severity so critical issues always
    appear first in the report, regardless of which agent found them.
    """
    print("\n[synthesize] Merging findings from all agents...")

    all_findings = (
        state.get("security_findings", []) +
        state.get("perf_findings",     []) +
        state.get("test_findings",     []) +
        state.get("style_findings",    [])
    )

    # Sort by severity: critical → high → medium → low
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_findings = sorted(
        all_findings,
        key=lambda x: severity_order.get(x.get("severity", "low"), 3)
    )

    # Count by severity for the summary
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in sorted_findings:
        sev = f.get("severity", "low")
        if sev in counts:
            counts[sev] += 1

    report = {
        "pr_url":         state["pr_url"],
        "pr_title":       state.get("pr_metadata", {}).get("title", ""),
        "author":         state.get("pr_metadata", {}).get("author", ""),
        "total_findings": len(sorted_findings),
        "by_severity":    counts,
        "by_agent": {
            "security":    len(state.get("security_findings", [])),
            "performance": len(state.get("perf_findings",     [])),
            "testing":     len(state.get("test_findings",     [])),
            "style":       len(state.get("style_findings",    [])),
        },
        "findings": sorted_findings,
        "summary": (
            f"Found {len(sorted_findings)} issue(s): "
            f"{counts['critical']} critical, {counts['high']} high, "
            f"{counts['medium']} medium, {counts['low']} low."
        ),
    }

    print(f"[synthesize] Report complete. {len(sorted_findings)} total findings.")
    print(f"[synthesize] {counts}")
    return {"final_report": report}