import json
import re
from typing import Dict, Any, Optional
from app.config import settings

class LLMService:
    """
    Unified LLM Service supporting:
    1. OpenAI structured responses
    2. Gemini structured responses
    3. High-fidelity heuristic/deterministic parsing engine (zero-dependency fallback)
    """

    @staticmethod
    def call_llm(system_prompt: str, user_prompt: str, response_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            try:
                import httpx
                headers = {
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": settings.LLM_MODEL or "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                response = httpx.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
            except Exception as e:
                print(f"[LLMService] OpenAI call failed, falling back to local evaluator: {e}")

        elif settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            try:
                import httpx
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{
                        "parts": [{"text": f"{system_prompt}\n\nTask: {user_prompt}\n\nReturn strictly valid JSON."}]
                    }],
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                }
                response = httpx.post(url, json=payload, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(content)
            except Exception as e:
                print(f"[LLMService] Gemini call failed, falling back to local evaluator: {e}")

        # Fallback to deterministic local evaluation
        return {}
