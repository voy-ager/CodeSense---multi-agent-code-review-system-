# agent/scanners.py
#
# Deterministic checks that run alongside the LLM agents. These target problems
# LLM reviewers are bad at or can be talked out of:
#   - leaked secrets (AI-assisted commits leak ~2x more, GitGuardian 2026)
#   - hallucinated / brand-new dependencies (slopsquatting)
#   - prompt injection aimed at AI reviewers, incl. invisible Unicode
# Rules can't be prompt-injected, so these findings hold even if the LLM is fooled.

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote

import requests

REGISTRY_TIMEOUT = 5          # seconds per registry lookup
MAX_PACKAGE_LOOKUPS = 25      # bounds review time on huge dependency diffs
NEW_PACKAGE_DAYS = 30

# ── Diff parsing ──────────────────────────────────────────────────────────────
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def diff_lines(diff: str):
    """Yield (file, line_number, text, kind) for every line the LLM will see.
    kind is "+" (added), "-" (removed), " " (context) or "path" (a file name).
    Removed lines carry their old line number; everything else the new one."""
    file, old_no, new_no, in_hunk = "", 0, 0, False
    for raw in diff.splitlines():
        if raw.startswith("diff --git"):
            in_hunk = False
        elif raw.startswith("@@"):
            m = HUNK_RE.match(raw)
            old_no, new_no = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
            in_hunk = True
        elif not in_hunk:
            # Outside a hunk "+++ " is the file header. Inside one it is an added line whose
            # content starts with "++ " — it must not rename the file or skip scanning.
            if raw.startswith("+++ "):
                file = raw[6:] if raw.startswith("+++ b/") else raw[4:]
                yield file, 0, file, "path"
        elif raw.startswith("+"):
            yield file, new_no, raw[1:], "+"
            new_no += 1
        elif raw.startswith("-"):
            yield file, old_no, raw[1:], "-"
            old_no += 1
        elif not raw.startswith("\\"):
            yield file, new_no, raw[1:], " "
            old_no += 1
            new_no += 1


def added_lines(diff: str):
    """Yield (file, new_line_number, text) for every added line."""
    for file, line, text, kind in diff_lines(diff):
        if kind == "+":
            yield file, line, text


def _finding(severity, file, line, category, issue, fix):
    return {"severity": severity, "file": file, "line": line, "category": category,
            "issue": issue, "fix": fix, "agent": "security", "source": "static"}


