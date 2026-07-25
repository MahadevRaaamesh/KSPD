import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Demo-grade credentials for the hackathon build — not a real auth system.
_DEMO_USERS = {
    ("KSP-1054", "drishti"),
    ("admin", "admin"),
}

_DEMO_OFFICER = {
    "name": "Insp. Pavankumar T",
    "rank": "Inspector",
    "station": "Cubbon Park PS",
    "badge_id": "KSP-1054",
}


class LoginRequest(BaseModel):
    badge_id: str
    password: str


@router.post("/login")
async def login(request: LoginRequest):
    if (request.badge_id, request.password) not in _DEMO_USERS:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "token": secrets.token_hex(16),
        "officer": _DEMO_OFFICER,
    }
