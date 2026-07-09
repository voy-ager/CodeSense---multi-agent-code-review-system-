# main.py

from agent.graph import build_graph
import json

def main():
    print("=== CodeSense Agent ===\n")

    # Build the graph once
    app = build_graph()

    # Use a real public PR for testing — this is a small React PR
    # Replace with any public GitHub PR URL you want to test
    pr_url = "https://github.com/psf/requests/pull/6746"

    print(f"Analyzing PR: {pr_url}\n")

    # invoke() runs the full graph synchronously and returns final state
    result = app.invoke({
        "pr_url":            pr_url,
        "raw_diff":          "",
        "pr_metadata":       {},
        "security_findings": [],
        "perf_findings":     [],
        "test_findings":     [],
        "style_findings":    [],
        "final_report":      {},
        "retry_count":       0,
        "error":             "",
    })

    # Print the final report
    if result.get("error"):
        print(f"\nError: {result['error']}")
    else:
        print("\n=== Final Report ===")
        print(json.dumps(result["final_report"], indent=2))

if __name__ == "__main__":
    main()