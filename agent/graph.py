# agent/graph.py

import logging
from langgraph.graph import StateGraph, START, END
from agent.state import GraphState
from agent.nodes import (
    ingest_diff,
    security_agent,
    perf_agent,
    test_agent,
    style_agent,
    static_scan,
    synthesize,
)


logger = logging.getLogger(__name__)

def route_after_ingest(state: GraphState) -> list[str]:
    if state.get("error"):
        logger.warning(f"[router] Error detected: {state['error']} — stopping graph.")
        return END

    logger.info("[router] Diff fetched — dispatching to 4 agents + static scan in parallel.")
    return ["security_agent", "perf_agent", "test_agent", "style_agent", "static_scan"]


def initial_state(pr_url: str) -> dict:
    """Empty state for one review — shared by the API, CLI and MCP server."""
    return {
        "pr_url":            pr_url,
        "raw_diff":          "",
        "pr_metadata":       {},
        "security_findings": [],
        "perf_findings":     [],
        "test_findings":     [],
        "style_findings":    [],
        "static_findings":   [],
        "final_report":      {},
        "failed_agents":     [],
        "error":             "",
    }


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("ingest_diff",    ingest_diff)
    graph.add_node("security_agent", security_agent)
    graph.add_node("perf_agent",     perf_agent)
    graph.add_node("test_agent",     test_agent)
    graph.add_node("style_agent",    style_agent)
    graph.add_node("static_scan",    static_scan)
    graph.add_node("synthesize",     synthesize)

    graph.add_edge(START, "ingest_diff")

    graph.add_conditional_edges(
        "ingest_diff",
        route_after_ingest,
    )

    graph.add_edge("security_agent", "synthesize")
    graph.add_edge("perf_agent",     "synthesize")
    graph.add_edge("test_agent",     "synthesize")
    graph.add_edge("style_agent",    "synthesize")
    graph.add_edge("static_scan",    "synthesize")

    graph.add_edge("synthesize", END)

    app = graph.compile()
    logger.info("[graph] Graph compiled successfully.")
    return app