# ── Secrets ───────────────────────────────────────────────────────────────────
SECRET_PATTERNS = [
    ("AWS access key",       re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token",         re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b")),
    ("Anthropic API key",    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key",       re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("Groq API key",         re.compile(r"\bgsk_[A-Za-z0-9]{40,}\b")),
    ("Google API key",       re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token",          re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Stripe live key",      re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}")),
    ("Private key",          re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("JSON Web Token",       re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]
# Keyword may sit inside a longer identifier: DB_PASSWORD, SECRET_KEY, STRIPE_API_KEY.
_SENSITIVE_NAME = r"([A-Za-z0-9_]*?(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)[A-Za-z0-9_]*)"
GENERIC_SECRET_RE = re.compile(_SENSITIVE_NAME + r"""["']?\s*[:=]\s*["']([^"'\s]{8,})["']""", re.I)
# .env / YAML / INI values are usually unquoted.
UNQUOTED_SECRET_RE = re.compile(r"^\s*(?:export\s+)?" + _SENSITIVE_NAME + r"""\s*[:=]\s*([^\s"'#]{8,})\s*(?:#.*)?$""", re.I)
UNQUOTED_FILES_RE = re.compile(r"(?:^|/)(?:\.env[^/]*|[^/]+\.(?:env|ya?ml|ini|cfg|conf|properties|toml))$", re.I)
PLACEHOLDER_RE = re.compile(r"(?i)example|your[_-]|placeholder|changeme|dummy|xxx|<|\$\{|\{\{|\$[A-Z_]|redacted|\*\*\*|os\.environ|process\.env|getenv")
# GhostCommit-style exfiltration: a secret written as a list of character codes (decimal or hex).
INT_LIST_RE = re.compile(r"[\[(]\s*((?:(?:0x[0-9a-fA-F]{2}|\d{2,3})\s*,\s*){15,}(?:0x[0-9a-fA-F]{2}|\d{2,3}))\s*,?\s*[\])]")


def _redact(value: str) -> str:
    return value[:4] + "…" + f"({len(value)} chars)"


def _match_secret(text: str):
    for name, pattern in SECRET_PATTERNS:
        m = pattern.search(text)
        if m:
            return name, m.group(0)
    return None


def _looks_like_secret(value: str) -> bool:
    # Plain words ("Authorization", "password123" excluded only if purely letters) are rarely real secrets.
    return not PLACEHOLDER_RE.search(value) and not value.isalpha()


def _decoded_int_lists(text: str):
    for nums in INT_LIST_RE.findall(text):
        codes = [int(n, 16) if n.lower().startswith("0x") else int(n) for n in re.findall(r"0x[0-9a-fA-F]{2}|\d+", nums)]
        if all(32 <= c < 127 for c in codes):
            yield "".join(map(chr, codes))


def scan_secrets(diff: str) -> list[dict]:
    findings = []
    for file, line, text in added_lines(diff):
        hit = _match_secret(text)
        if hit:
            findings.append(_finding(
                "critical", file, line, "Hardcoded Secret",
                f"{hit[0]} committed in plain text ({_redact(hit[1])}).",
                "Revoke and rotate this credential now, then load it from an environment variable or secret manager.",
            ))
            continue

        encoded = next((h for s in _decoded_int_lists(text) if (h := _match_secret(s))), None)
        if encoded:
            findings.append(_finding(
                "critical", file, line, "Encoded Secret",
                f"Character-code list decodes to a {encoded[0]} — a known technique for hiding secrets from scanners.",
                "Remove the encoded value, rotate the credential, and audit how it was introduced.",
            ))
            continue

        m = GENERIC_SECRET_RE.search(text)
        if not m and UNQUOTED_FILES_RE.search(file):
            m = UNQUOTED_SECRET_RE.match(text)
        if m and _looks_like_secret(m.group(2)):
            findings.append(_finding(
                "high", file, line, "Hardcoded Secret",
                f"Literal value assigned to '{m.group(1)}' ({_redact(m.group(2))}).",
                "Read this value from configuration or a secret manager instead of source code.",
            ))
    return findings


# ── Prompt injection / invisible characters ──────────────────────────────────
INJECTION_RE = re.compile(
    r"(?i)("
    r"ignore\s+(?:all\s+|any\s+)?(?:of\s+)?(?:the\s+|your\s+)?(?:previous|prior|above|earlier|preceding)\s+(?:instructions|prompts?|rules|directions)"
    r"|disregard\s+(?:all\s+|the\s+|any\s+)?(?:previous|prior|above|system)\s+(?:instructions|prompts?|rules)"
    r"|forget\s+(?:everything|all)\s+(?:above|before|previous|you\s+were\s+told)"
    r"|you\s+are\s+now\s+(?:an?\s+|the\s+)?(?:ai|assistant|(?:code\s+)?reviewer|language\s+model|unrestricted|jailbroken|dan)\b"
    r"|(?:new|override|updated)\s+system\s+prompt"
    r"|\b(?:ai|llm|automated)\s+(?:code\s+)?review(?:er|ers)?\b.{0,40}\b(?:approve|ignore|skip|must\s+not|do\s+not\s+(?:flag|report))"
    r"|(?:report|return|output)\s+(?:no|zero)\s+(?:issues|findings|problems|vulnerabilities)"
    r"|return\s+(?:an\s+)?empty\s+(?:json\s+)?(?:array|list)"
    r")"
)

# Invisible / format characters that make code read differently than it runs:
# zero-width, bidi controls (Trojan Source), invisible math operators, Hangul fillers,
# soft hyphen, tag characters (ASCII smuggling) and supplementary variation selectors
# and private-use characters (GlassWorm-style payloads). Built from code points so
# this source file itself contains no invisible characters.
_HIDDEN_RANGES = [
    (0x00AD, 0x00AD), (0x061C, 0x061C), (0x115F, 0x1160), (0x180E, 0x180E),
    (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x2064), (0x2066, 0x2069),
    (0x3164, 0x3164), (0xE000, 0xF8FF), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0),
    (0xE0000, 0xE007F), (0xE0100, 0xE01EF),
]
HIDDEN_CHAR_RE = re.compile("[" + "".join(f"{re.escape(chr(a))}-{re.escape(chr(b))}" for a, b in _HIDDEN_RANGES) + "]")
# U+FE00-FE0F: one selector after an emoji is normal; a run of them is an encoded payload.
VARIATION_RUN_RE = re.compile("[" + re.escape(chr(0xFE00)) + "-" + re.escape(chr(0xFE0F)) + "]{2,}")


def _normalise(text: str) -> str:
    # NFKC folds lookalikes such as non-breaking or full-width spaces before matching.
    return unicodedata.normalize("NFKC", text)


def scan_prompt_injection(diff: str) -> list[dict]:
    """Scans every line the LLM sees — added, removed, context and file names."""
    findings = []
    for file, line, text, kind in diff_lines(diff):
        hidden = HIDDEN_CHAR_RE.findall(text) + VARIATION_RUN_RE.findall(text)
        if hidden and kind in ("+", "path"):
            codes = ", ".join(sorted({f"U+{ord(c):04X}" for c in "".join(hidden)}))
            findings.append(_finding(
                "critical", file, line, "Hidden Unicode",
                f"Invisible or bidirectional control characters ({codes}) can hide code or instructions from human reviewers.",
                "Remove the hidden characters; reject them in CI with a Unicode lint.",
            ))
        m = INJECTION_RE.search(_normalise(text))
        if m:
            where = {"+": "", "-": " (in a removed line)", " ": " (in unchanged context)", "path": " (in a file name)"}[kind]
            findings.append(_finding(
                "high", file, line, "Prompt Injection",
                f"Text that tries to instruct an AI reviewer{where}: \"{m.group(0)[:80]}\".",
                "Remove it. Treat any instruction aimed at automated reviewers as a red flag in this PR.",
            ))
    return findings


# ── Dependencies (slopsquatting) ─────────────────────────────────────────────
PY_NAME_RE  = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]{0,99})\s*(?:\[[^\]]*\])?\s*(?:[=<>!~;@#(,]|$)")
PYPROJECT_DEP_RE = re.compile(r"""^\s*["']([A-Za-z0-9][A-Za-z0-9._-]{0,99})\s*(?:\[[^\]]*\])?\s*(?:[=<>!~;@(]|["'])""")
NPM_NAME_RE = re.compile(r"^(?:@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]{0,213}$")
NPM_DEP_RE  = re.compile(r'^\s*"([^"]+)"\s*:\s*"(npm:(@?[^"@]+)@[^"]*|(?:[\^~<>=*]|\d)[^"]*|latest|next)"')
NPM_SECTION_RE = re.compile(r'"([^"]+)"\s*:\s*\{')
NPM_DEP_SECTIONS = {"dependencies", "devDependencies", "peerDependencies", "optionalDependencies"}
# package.json keys that look like "name": "version" but aren't dependencies.
NPM_NON_DEP_KEYS = {"version", "node", "npm", "yarn", "pnpm", "bun", "vscode", "name", "main", "types", "license"}


def _is_requirements_file(path: str) -> bool:
    base = path.rsplit("/", 1)[-1].lower()
    return base.endswith(".txt") and (base.startswith("requirements") or "/requirements/" in f"/{path.lower()}")


def _added_dependencies(diff: str) -> list[tuple[str, str, int, str]]:
    """Return (ecosystem, name, line, file) for every package added in a manifest."""
    deps, in_npm_section = [], None
    for file, line, text, kind in diff_lines(diff):
        base = file.rsplit("/", 1)[-1].lower()
        if kind == "path":
            in_npm_section = None
            continue
        if base == "package.json":
            section = NPM_SECTION_RE.search(text)
            if section:
                in_npm_section = section.group(1) in NPM_DEP_SECTIONS
            elif text.strip().startswith("}"):
                in_npm_section = False
        if kind != "+":
            continue
        stripped = text.strip()
        if _is_requirements_file(file):
            if stripped and not stripped.startswith(("#", "-", "git+", "http")):
                m = PY_NAME_RE.match(stripped)
                if m:
                    deps.append(("pypi", m.group(1), line, file))
        elif base == "pyproject.toml":
            m = PYPROJECT_DEP_RE.match(stripped)
            if m:
                deps.append(("pypi", m.group(1), line, file))
        elif base == "package.json" and in_npm_section is not False:
            m = NPM_DEP_RE.match(text)
            if m:
                name = m.group(3) or m.group(1)   # "alias": "npm:real-name@1.0" installs real-name
                if name not in NPM_NON_DEP_KEYS and NPM_NAME_RE.match(name):
                    deps.append(("npm", name, line, file))
    return deps


def _registry_lookup(ecosystem: str, name: str) -> tuple[str, datetime | None] | None:
    """Return ("missing", None), ("ok", created_at) or None if the registry couldn't be reached."""
    if ecosystem == "pypi":
        url = f"https://pypi.org/pypi/{quote(name, safe='')}/json"
    else:
        url = f"https://registry.npmjs.org/{quote(name, safe='@')}"
    try:
        r = requests.get(url, timeout=REGISTRY_TIMEOUT, headers={"Accept": "application/json"})
    except requests.RequestException:
        return None
    if r.status_code == 404:
        return "missing", None
    if not r.ok:
        return None
    try:
        data = r.json()
        if ecosystem == "pypi":
            uploads = [f["upload_time_iso_8601"] for files in data.get("releases", {}).values() for f in files]
            created = min(uploads) if uploads else None
        else:
            created = data.get("time", {}).get("created")
        return "ok", datetime.fromisoformat(created.replace("Z", "+00:00")) if created else None
    except (ValueError, KeyError, AttributeError, TypeError, json.JSONDecodeError):
        return None


def scan_dependencies(diff: str) -> list[dict]:
    all_deps = _added_dependencies(diff)
    deps = all_deps[:MAX_PACKAGE_LOOKUPS]
    if not deps:
        return []
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda d: _registry_lookup(d[0], d[1]), deps))

    findings, unverified, now = [], [], datetime.now(timezone.utc)
    for (eco, name, line, file), result in zip(deps, results):
        registry = "PyPI" if eco == "pypi" else "npm"
        if result is None:
            unverified.append(name)
            continue
        status, created = result
        if status == "missing":
            findings.append(_finding(
                "critical", file, line, "Non-existent Package",
                f"'{name}' does not exist on {registry} — likely an AI-hallucinated dependency (slopsquatting risk).",
                "Remove it or replace it with the intended package; never register or install unverified names.",
            ))
        elif created and (now - created).days < NEW_PACKAGE_DAYS:
            findings.append(_finding(
                "high", file, line, "New Package",
                f"'{name}' was first published to {registry} {(now - created).days} day(s) ago.",
                "Verify the maintainer and source before depending on it; brand-new packages are a common supply-chain vector.",
            ))

    # Never let "not checked" read as "checked and clean".
    skipped = [d[1] for d in all_deps[MAX_PACKAGE_LOOKUPS:]] + unverified
    if skipped:
        findings.append(_finding(
            "medium", deps[0][3], 0, "Dependency Check Incomplete",
            f"{len(skipped)} added package(s) could not be verified against the registry: {', '.join(skipped[:10])}"
            + ("…" if len(skipped) > 10 else "") + ".",
            "Verify these packages manually before merging.",
        ))
    return findings


def run_static_scans(diff: str) -> list[dict]:
    return scan_secrets(diff) + scan_prompt_injection(diff) + scan_dependencies(diff)
