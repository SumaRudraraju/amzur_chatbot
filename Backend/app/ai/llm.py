import json
import os
import urllib.error
import urllib.request
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from ..core.settings import settings


class LiteLLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    litellm_proxy_url: str = os.getenv("LITELLM_PROXY_URL", "https://litellm.amzur.com")
    litellm_api_key: str = os.getenv("LITELLM_API_KEY", "")
    llm_model: str = settings.LLM_MODEL
    litellm_user_id: str = os.getenv("LITELLM_USER_ID", "")
    litellm_embedding_model: Optional[str] = None
    image_gen_model: Optional[str] = None
    supabase_url: Optional[str] = None


class LiteLLM:
    def __init__(self, model: str, proxy_url: str, api_key: str, user_email: str, temperature: float = 0.2) -> None:
        self.model = model
        self.proxy_url = proxy_url
        self.api_key = api_key
        self.user_email = user_email
        self.temperature = temperature

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "metadata": {"user_email": self.user_email},
        }
        if stop:
            payload["stop"] = stop

        url = self.proxy_url.rstrip("/") + "/v1/chat/completions"
        request_data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            raise RuntimeError(f"LiteLLM request failed: {exc.code} {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LiteLLM request failed: {exc.reason}") from exc

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise RuntimeError("LiteLLM response did not contain valid choices.")

        first_choice = choices[0]
        message = first_choice.get("message", {})
        content = message.get("content")
        if content is None:
            raise RuntimeError("LiteLLM response did not include assistant content.")

        return content

    def generate(self, prompts: List[str], stop: Optional[List[str]] = None) -> SimpleNamespace:
        generations = []
        for prompt in prompts:
            text = self._call(prompt, stop=stop)
            generations.append([SimpleNamespace(text=text)])
        return SimpleNamespace(generations=generations)


def get_llm() -> LiteLLM:
    llm_settings = LiteLLMSettings()
    if not llm_settings.litellm_api_key:
        raise RuntimeError("LITELLM_API_KEY is required for the chat service.")

    return LiteLLM(
        model=settings.LLM_MODEL,
        proxy_url=llm_settings.litellm_proxy_url,
        api_key=llm_settings.litellm_api_key,
        user_email=llm_settings.litellm_user_id,
        temperature=0.2,
    )
