from __future__ import annotations

import os
from typing import Optional

from .validators import validate_model

OFFICIAL_OPENAI_BASE_URL = "https://api.openai.com/v1"
NATIVE_TOOLS = "native_tools"
HOST_MANAGED_TOOLS = "host_managed_tools"

_DEFAULT_CUSTOM_GATEWAY_FALLBACKS = ("gpt-5.3-codex-spark", "gemma-4-31b")


def normalize_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None
    return base_url.rstrip("/")


def resolve_tool_execution_mode(provider: str, base_url: Optional[str]) -> str:
    provider_lower = provider.lower()

    if provider_lower == "openai":
        override = os.getenv("OPENAI_TOOL_MODE", "").strip().lower()
        if override in {NATIVE_TOOLS, HOST_MANAGED_TOOLS}:
            return override

        if normalize_base_url(base_url) == normalize_base_url(OFFICIAL_OPENAI_BASE_URL):
            return NATIVE_TOOLS

        return HOST_MANAGED_TOOLS

    return NATIVE_TOOLS


def resolve_model_fallback_chain(
    provider: str,
    primary_model: str,
    base_url: Optional[str],
) -> list[str]:
    provider_lower = provider.lower()
    candidates = [primary_model]

    if (
        provider_lower == "openai"
        and normalize_base_url(base_url) != normalize_base_url(OFFICIAL_OPENAI_BASE_URL)
    ):
        override = os.getenv("OPENAI_FALLBACK_MODELS", "").strip()
        extras = (
            [item.strip() for item in override.split(",") if item.strip()]
            if override
            else list(_DEFAULT_CUSTOM_GATEWAY_FALLBACKS)
        )
        if normalize_base_url(base_url) == normalize_base_url(OFFICIAL_OPENAI_BASE_URL):
            candidates.extend(
                model for model in extras if validate_model(provider_lower, model)
            )
        else:
            candidates.extend(extras)

    seen: set[str] = set()
    ordered: list[str] = []
    for model in candidates:
        if model and model not in seen:
            seen.add(model)
            ordered.append(model)
    return ordered
