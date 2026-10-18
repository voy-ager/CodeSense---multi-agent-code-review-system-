# agent/state.py

import operator
from typing import Annotated, TypedDict

class GraphState(TypedDict):
    """
    The shared whiteboard for all nodes in the graph.

    Every node receives the full state and returns a dict
    of only the keys it wants to update. LangGraph merges
    those updates automatically — nodes never overwrite
    each other's keys.
    """

    # ── Input ─────────────────────────────────────────
    pr_url: str
    # The GitHub PR URL submitted by the user.
    # Example: "https://github.com/owner/repo/pull/42"

    raw_diff: str
    # The raw unified diff text fetched from GitHub.
    # Set by ingest_diff. Read by all four agents.
    # Looks like:
    #   diff --git a/auth.py b/auth.py
    #   -  password = request.args["password"]
    #   +  password = request.form.get("password", "")

    pr_metadata: dict
    # Title, author, description, file list — from GitHub API.
    # Gives agents context beyond just the raw diff lines.

    # ── Agent outputs ──────────────────────────────────
    security_findings: list
    # Written by security_agent. Each finding looks like:
    # {
    #   "severity": "critical",
    #   "line": 42,
    #   "file": "auth.py",
    #   "issue": "SQL injection via string concatenation",
    #   "fix": "Use parameterized queries: db.execute(query, [user_id])"
    # }

    perf_findings: list
    # Written by perf_agent. Same structure as above.

    test_findings: list
    # Written by test_agent. Same structure as above.

    style_findings: list
    # Written by style_agent. Same structure as above.

    # ── Output ────────────────────────────────────────
    final_report: dict
    # Written by synthesize. The merged, ranked, deduplicated
    # report that gets sent back to the user.

    # ── Housekeeping ──────────────────────────────────
    failed_agents: Annotated[list, operator.add]
    # Names of agents whose LLM call or JSON parse failed.
    # operator.add lets the 4 parallel agents append without conflicting.

    error: str
    # Set by any node that encounters an unrecoverable error.
    # The conditional edge checks this and routes to END early.