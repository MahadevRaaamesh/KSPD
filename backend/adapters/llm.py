import json
import re
import httpx
from config import settings
from adapters.database import execute_query

# ---------------------------------------------------------------------------
# Known entities for local (offline) intent classification
# ---------------------------------------------------------------------------

KNOWN_DISTRICTS = [
    "Bengaluru City", "Mysuru", "Mangaluru", "Hubballi-Dharwad", "Belagavi",
    "Kalaburagi", "Ballari", "Shivamogga", "Tumakuru", "Davanagere",
    "Vijayapura", "Udupi", "Hassan", "Ramanagara",
]

KNOWN_MAJOR_HEADS = [
    "Property Crimes", "Crimes Against Body", "Cyber Crimes",
    "Crimes Against Women", "Narcotics", "Economic Offences",
    "Road Incidents", "Public Order",
]

KNOWN_MINOR_HEADS = [
    "Chain Snatching", "House Burglary", "Vehicle Theft", "Mobile Phone Theft",
    "Robbery", "Assault", "Murder", "Attempt to Murder", "Kidnapping",
    "OTP Fraud", "Investment Scam", "Identity Theft", "Social Media Harassment",
    "Domestic Cruelty", "Harassment", "Stalking", "Ganja Possession",
    "Synthetic Drugs Peddling", "Cheating", "Ponzi Scheme", "Bank Fraud",
    "Hit and Run", "Rash Driving", "Rioting", "Unlawful Assembly",
]

# loose keyword -> canonical category
_CATEGORY_ALIASES = {
    "snatching": ("Chain Snatching", "minor"),
    "burglary": ("House Burglary", "minor"),
    "vehicle theft": ("Vehicle Theft", "minor"),
    "bike theft": ("Vehicle Theft", "minor"),
    "phone theft": ("Mobile Phone Theft", "minor"),
    "robbery": ("Robbery", "minor"),
    "murder": ("Murder", "minor"),
    "kidnapping": ("Kidnapping", "minor"),
    "assault": ("Assault", "minor"),
    "otp": ("OTP Fraud", "minor"),
    "investment scam": ("Investment Scam", "minor"),
    "stalking": ("Stalking", "minor"),
    "ganja": ("Ganja Possession", "minor"),
    "drug": ("Narcotics", "major"),
    "narcotic": ("Narcotics", "major"),
    "cyber": ("Cyber Crimes", "major"),
    "fraud": ("Cyber Crimes", "major"),
    "theft": ("Property Crimes", "major"),
    "property": ("Property Crimes", "major"),
    "women": ("Crimes Against Women", "major"),
    "cheating": ("Cheating", "minor"),
    "ponzi": ("Ponzi Scheme", "minor"),
    "hit and run": ("Hit and Run", "minor"),
    "rioting": ("Rioting", "minor"),
}

_NAME_STOPWORDS = {
    "show", "what", "which", "who", "whose", "where", "when", "how", "why",
    "find", "give", "list", "tell", "compare", "analyse", "analyze", "the",
    "ipc", "fir", "police", "station", "district", "karnataka", "crime",
    "crimes", "criminal", "network", "history", "record", "cases", "case",
    "trends", "trend", "hotspot", "hotspots", "last", "months", "month",
    "days", "day", "across", "against", "similar", "connected", "gang",
    "associates",
}
_NAME_STOPWORDS.update(w.lower() for d in KNOWN_DISTRICTS for w in re.split(r"[ -]", d))
_NAME_STOPWORDS.update(w.lower() for c in KNOWN_MINOR_HEADS + KNOWN_MAJOR_HEADS for w in c.split())


def _extract_district(q_lower: str):
    found = []
    for d in KNOWN_DISTRICTS:
        first_token = re.split(r"[ -]", d)[0].lower()
        if d.lower() in q_lower or first_token in q_lower:
            found.append(d)
    return found


def _extract_category(q_lower: str):
    for m in KNOWN_MINOR_HEADS:
        if m.lower() in q_lower:
            return m, "minor"
    for m in KNOWN_MAJOR_HEADS:
        if m.lower() in q_lower:
            return m, "major"
    for alias, (cat, level) in _CATEGORY_ALIASES.items():
        if alias in q_lower:
            return cat, level
    return None, None


async def _extract_person_name(question: str):
    """Match capitalized tokens against real Accused names in the DB."""
    tokens = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", question)
    candidates = []
    for t in tokens:
        words = t.split()
        if all(w.lower() in _NAME_STOPWORDS for w in words):
            continue
        candidates.append(t)
    # longest candidates first (full names beat single tokens)
    candidates.sort(key=len, reverse=True)
    for cand in candidates[:5]:
        res = await execute_query(
            "SELECT name FROM Accused WHERE LOWER(name) LIKE LOWER(:n) LIMIT 1",
            {"n": f"%{cand}%"})
        if res:
            return res[0]["name"]
    return None


