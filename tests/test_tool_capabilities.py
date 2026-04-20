from tradingagents.llm_clients.capabilities import (
    HOST_MANAGED_TOOLS,
    NATIVE_TOOLS,
    resolve_model_fallback_chain,
    resolve_tool_execution_mode,
)


def test_custom_openai_gateway_prefers_host_managed_tools():
    assert (
        resolve_tool_execution_mode("openai", "https://gateway.example/v1")
        == HOST_MANAGED_TOOLS
    )


def test_official_openai_prefers_native_tools():
    assert (
        resolve_tool_execution_mode("openai", "https://api.openai.com/v1")
        == NATIVE_TOOLS
    )


def test_custom_gateway_fallback_chain_adds_backup_models():
    assert resolve_model_fallback_chain(
        "openai",
        "gpt-5.2",
        "https://gateway.example/v1",
    ) == ["gpt-5.2", "gpt-5.3-codex-spark", "gemma-4-31b"]


def test_official_openai_fallback_chain_stays_on_primary_model():
    assert resolve_model_fallback_chain(
        "openai",
        "gpt-5.2",
        "https://api.openai.com/v1",
    ) == ["gpt-5.2"]
