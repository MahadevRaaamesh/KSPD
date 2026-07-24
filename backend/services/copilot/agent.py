from langgraph.graph import StateGraph, END
from services.copilot.state import CopilotState
from services.copilot.nodes import router_node, tool_executor_node, synthesizer_node, error_node

def build_copilot_agent():
    graph = StateGraph(CopilotState)

    graph.add_node("router", router_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("synthesizer", synthesizer_node)
    graph.add_node("error_handler", error_node)

    graph.set_entry_point("router")

    graph.add_edge("router", "tool_executor")
    graph.add_edge("tool_executor", "synthesizer")
    graph.add_edge("synthesizer", END)
    graph.add_edge("error_handler", END)

    return graph.compile()

copilot_agent = build_copilot_agent()
