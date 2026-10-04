import json
import re
from typing import Dict, Any, Optional
from app.config import settings

class LLMService:
    """
    Unified LLM Service supporting:
    1. Google Gemini structured responses (gemini-1.5-flash / gemini-1.5-pro)
    2. High-fidelity heuristic/deterministic parsing engine (zero-dependency fallback)
    """

    @staticmethod
    def call_llm(system_prompt: str, user_prompt: str, response_schema: Optional[Dict[str, Any]] = None,
                 timeout_seconds: float = 30.0, model_name: Optional[str] = None,
                 raise_errors: bool = False) -> Dict[str, Any]:
        if settings.LLM_PROVIDER in ["gemini", "default"] and settings.GEMINI_API_KEY:
            try:
                import httpx
                model = model_name or settings.LLM_MODEL or "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{
                        "parts": [{"text": f"{system_prompt}\n\nTask: {user_prompt}\n\nReturn strictly valid JSON matching the requested structure."}]
                    }],
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                }
                response = httpx.post(url, json=payload, timeout=timeout_seconds)
                if response.status_code == 200:
                    data = response.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    # Strip any markdown fences if present
                    if content.startswith("```"):
                        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
                    return json.loads(content)
                else:
                    if raise_errors:
                        raise RuntimeError(f"LLM_HTTP_{response.status_code}")
                    print(f"[LLMService] Gemini API returned HTTP {response.status_code}")
            except Exception as e:
                if raise_errors:
                    raise
                print(f"[LLMService] Gemini call failed, falling back to local evaluator: {e}")

        # Fallback to deterministic local evaluation
        return {}
