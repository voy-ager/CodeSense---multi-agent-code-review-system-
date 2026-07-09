# tools/github.py

import requests
import os
from dotenv import load_dotenv

load_dotenv()

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
    try:
        parts  = pr_url.rstrip("/").split("/")
        owner  = parts[-4]
        repo   = parts[-3]
        pr_num = parts[-1]
    except IndexError:
        raise ValueError(f"Invalid GitHub PR URL: {pr_url}")

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
    meta_response = requests.get(base_url, headers=headers_json)
    if meta_response.status_code == 404:
        raise ValueError(f"PR not found: {pr_url}")
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
    }

    # ── Fetch raw diff ────────────────────────────────────────────
    diff_response = requests.get(base_url, headers=headers_diff)
    if not diff_response.ok:
        raise ValueError(f"Failed to fetch diff: {diff_response.status_code}")

    raw_diff = diff_response.text

    # Truncate very large diffs — LLMs have context limits.
    # 8000 chars ≈ the first ~200 changed lines, enough for meaningful review.
    # In production you'd chunk this and run agents per-file instead.
    MAX_DIFF_CHARS = 8000
    if len(raw_diff) > MAX_DIFF_CHARS:
        raw_diff = raw_diff[:MAX_DIFF_CHARS] + "\n\n[diff truncated — too large]"

    return raw_diff, metadata