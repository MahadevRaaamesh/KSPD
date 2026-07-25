import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from models.schemas import CopilotRequest, CopilotResponse
from services.copilot.agent import copilot_agent

router = APIRouter()


def _initial_state(question: str) -> dict:
    return {
        "question": question,
        "intent": "",
        "params": {},
        "tool_results": [],
        "response": "",
        "sources": [],
        "visualization_hint": None,
        "error": None,
    }


@router.post("/query", response_model=CopilotResponse)
async def copilot_query(request: CopilotRequest):
    final_state = await copilot_agent.ainvoke(_initial_state(request.question))

    return CopilotResponse(
        answer=final_state.get("response", "No response generated."),
        sources=final_state.get("sources", []),
        visualization_hint=final_state.get("visualization_hint"),
        data={"raw": final_state.get("tool_results", [])}
    )


def _chunk_words(text: str, size: int = 8):
    words = text.split(" ")
    for i in range(0, len(words), size):
        yield " ".join(words[i:i + size]) + (" " if i + size < len(words) else "")


@router.get("/stream")
async def copilot_stream(question: str):
    async def generate():
        final = {"response": "", "sources": [], "visualization_hint": None,
                 "tool_results": [], "intent": None}

        async for output in copilot_agent.astream(_initial_state(question)):
            # output is a dict mapping node_name -> state_updates
            for node, state in output.items():
                if node == "router":
                    final["intent"] = state.get("intent")
                    yield f"data: {json.dumps({'event': 'intent', 'intent': state.get('intent')})}\n\n"
                    yield f"data: {json.dumps({'event': 'searching', 'message': 'Gathering information...'})}\n\n"

                elif node == "tool_executor":
                    final["visualization_hint"] = state.get("visualization_hint")
                    final["tool_results"] = state.get("tool_results", [])
                    yield f"data: {json.dumps({'event': 'data_ready', 'hint': state.get('visualization_hint')})}\n\n"

                elif node in ("synthesizer", "error_handler"):
                    text = state.get("response") or ""
                    final["response"] = text
                    final["sources"] = state.get("sources") or []
                    # stream the answer in small chunks for a live-typing feel
                    for chunk in _chunk_words(text, 8):
                        yield f"data: {json.dumps({'event': 'response', 'text': chunk})}\n\n"
                        await asyncio.sleep(0.05)
                    if final["sources"]:
                        yield f"data: {json.dumps({'event': 'sources', 'sources': final['sources']})}\n\n"

        # full payload (same shape as /query) so the UI can render charts/graphs
        payload = {
            "answer": final["response"],
            "sources": final["sources"],
            "visualization_hint": final["visualization_hint"],
            "data": {"raw": final["tool_results"]},
        }
        yield f"data: {json.dumps({'event': 'payload', 'data': payload})}\n\n"
        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/suggestions")
async def copilot_suggestions():
    """Suggestions generated from the live data: real offender, district, spike."""
    from services.graph_service import get_repeat_offenders
    from services.analytics_service import get_district_stats, get_insights

    offender_name = "Ravi Gowda"
    top_district = "Bengaluru City"
    spike_cat, spike_district = "Chain Snatching", "Bengaluru City"

    try:
        offenders = await get_repeat_offenders(limit=1)
        if offenders:
            offender_name = offenders[0]["name"]
        districts = await get_district_stats()
        if districts:
            top_district = districts[0].district
        insights = await get_insights()
        spike = next((i for i in insights if i.get("type") == "spike"), None)
        if spike:
            spike_cat = spike.get("category") or spike_cat
            spike_district = spike.get("district") or spike_district
    except Exception:
        pass  # fall back to defaults — suggestions must never fail

    return [
        {"text": f"Show {spike_cat.lower()} trends in {spike_district} over the last 6 months", "icon": "chart"},
        {"text": f"Where are the {spike_cat.lower()} hotspots in {spike_district}?", "icon": "map"},
        {"text": f"Show the criminal network of {offender_name}", "icon": "graph"},
        {"text": f"Which police station in {top_district} has the most pending cases?", "icon": "table"},
        {"text": "Compare crime volumes and clearance across districts", "icon": "chart"},
        {"text": "Find cases similar to a night house burglary where a van was seen nearby", "icon": "search"},
    ]
