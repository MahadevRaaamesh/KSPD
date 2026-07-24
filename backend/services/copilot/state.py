from typing import TypedDict, Optional, List, Dict, Any

class CopilotState(TypedDict):
    question: str
    intent: str
    params: dict
    tool_results: List[dict]
    response: str
    sources: List[str]
    visualization_hint: Optional[str]
    error: Optional[str]
