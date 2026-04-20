from __future__ import annotations

from datetime import date
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from cli.models import AnalystType
from cli.utils import ANALYST_ORDER
from tradingagents.default_config import get_provider_base_url
from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS, get_model_options

SUPPORTED_PROVIDERS = (
    "openai",
    "google",
    "anthropic",
    "xai",
    "deepseek",
    "qwen",
    "glm",
    "openrouter",
    "azure",
    "ollama",
)

PROVIDER_LABELS = {
    "openai": "OpenAI",
    "google": "Google",
    "anthropic": "Anthropic",
    "xai": "xAI",
    "deepseek": "DeepSeek",
    "qwen": "Qwen",
    "glm": "GLM",
    "openrouter": "OpenRouter",
    "azure": "Azure OpenAI",
    "ollama": "Ollama",
}

RESEARCH_DEPTH_OPTIONS = [
    {"label": "浅度 - 快速研究，较少辩论和策略讨论轮次", "value": 1},
    {"label": "中等 - 平衡研究深度与讨论轮次", "value": 3},
    {"label": "深度 - 全面研究，包含更深入的辩论和策略讨论", "value": 5},
]

OUTPUT_LANGUAGE_OPTIONS = [
    {"label": "英文", "value": "English"},
    {"label": "中文", "value": "Chinese"},
    {"label": "日文", "value": "Japanese"},
    {"label": "韩文", "value": "Korean"},
    {"label": "印地语", "value": "Hindi"},
    {"label": "西班牙语", "value": "Spanish"},
    {"label": "葡萄牙语", "value": "Portuguese"},
    {"label": "法语", "value": "French"},
    {"label": "德语", "value": "German"},
    {"label": "阿拉伯语", "value": "Arabic"},
    {"label": "俄语", "value": "Russian"},
]

ANALYST_LABELS = {
    "market": "市场分析师",
    "social": "社交媒体分析师",
    "news": "新闻分析师",
    "fundamentals": "基本面分析师",
}

MODEL_LABEL_TRANSLATIONS = {
    "Fast, strong coding and tool use": "快速，擅长代码与工具调用",
    "Cheapest, high-volume tasks": "成本最低，适合高频任务",
    "Latest frontier, 1M context": "最新前沿模型，支持 1M 上下文",
    "Smartest non-reasoning model": "最强非推理模型",
    "Strong reasoning, cost-effective": "推理能力强，性价比高",
    "Most capable, expensive ($30/$180 per 1M tokens)": "能力最强，成本最高（$30/$180 每百万 tokens）",
    "Best speed and intelligence balance": "速度与智能的最佳平衡",
    "Fast, near-instant responses": "响应极快，接近即时",
    "Agents and coding": "适合代理任务与编码",
    "Most intelligent, agents and coding": "最强智能，适合代理任务与编码",
    "Premium, max intelligence": "高阶版本，智能上限最高",
    "Next-gen fast": "新一代快速模型",
    "Balanced, stable": "均衡稳定",
    "Most cost-efficient": "成本效率最高",
    "Fast, low-cost": "快速且低成本",
    "Reasoning-first, complex workflows": "以推理为先，适合复杂流程",
    "Stable pro model": "稳定的专业模型",
    "Flagship model": "旗舰模型",
    "Speed optimized, 2M ctx": "速度优化，2M 上下文",
    "Speed optimized": "速度优化",
    "High-performance, 2M ctx": "高性能，2M 上下文",
    "High-performance": "高性能",
    "Custom model ID": "自定义模型 ID",
    "Custom deployment name": "自定义部署名称",
}


def translate_model_label(label: str) -> str:
    if label in MODEL_LABEL_TRANSLATIONS:
        return MODEL_LABEL_TRANSLATIONS[label]
    if " - " in label:
        prefix, suffix = label.split(" - ", 1)
        return f"{prefix} - {MODEL_LABEL_TRANSLATIONS.get(suffix, suffix)}"
    return label


class SubmissionPayload(BaseModel):
    ticker: str = Field(min_length=1)
    analysis_date: date
    output_language: str = "English"
    analysts: list[AnalystType]
    research_depth: Literal[1, 3, 5] = 1
    llm_provider: Literal[
        "openai",
        "google",
        "anthropic",
        "xai",
        "deepseek",
        "qwen",
        "glm",
        "openrouter",
        "azure",
        "ollama",
    ] = "openai"
    backend_url: str | None = None
    quick_think_llm: str
    deep_think_llm: str
    google_thinking_level: str | None = None
    openai_reasoning_effort: str | None = None
    anthropic_effort: str | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("analysts")
    @classmethod
    def require_analysts(cls, value: list[AnalystType]) -> list[AnalystType]:
        if not value:
            raise ValueError("At least one analyst must be selected.")
        return value


class SubmissionRecord(BaseModel):
    submission_id: str
    saved_path: str
    payload: SubmissionPayload


class RunEvent(BaseModel):
    event: str
    step: str | None = None
    message: str
    timestamp: str
    data: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    run_id: str
    status: Literal["queued", "running", "completed", "failed"]
    run_dir: str
    current_step: str | None = None
    report_path: str | None = None
    error_path: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None


class FormOptionsResponse(BaseModel):
    defaults: dict
    options: dict


def build_form_options() -> FormOptionsResponse:
    provider_options = [
        {
            "label": PROVIDER_LABELS[provider],
            "value": provider,
            "backend_url": get_provider_base_url(provider),
        }
        for provider in SUPPORTED_PROVIDERS
    ]
    analyst_options = [
        {"label": ANALYST_LABELS[analyst.value], "value": analyst.value}
        for _, analyst in ANALYST_ORDER
    ]
    model_options = {
        provider: {
            mode: [{"label": translate_model_label(label), "value": value} for label, value in options]
            for mode, options in mode_map.items()
        }
        for provider, mode_map in MODEL_OPTIONS.items()
    }
    model_options["azure"] = {
        "quick": [{"label": "自定义部署名称", "value": ""}],
        "deep": [{"label": "自定义部署名称", "value": ""}],
    }
    model_options["openrouter"] = {
        "quick": [{"label": "自定义模型 ID", "value": ""}],
        "deep": [{"label": "自定义模型 ID", "value": ""}],
    }
    defaults = {
        "ticker": "SPY",
        "analysis_date": date.today().isoformat(),
        "output_language": "English",
        "analysts": [analyst.value for _, analyst in ANALYST_ORDER],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": get_provider_base_url("openai"),
        "quick_think_llm": get_model_options("openai", "quick")[0][1],
        "deep_think_llm": get_model_options("openai", "deep")[0][1],
        "google_thinking_level": "high",
        "openai_reasoning_effort": "medium",
        "anthropic_effort": "high",
    }
    return FormOptionsResponse(
        defaults=defaults,
        options={
            "providers": provider_options,
            "analysts": analyst_options,
            "research_depths": RESEARCH_DEPTH_OPTIONS,
            "output_languages": OUTPUT_LANGUAGE_OPTIONS,
            "model_options": model_options,
            "google_thinking_levels": [
                {"label": "高", "value": "high"},
                {"label": "最小", "value": "minimal"},
            ],
            "openai_reasoning_efforts": [
                {"label": "中等", "value": "medium"},
                {"label": "高", "value": "high"},
                {"label": "低", "value": "low"},
            ],
            "anthropic_efforts": [
                {"label": "高", "value": "high"},
                {"label": "中等", "value": "medium"},
                {"label": "低", "value": "low"},
            ],
        },
    )


def new_submission_id() -> str:
    return uuid4().hex
