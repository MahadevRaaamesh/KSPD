from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from models.schemas import CopilotRequest, CopilotResponse
from services.copilot.agent import copilot_agent
import json

router = APIRouter()

@router.post("/query", response_model=CopilotResponse)
async def copilot_query(request: CopilotRequest):
    initial_state = {
        "question": request.question,
        "intent": "",
        "params": {},
        "tool_results": [],
        "response": "",
        "sources": [],
        "visualization_hint": None,
        "error": None
    }
    
    final_state = await copilot_agent.ainvoke(initial_state)
    
    return CopilotResponse(
        answer=final_state.get("response", "No response generated."),
        sources=final_state.get("sources", []),
        visualization_hint=final_state.get("visualization_hint"),
        data={"raw": final_state.get("tool_results", [])}
    )

@router.get("/stream")
async def copilot_stream(question: str):
    async def generate():
        initial_state = {
            "question": question,
            "intent": "",
            "params": {},
            "tool_results": [],
            "response": "",
            "sources": [],
            "visualization_hint": None,
            "error": None
        }
        
        # We can yield state changes as they happen
        async for output in copilot_agent.astream(initial_state):
            # output is a dict mapping node_name -> state_updates
            for node, state in output.items():
                
                if node == "router":
                    yield f"data: {json.dumps({'event': 'intent', 'intent': state.get('intent')})}\n\n"
                    yield f"data: {json.dumps({'event': 'searching', 'message': 'Gathering information...'})}\n\n"
                    
                elif node == "tool_executor":
                    yield f"data: {json.dumps({'event': 'data_ready', 'hint': state.get('visualization_hint')})}\n\n"
                    
                elif node == "synthesizer" or node == "error_handler":
                    yield f"data: {json.dumps({'event': 'response', 'text': state.get('response')})}\n\n"
                    if state.get('sources'):
                        yield f"data: {json.dumps({'event': 'sources', 'sources': state.get('sources')})}\n\n"
                        
        yield f"data: {json.dumps({'event': 'done'})}\n\n"
        
    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/suggestions")
async def copilot_suggestions():
    return [
      {"text": "Show robbery trends in Bengaluru Urban", "icon": "chart"},
      {"text": "Find cases similar to chain snatching at night", "icon": "search"},
      {"text": "Show criminal network of Ramesh", "icon": "graph"},
      {"text": "Which police station has the most pending cases?", "icon": "table"},
      {"text": "Compare crime rates across districts", "icon": "chart"},
      {"text": "What IPC sections are most common in theft?", "icon": "table"},
    ]
