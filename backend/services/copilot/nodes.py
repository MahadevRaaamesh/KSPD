from config import settings
from services.copilot.state import CopilotState
from services.copilot.synthesis import compose_answer
from adapters.llm import classify_intent, synthesize_response
from services.copilot.tools import (
    sql_query_tool, graph_query_tool, vector_search_tool, hotspot_tool,
)


async def router_node(state: CopilotState) -> CopilotState:
    try:
        classification = await classify_intent(state["question"])
        state["intent"] = classification.get("intent", "general_question")
        state["params"] = classification.get("params", {})

        # For similar-case search the whole question is the query text
        if state["intent"] == "similar_cases" and "text" not in state["params"]:
            state["params"]["text"] = state["question"]
    except Exception as e:
        state["error"] = f"intent classification failed: {e}"
    return state


async def tool_executor_node(state: CopilotState) -> CopilotState:
    if state.get("error"):
        return state
    try:
        intent = state["intent"]
        params = state["params"]
        results = []
        hint = None

        if intent in ["crime_trends", "station_analysis", "district_comparison",
                      "ipc_analysis", "case_details"]:
            results.append(await sql_query_tool(intent, params))
            hint = "chart" if intent in ("crime_trends", "district_comparison") else "table"

        elif intent == "criminal_network":
            results.append(await graph_query_tool(intent, params))
            hint = "graph"

        elif intent == "accused_history":
            results.append(await sql_query_tool(intent, params))
            results.append(await graph_query_tool(intent, params))
            hint = "graph"

        elif intent == "similar_cases":
            results.append(await vector_search_tool(intent, params))
            hint = "table"

        elif intent == "hotspot_analysis":
            results.append(await hotspot_tool(intent, params))
            hint = "map"

        state["tool_results"] = results
        state["visualization_hint"] = hint
    except Exception as e:
        state["error"] = f"tool execution failed: {e}"
    return state


def _extract_sources(tool_results: list) -> list:
    sources = set()
    for res in tool_results or []:
        for row in res.get("data") or []:
            if isinstance(row, dict) and row.get("fir_number"):
                sources.add(row["fir_number"])
        for item in res.get("similar_firs") or []:
            fir = item.get("fir") or {}
            if fir.get("fir_number"):
                sources.add(fir["fir_number"])
        summary = res.get("summary") or {}
        for fn in summary.get("fir_numbers") or []:
            sources.add(fn)
    return sorted(sources)[:12]


async def synthesizer_node(state: CopilotState) -> CopilotState:
    try:
        if settings.ENVIRONMENT == "local":
            state["response"] = compose_answer(
                state["question"], state["intent"], state["params"],
                state.get("tool_results", []))
        else:
            data = {} if state["intent"] == "general_question" else state.get("tool_results", [])
            state["response"] = await synthesize_response(state["question"], data, state["intent"])

        state["sources"] = _extract_sources(state.get("tool_results", []))
    except Exception as e:
        state["error"] = f"synthesis failed: {e}"
    return state


async def error_node(state: CopilotState) -> CopilotState:
    state["response"] = (
        "I hit a snag processing that question"
        + (f" ({state['error']})" if state.get("error") else "")
        + ". Try asking about crime trends, hotspots, similar cases, "
          "a district comparison, or the network of a named accused."
    )
    state["sources"] = state.get("sources") or []
    return state
