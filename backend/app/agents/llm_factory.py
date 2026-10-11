import json
import re
from typing import Dict, Any, Optional
from app.config import settings


def llm_available() -> bool:
    return settings.LLM_PROVIDER in ("gemini", "default") and bool(settings.GEMINI_API_KEY)


class LLMService:
    """Thin Gemini client returning parsed JSON. Callers treat any failure as a fallback signal."""

    @staticmethod
    def call_llm(system_prompt: str, user_prompt: str, response_schema: Optional[Dict[str, Any]] = None,
                 timeout_seconds: float = 30.0, model_name: Optional[str] = None,
                 raise_errors: bool = False) -> Dict[str, Any]:
        if not llm_available():
            if raise_errors:
                raise RuntimeError("LLM_DISABLED")
            return {}
        try:
            import httpx
            model = model_name or settings.LLM_MODEL
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": f"{user_prompt}\n\nReturn strictly valid JSON."}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
            }
            # API key travels in a header, never in the URL (URLs end up in proxy and access logs).
            response = httpx.post(url, json=payload, timeout=timeout_seconds,
                                  headers={"x-goog-api-key": settings.GEMINI_API_KEY})
            if response.status_code != 200:
                raise RuntimeError(f"LLM_HTTP_{response.status_code}")
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
            data = json.loads(content)
            return data if isinstance(data, dict) else {}
        except Exception:
            if raise_errors:
                raise
            return {}
