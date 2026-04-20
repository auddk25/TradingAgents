from __future__ import annotations

from langchain_core.messages import AIMessage

from tradingagents.llm_clients.resilience import wrap_llm_with_resilience


class DummyLLM:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)

    def invoke(self, input, config=None, **kwargs):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def bind_tools(self, tools):
        return self


def test_resilient_llm_retries_transient_failure_then_succeeds():
    models = {
        "gpt-5.2": DummyLLM([RuntimeError("502 bad gateway"), AIMessage(content="ok", tool_calls=[])]),
    }
    llm = wrap_llm_with_resilience(
        provider="openai",
        primary_model="gpt-5.2",
        fallback_models=["gpt-5.2"],
        llm_factory=models.__getitem__,
        gate_key="test-gateway",
        max_retries=1,
        base_delay=0.0,
        min_interval=0.0,
        jitter_max=0.0,
    )

    result = llm.invoke("hello")

    assert result.content == "ok"


def test_resilient_llm_falls_back_to_next_model_after_routing_error():
    models = {
        "gpt-5.2": DummyLLM([RuntimeError("502 unknown provider for model gpt-5.2")]),
        "grok-4": DummyLLM([AIMessage(content="fallback ok", tool_calls=[])]),
    }
    llm = wrap_llm_with_resilience(
        provider="openai",
        primary_model="gpt-5.2",
        fallback_models=["gpt-5.2", "grok-4"],
        llm_factory=models.__getitem__,
        gate_key="test-gateway",
        max_retries=0,
        base_delay=0.0,
        min_interval=0.0,
        jitter_max=0.0,
    )

    result = llm.invoke("hello")

    assert result.content == "fallback ok"


def test_resilient_llm_treats_empty_response_as_failure_and_falls_back():
    models = {
        "gpt-5.2": DummyLLM([AIMessage(content="", tool_calls=[])]),
        "grok-4": DummyLLM([AIMessage(content="non-empty", tool_calls=[])]),
    }
    llm = wrap_llm_with_resilience(
        provider="openai",
        primary_model="gpt-5.2",
        fallback_models=["gpt-5.2", "grok-4"],
        llm_factory=models.__getitem__,
        gate_key="test-gateway",
        max_retries=0,
        base_delay=0.0,
        min_interval=0.0,
        jitter_max=0.0,
    )

    result = llm.invoke("hello")

    assert result.content == "non-empty"
