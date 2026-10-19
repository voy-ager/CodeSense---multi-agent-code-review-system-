# tools/github.py

import logging
import re
import requests
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GITHUB_TIMEOUT = 15  # seconds
MAX_DIFF_BYTES = 2_000_000

# Owner: GitHub username rules. Repo: GitHub repo-name charset, but never "." or "..",
# since both are interpolated into the api.github.com path along with our token.
# Accepts the /files, /commits, /checks tabs and a trailing ?query or #fragment.
PR_URL_RE = re.compile(
    r"^https://github\.com/"
    r"([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"((?!\.\.?/)[A-Za-z0-9._-]{1,100})/"
    r"pull/(\d{1,10})"
    r"(?:/(?:files|checks|commits(?:/[0-9a-f]{7,40})?))?/?(?:[?#].*)?$"
)


def parse_pr_url(pr_url: str) -> tuple[str, str, str] | None:
    """Return (owner, repo, pr_number) for a valid PR URL, else None."""
    match = PR_URL_RE.match(pr_url.strip())
    return match.groups() if match else None


def canonical_pr_url(pr_url: str) -> str | None:
    """https://github.com/o/r/pull/1/files?x → https://github.com/o/r/pull/1 (one cache key per PR)."""
    parsed = parse_pr_url(pr_url)
    if not parsed:
        return None
    owner, repo, num = parsed
    return f"https://github.com/{owner}/{repo}/pull/{int(num)}"   # pull/01 and pull/1 are the same PR


def fetch_head_sha(pr_url: str) -> str | None:
    """The PR's latest commit SHA, used to key the review cache so a new push
    never gets a stale review. None on any failure (caller just skips the cache)."""
    parsed = parse_pr_url(pr_url)
    if not parsed:
        return None
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        r = requests.get("https://api.github.com/repos/{}/{}/pulls/{}".format(*parsed),
                         headers=headers, timeout=GITHUB_TIMEOUT)
        return r.json().get("head", {}).get("sha") or None if r.ok else None
    except (requests.RequestException, ValueError):
        return None


def fetch_pr_diff(pr_url: str) -> tuple[str, dict]:
    """
    Given a GitHub PR URL, fetch:
      1. The raw unified diff (what the agents analyze)
      2. PR metadata (title, author, description, file list)

    Returns a tuple: (raw_diff, metadata)
    Raises ValueError if the URL is invalid or the API call fails.
    """

    # ── Parse the URL ─────────────────────────────────────────────
    # Input:  "https://github.com/facebook/react/pull/12345"
    # We need: owner="facebook", repo="react", number="12345"
    parsed = parse_pr_url(pr_url)
    if not parsed:
        raise ValueError(f"Invalid GitHub PR URL: {pr_url}")
    owner, repo, pr_num = parsed

    token = os.getenv("GITHUB_TOKEN", "")
    headers_json = {
        "Authorization": f"token {token}" if token else "",
        "Accept": "application/vnd.github.v3+json",
    }
    headers_diff = {
        "Authorization": f"token {token}" if token else "",
        # This Accept header tells GitHub to return the raw diff format
        # instead of JSON. Same endpoint, different response format.
        "Accept": "application/vnd.github.v3.diff",
    }

    base_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}"

    # ── Fetch metadata (JSON) ─────────────────────────────────────
    # Timeouts stop a slow GitHub response from hanging the request forever.
    try:
        meta_response = requests.get(base_url, headers=headers_json, timeout=GITHUB_TIMEOUT)
    except requests.RequestException as e:
        logger.warning("GitHub request failed: %s", e)   # details stay in the server log
        raise ValueError("Could not reach GitHub — please try again")
    if meta_response.status_code == 404:
        raise ValueError(f"PR not found: {pr_url}")
    if meta_response.status_code in (403, 429) and meta_response.headers.get("X-RateLimit-Remaining") == "0":
        raise ValueError("GitHub API rate limit reached — try again later (a GITHUB_TOKEN raises the limit)")
    if meta_response.status_code == 401:
        raise ValueError("GitHub token invalid or missing")
    if not meta_response.ok:
        raise ValueError(f"GitHub API error: {meta_response.status_code}")

    meta_json = meta_response.json()
    metadata = {
        "title":       meta_json.get("title", ""),
        "author":      meta_json.get("user", {}).get("login", ""),
        "description": meta_json.get("body", "") or "",
        "base_branch": meta_json.get("base", {}).get("ref", ""),
        "files_changed": meta_json.get("changed_files", 0),
        "additions":   meta_json.get("additions", 0),
        "deletions":   meta_json.get("deletions", 0),
        "head_sha":    meta_json.get("head", {}).get("sha", ""),
    }

    # ── Fetch raw diff ────────────────────────────────────────────
    try:
        diff_response = requests.get(base_url, headers=headers_diff, timeout=GITHUB_TIMEOUT)
    except requests.RequestException as e:
        logger.warning("GitHub request failed: %s", e)   # details stay in the server log
        raise ValueError("Could not reach GitHub — please try again")
    if not diff_response.ok:
        raise ValueError(f"Failed to fetch diff: {diff_response.status_code}")

    # The full diff goes to the static scanners (a secret on line 5,000 still counts);
    # only the LLM prompts are cut to fit the model budget (see agent/nodes.py).
    # Hard cap protects memory against pathological multi-MB diffs.
    raw_diff = diff_response.text
    if len(raw_diff) > MAX_DIFF_BYTES:
        raw_diff = raw_diff[:MAX_DIFF_BYTES]
        metadata["diff_capped"] = True

    return raw_diff, metadata