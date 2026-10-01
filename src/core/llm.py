"""Lightweight, multi-provider LLM client supporting OpenRouter, Gemini, and OpenAI."""

from typing import Optional, Dict, Any, List
import logging
import json
import httpx
from src.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Zero-dependency (via httpx) multi-provider LLM interface with Pydantic JSON schema support."""

    def __init__(self):
        self.openrouter_key = settings.openrouter_api_key
        self.google_key = settings.google_api_key
        self.openai_key = settings.openai_api_key
        self.timeout = settings.llm_timeout

    @property
    def is_available(self) -> bool:
        """Returns True if any valid LLM key is configured."""
        return settings.has_llm_key

    def generate_json(self, prompt: str, system_prompt: str = "") -> Optional[Dict[str, Any]]:
        """Call LLM and parse JSON response. Returns None if no key is available or on error."""
        if not self.is_available:
            return None

        # 1. Try OpenRouter
        if self.openrouter_key:
            return self._call_openrouter(prompt, system_prompt)

        # 2. Try Google Gemini
        if self.google_key:
            return self._call_gemini(prompt, system_prompt)

        # 3. Try OpenAI
        if self.openai_key:
            return self._call_openai(prompt, system_prompt)

        return None

    def _call_openrouter(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": settings.app_name
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.openrouter_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            logger.warning(f"OpenRouter call failed: {e}")
            return None

    def _call_gemini(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        model = settings.google_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.google_key}"
        headers = {"Content-Type": "application/json"}
        
        full_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "contents": [{"parts": [{"text": full_text}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(content)
        except Exception as e:
            logger.warning(f"Gemini call failed: {e}")
            return None

    def _call_openai(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.openai_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            logger.warning(f"OpenAI call failed: {e}")
            return None


llm_client = LLMClient()
