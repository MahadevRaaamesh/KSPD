import json
import httpx
from config import settings

async def call_llm(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.1,
    max_tokens: int = 500
) -> str:
    """Unified LLM interface. Mock for local, Catalyst API for prod."""
    
    if settings.ENVIRONMENT == "local":
        print(f"[LLM Mock] Called with prompt: {prompt[:100]}...")
        # Simple mock matching logic for local testing
        if "classify this user question" in system_prompt.lower():
            if "trend" in prompt.lower():
                return '{"intent": "crime_trends", "params": {}}'
            if "similar" in prompt.lower():
                return '{"intent": "similar_cases", "params": {}}'
            if "network" in prompt.lower() or "connected" in prompt.lower():
                return '{"intent": "criminal_network", "params": {"person_name": "Ramesh"}}'
            return '{"intent": "general_question", "params": {}}'
        else:
            return f"Mock response based on: {prompt[:50]}..."
            
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
    system_prompt = """Classify this user question about crime data into one of these categories:
1. similar_cases - Finding similar FIRs or cases
2. accused_history - Looking up a person's criminal history
3. criminal_network - Finding connections between criminals
4. crime_trends - Asking about crime trends or statistics
5. station_analysis - Analyzing police station performance
6. district_comparison - Comparing districts
7. ipc_analysis - Asking about IPC sections
8. case_details - Looking up a specific case
9. general_question - General knowledge question

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
    except Exception as e:
        print(f"Failed to parse LLM intent JSON: {result_text}")
        return {"intent": "general_question", "params": {}}

async def synthesize_response(question: str, data: dict, intent: str) -> str:
    system_prompt = """You are a crime intelligence assistant for Karnataka State Police.
Write a clear, concise answer summarizing the provided data to answer the user's question.
Reference specific FIR numbers and names when available.
Keep the response professional and under 200 words."""

    prompt = f"User Question: {question}\nIntent: {intent}\nData Retrieved: {json.dumps(data)}"
    
    return await call_llm(prompt=prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=600)
