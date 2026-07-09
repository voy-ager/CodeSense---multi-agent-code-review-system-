# agent/graph.py

from langgraph.graph import StateGraph, START, END
from agent.state import GraphState
from agent.nodes import (
    ingest_diff,
    security_agent,
    perf_agent,
    test_agent,
    style_agent,
    synthesize,
)


def route_after_ingest(state: GraphState) -> list[str]:
    if state.get("error"):
        print(f"[router] Error detected: {state['error']} — stopping graph.")
        return END

    print("[router] Diff fetched — dispatching to all 4 agents in parallel.")
    return ["security_agent", "perf_agent", "test_agent", "style_agent"]


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("ingest_diff",    ingest_diff)
    graph.add_node("security_agent", security_agent)
    graph.add_node("perf_agent",     perf_agent)
    graph.add_node("test_agent",     test_agent)
    graph.add_node("style_agent",    style_agent)
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

    graph.add_edge("synthesize", END)

    app = graph.compile()
    print("[graph] Graph compiled successfully.")
    return app