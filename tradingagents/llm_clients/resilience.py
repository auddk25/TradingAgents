from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class EmptyLLMResponseError(RuntimeError):
    """Raised when a model returns neither text nor tool calls."""


@dataclass
class _RequestGate:
    lock: threading.Lock
    last_started_at: float = 0.0


_GATES: dict[str, _RequestGate] = {}
_GATES_LOCK = threading.Lock()


def _get_gate(key: str) -> _RequestGate:
    with _GATES_LOCK:
        gate = _GATES.get(key)
        if gate is None:
            gate = _RequestGate(lock=threading.Lock())
            _GATES[key] = gate
        return gate


def _stringify_exception(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}".lower()


def _is_retryable_error(exc: Exception) -> bool:
    text = _stringify_exception(exc)
    retry_markers = (
        "429",
        "502",
        "503",
        "rate limit",
        "timeout",
        "timed out",
        "connection reset",
        "connection aborted",
        "temporarily unavailable",
        "unknown provider",
        "model_not_found",
        "internal_server_error",
        "emptyllmresponseerror",
    )
    return any(marker in text for marker in retry_markers)


def _has_meaningful_response(result: Any) -> bool:
    tool_calls = getattr(result, "tool_calls", None) or []
    content = str(getattr(result, "content", "") or "").strip()
    return bool(tool_calls) or bool(content)


class ResilientLLM:
    def __init__(
        self,
        *,
        provider: str,
        primary_model: str,
        fallback_models: list[str],
        llm_factory: Callable[[str], Any],
        gate_key: str,
        max_retries: int = 1,
        base_delay: float = 0.75,
        min_interval: float = 0.2,
        jitter_max: float = 0.1,
    ):
        self.provider = provider
        self.primary_model = primary_model
        self.fallback_models = fallback_models
        self.llm_factory = llm_factory
        self.gate_key = gate_key
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.min_interval = min_interval
        self.jitter_max = jitter_max
        self._llm_cache: dict[str, Any] = {}

    def _get_llm(self, model: str) -> Any:
        if model not in self._llm_cache:
            self._llm_cache[model] = self.llm_factory(model)
        return self._llm_cache[model]

    def _apply_buffer(self) -> None:
        gate = _get_gate(self.gate_key)
        with gate.lock:
            now = time.monotonic()
            wait_for = self.min_interval - (now - gate.last_started_at)
            if wait_for > 0:
                time.sleep(wait_for + random.uniform(0.0, self.jitter_max))
            gate.last_started_at = time.monotonic()

    def _log(self, message: str) -> None:
        print(f"[llm-resilience] {message}")

    def _invoke_once(self, model: str, input: Any, config=None, tools=None, **kwargs):
        llm = self._get_llm(model)
        if tools is not None:
            llm = llm.bind_tools(tools)
        self._apply_buffer()
        result = llm.invoke(input, config=config, **kwargs)
        if not _has_meaningful_response(result):
            raise EmptyLLMResponseError(f"Empty response from model {model}")
        return result

    def _invoke_with_resilience(self, input: Any, config=None, tools=None, **kwargs):
        last_exc: Exception | None = None

        for model_index, model in enumerate(self.fallback_models):
            for attempt in range(self.max_retries + 1):
                try:
                    result = self._invoke_once(model, input, config=config, tools=tools, **kwargs)
                    if model != self.primary_model or attempt > 0:
                        self._log(
                            f"provider={self.provider} model={self.primary_model} "
                            f"resolved_with={model} attempt={attempt + 1}"
                        )
                    return result
                except Exception as exc:  # pragma: no cover - exercised through tests
                    last_exc = exc
                    retryable = _is_retryable_error(exc)
                    has_more_attempts = attempt < self.max_retries
                    has_more_models = model_index < len(self.fallback_models) - 1
                    self._log(
                        f"provider={self.provider} model={model} attempt={attempt + 1} failed: {exc}"
                    )

                    if retryable and has_more_attempts:
                        time.sleep(self.base_delay * (2**attempt))
                        continue

                    if retryable and has_more_models:
                        self._log(
                            f"provider={self.provider} switching fallback model "
                            f"{model} -> {self.fallback_models[model_index + 1]}"
                        )
                        break

                    raise

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("ResilientLLM exhausted without a result.")

    def invoke(self, input: Any, config=None, **kwargs):
        return self._invoke_with_resilience(input, config=config, **kwargs)

    def bind_tools(self, tools):
        return _ResilientToolBoundLLM(self, tools)


class _ResilientToolBoundLLM:
    def __init__(self, parent: ResilientLLM, tools):
        self.parent = parent
        self.tools = tools

    def invoke(self, input: Any, config=None, **kwargs):
        return self.parent._invoke_with_resilience(input, config=config, tools=self.tools, **kwargs)


def wrap_llm_with_resilience(
    *,
    provider: str,
    primary_model: str,
    fallback_models: list[str],
    llm_factory: Callable[[str], Any],
    gate_key: str,
    max_retries: int,
    base_delay: float,
    min_interval: float,
    jitter_max: float,
) -> ResilientLLM:
    return ResilientLLM(
        provider=provider,
        primary_model=primary_model,
        fallback_models=fallback_models,
        llm_factory=llm_factory,
        gate_key=gate_key,
        max_retries=max_retries,
        base_delay=base_delay,
        min_interval=min_interval,
        jitter_max=jitter_max,
    )