async def local_classify_intent(question: str) -> dict:
    """Deterministic keyword/entity intent classifier — no LLM required."""
    q = question.lower()
    params: dict = {}

    districts = _extract_district(q)
    if districts:
        params["district"] = districts[0]
        if len(districts) > 1:
            params["districts"] = districts

    category, level = _extract_category(q)
    if category:
        params["crime_category"] = category
        params["category_level"] = level

    m = re.search(r"last\s+(\d+)\s*(month|day|week)s?", q)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        params["last_n"] = n
        params["last_unit"] = unit

    fir_match = re.search(r"\b([A-Z]{4}-\d{4}/\d{4})\b", question)
    if fir_match:
        params["fir_number"] = fir_match.group(1)
        return {"intent": "case_details", "params": params}

    person = await _extract_person_name(question)
    if person:
        params["person_name"] = person

    def has(*words):
        return any(w in q for w in words)

    if has("similar", "like this", "matching", "resembl"):
        intent = "similar_cases"
        params["text"] = question
    elif has("network", "connected", "associate", "gang", "links", "co-accused", "nexus"):
        intent = "criminal_network"
    elif has("history of", "record of", "cases against", "criminal history", "priors", "antecedent"):
        intent = "accused_history"
    elif has("hotspot", "dangerous", "risky", "unsafe") or ("where" in q and category):
        intent = "hotspot_analysis"
    elif has("compare", "across districts", "which district", "district wise", "districtwise", "versus", " vs "):
        intent = "district_comparison"
    elif has("station"):
        intent = "station_analysis"
    elif has("ipc", "section"):
        intent = "ipc_analysis"
    elif has("trend", "over time", "monthly", "increase", "rising", "growth", "statistics", "how many"):
        intent = "crime_trends"
    elif person:
        intent = "accused_history"
    elif districts or category:
        intent = "crime_trends"
    else:
        intent = "general_question"

    return {"intent": intent, "params": params}


# ---------------------------------------------------------------------------
# LLM plumbing (QuickML in production, offline analyst locally)
# ---------------------------------------------------------------------------

async def call_llm(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.1,
    max_tokens: int = 500
) -> str:
    """Unified LLM interface. Local mode is fully offline; prod uses Catalyst QuickML."""

    if settings.ENVIRONMENT == "local":
        # Local mode never calls out. Copilot answers are composed by the
        # template NLG in services/copilot/synthesis.py; this path only serves
        # as a safety net if invoked directly.
        return ("Offline analyst mode: ask about crime trends, hotspots, "
                "criminal networks, repeat offenders, district comparisons or IPC sections.")

    # Catalyst QuickML API
    if not settings.QUICKML_LLM_ENDPOINT:
        return "Error: QUICKML_LLM_ENDPOINT is not configured."

    headers = {
        "Authorization": f"Zoho-oauthtoken {settings.QUICKML_OAUTH_TOKEN}",
        "X-ZORG-ID": settings.QUICKML_ORG_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(settings.QUICKML_LLM_ENDPOINT, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM Call Error: {str(e)}")
            return f"Error connecting to LLM: {str(e)}"


async def classify_intent(question: str) -> dict:
    if settings.ENVIRONMENT == "local":
        return await local_classify_intent(question)

    system_prompt = """Classify this user question about crime data into one of these categories:
1. similar_cases - Finding similar FIRs or cases
2. accused_history - Looking up a person's criminal history
3. criminal_network - Finding connections between criminals
4. crime_trends - Asking about crime trends or statistics
5. station_analysis - Analyzing police station performance
6. district_comparison - Comparing districts
7. ipc_analysis - Asking about IPC sections
8. hotspot_analysis - Asking where crime concentrates
9. case_details - Looking up a specific case
10. general_question - General knowledge question

Also extract these parameters if present:
- district: str or null
- crime_category: str or null
- person_name: str or null
- date_from: str or null
- date_to: str or null
- fir_number: str or null

Respond ONLY with valid JSON in this format: {"intent": "...", "params": {...}}
"""
    result_text = await call_llm(prompt=question, system_prompt=system_prompt, temperature=0.1)

    try:
        # Extract JSON if the LLM wrapped it in markdown
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]

        return json.loads(result_text.strip())
    except Exception:
        print(f"Failed to parse LLM intent JSON: {result_text}")
        return {"intent": "general_question", "params": {}}


async def synthesize_response(question: str, data, intent: str) -> str:
    system_prompt = """You are a crime intelligence assistant for Karnataka State Police.
Write a clear, concise answer summarizing the provided data to answer the user's question.
Reference specific FIR numbers and names when available.
Keep the response professional and under 200 words."""

    prompt = f"User Question: {question}\nIntent: {intent}\nData Retrieved: {json.dumps(data, default=str)}"

    return await call_llm(prompt=prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=600)
