import os

_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")

_PROVIDER_BASE_URLS = {
    "openai": ("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "google": ("GOOGLE_BASE_URL", None),
    "anthropic": ("ANTHROPIC_BASE_URL", "https://api.anthropic.com/"),
    "xai": ("XAI_BASE_URL", "https://api.x.ai/v1"),
    "deepseek": ("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "qwen": ("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"),
    "glm": ("GLM_BASE_URL", "https://api.z.ai/api/paas/v4/"),
    "openrouter": ("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    "azure": ("AZURE_OPENAI_ENDPOINT", None),
    "ollama": ("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
}


def get_provider_base_url(provider: str):
    env_key, default = _PROVIDER_BASE_URLS[provider.lower()]
    return os.getenv(env_key, default)


def resolve_provider_base_url(provider: str, configured_base_url=None):
    if configured_base_url:
        return configured_base_url
    return get_provider_base_url(provider)

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.join(_TRADINGAGENTS_HOME, "logs")),
    "data_cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", os.path.join(_TRADINGAGENTS_HOME, "cache")),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5.2",
    "backend_url": None,
    "tool_execution_mode": None,
    "llm_retry_attempts": 1,
    "llm_retry_base_delay": 0.75,
    "llm_request_min_interval": 0.2,
    "llm_request_jitter_max": 0.1,
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Output language for analyst reports and final decision
    # Internal agent debate stays in English for reasoning quality
    "output_language": "English",
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
}
