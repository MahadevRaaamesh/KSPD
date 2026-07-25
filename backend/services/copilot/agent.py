from langgraph.graph import StateGraph, END
from services.copilot.state import CopilotState
from services.copilot.nodes import router_node, tool_executor_node, synthesizer_node, error_node


def _route_on_error(next_node: str):
    def _route(state: CopilotState) -> str:
        return "error_handler" if state.get("error") else next_node
    return _route


def build_copilot_agent():
    graph = StateGraph(CopilotState)

    graph.add_node("router", router_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("error_handler", error_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges("router", _route_on_error("tool_executor"),
                                {"tool_executor": "tool_executor", "error_handler": "error_handler"})
    graph.add_conditional_edges("tool_executor", _route_on_error("synthesizer"),
                                {"synthesizer": "synthesizer", "error_handler": "error_handler"})
    graph.add_conditional_edges("synthesizer", _route_on_error(END),
                                {END: END, "error_handler": "error_handler"})
    graph.add_edge("error_handler", END)

    return graph.compile()


copilot_agent = build_copilot_agent()
