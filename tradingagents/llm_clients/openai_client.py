import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from .base_client import BaseLLMClient, normalize_content
from tradingagents.default_config import get_provider_base_url
from .validators import validate_model


class NormalizedChatOpenAI(ChatOpenAI):
    """ChatOpenAI with normalized content output.

    The Responses API returns content as a list of typed blocks
    (reasoning, text, etc.). This normalizes to string for consistent
    downstream handling.
    """

    def invoke(self, input, config=None, **kwargs):
        return normalize_content(super().invoke(input, config, **kwargs))

# Kwargs forwarded from user config to ChatOpenAI
_PASSTHROUGH_KWARGS = (
    "timeout", "max_retries", "reasoning_effort",
    "api_key", "callbacks", "http_client", "http_async_client",
)

# Provider API key env vars
_PROVIDER_CONFIG = {
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "glm": "ZHIPU_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": None,
}

_OFFICIAL_OPENAI_BASE_URL = "https://api.openai.com/v1"
_RESPONSES_API_MODE = "responses"
_CHAT_COMPLETIONS_API_MODE = "chat_completions"


def _normalize_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None
    return base_url.rstrip("/")


def _resolve_openai_api_mode(base_url: Optional[str]) -> str:
    override = os.getenv("OPENAI_API_MODE", "").strip().lower()
    if override in (_RESPONSES_API_MODE, _CHAT_COMPLETIONS_API_MODE):
        return override

    if _normalize_base_url(base_url) == _normalize_base_url(_OFFICIAL_OPENAI_BASE_URL):
        return _RESPONSES_API_MODE

    return _CHAT_COMPLETIONS_API_MODE


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI, Ollama, OpenRouter, and xAI providers.

    For native OpenAI models, uses the Responses API (/v1/responses) which
    supports reasoning_effort with function tools across all model families
    (GPT-4.1, GPT-5). Third-party compatible providers (xAI, OpenRouter,
    Ollama) use standard Chat Completions.
    """

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        provider: str = "openai",
        **kwargs,
    ):
        super().__init__(model, base_url, **kwargs)
        self.provider = provider.lower()

    def get_llm(self) -> Any:
        """Return configured ChatOpenAI instance."""
        self.warn_if_unknown_model()
        llm_kwargs = {"model": self.model}
        resolved_base_url = self.base_url

        # Provider-specific base URL and auth
        if self.provider in _PROVIDER_CONFIG:
            resolved_base_url = self.base_url or get_provider_base_url(self.provider)
            llm_kwargs["base_url"] = resolved_base_url
            api_key_env = _PROVIDER_CONFIG[self.provider]
            if api_key_env:
                api_key = os.environ.get(api_key_env)
                if api_key:
                    llm_kwargs["api_key"] = api_key
            else:
                llm_kwargs["api_key"] = "ollama"
        elif self.base_url:
            llm_kwargs["base_url"] = self.base_url

        # Forward user-provided kwargs
        for key in _PASSTHROUGH_KWARGS:
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        # Native OpenAI: use Responses API for consistent behavior across
        # all model families. Third-party providers use Chat Completions.
        if self.provider == "openai":
            llm_kwargs["use_responses_api"] = (
                _resolve_openai_api_mode(resolved_base_url) == _RESPONSES_API_MODE
            )

        return NormalizedChatOpenAI(**llm_kwargs)

    def validate_model(self) -> bool:
        """Validate model for the provider."""
        return validate_model(self.provider, self.model)
