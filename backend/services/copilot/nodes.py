from services.copilot.state import CopilotState
from adapters.llm import classify_intent, synthesize_response
from services.copilot.tools import sql_query_tool, graph_query_tool, vector_search_tool

async def router_node(state: CopilotState) -> CopilotState:
    classification = await classify_intent(state["question"])
    state["intent"] = classification.get("intent", "general_question")
    state["params"] = classification.get("params", {})
    
    # If the user is asking for similar cases, make sure the text parameter is the whole question
    if state["intent"] == "similar_cases" and "text" not in state["params"]:
        state["params"]["text"] = state["question"]
        
    return state

async def tool_executor_node(state: CopilotState) -> CopilotState:
    intent = state["intent"]
    params = state["params"]
    results = []
    hint = None
    
    if intent in ["crime_trends", "station_analysis", "district_comparison", "ipc_analysis", "case_details"]:
        res = await sql_query_tool(intent, params)
        results.append(res)
        hint = "chart" if intent == "crime_trends" else "table"
        
    elif intent == "criminal_network":
        res = await graph_query_tool(intent, params)
        results.append(res)
        hint = "graph"
        
    elif intent == "accused_history":
        res1 = await sql_query_tool(intent, params)
        res2 = await graph_query_tool(intent, params)
        results.extend([res1, res2])
        hint = "graph"
        
    elif intent == "similar_cases":
        res = await vector_search_tool(intent, params)
        results.append(res)
        hint = "table"
        
    state["tool_results"] = results
    state["visualization_hint"] = hint
    return state

async def synthesizer_node(state: CopilotState) -> CopilotState:
    if state["intent"] == "general_question":
        # Just answer directly without data
        state["response"] = await synthesize_response(state["question"], {}, state["intent"])
    else:
        state["response"] = await synthesize_response(state["question"], state["tool_results"], state["intent"])
        
    # Extract FIR sources as a simple heuristic (look for CaseNo in tool results)
    sources = set()
    for res in state["tool_results"]:
        if "data" in res:
            for row in res["data"]:
                if "CaseNo" in row and row["CaseNo"]:
                    sources.add(row["CaseNo"])
        elif "similar_firs" in res:
            for item in res["similar_firs"]:
                if "fir" in item and "CaseNo" in item["fir"] and item["fir"]["CaseNo"]:
                    sources.add(item["fir"]["CaseNo"])
                    
    state["sources"] = list(sources)
    return state

async def error_node(state: CopilotState) -> CopilotState:
    state["response"] = "I couldn't process that question. Try asking about crime trends, similar cases, or criminal networks."
    return state
