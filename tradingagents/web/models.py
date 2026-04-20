from __future__ import annotations

import os
from datetime import date
from typing import Any, Literal
from uuid import uuid4

from openai import AzureOpenAI, OpenAI
from openai import APIError, APIStatusError
from pydantic import BaseModel, Field, field_validator

from cli.models import AnalystType
from cli.utils import ANALYST_ORDER
from tradingagents.default_config import get_provider_base_url, resolve_provider_base_url
from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
from tradingagents.llm_clients.validators import validate_model

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

FIELD_HELP = {
    "research_depth": "控制研究团队和风险团队的讨论轮次，不是模型能力等级。",
    "main_model": "默认给整条链路使用。未展开高级选项时，快速模型和深度模型都跟随它。",
    "quick_think_llm": "给分析师、交易员、风险辩手等高频节点使用。",
    "deep_think_llm": "给研究经理和投资组合经理等最终裁决节点使用。",
    "google_thinking_level": "控制 Google 系列模型的单次思考预算。",
    "openai_reasoning_effort": "控制 OpenAI 推理调用的推理强度，不等于研究轮次。",
    "anthropic_effort": "控制 Anthropic 推理调用的思考强度，不等于研究轮次。",
}


class UnsupportedModelError(ValueError):
    pass


class TransientModelProbeError(ValueError):
    pass

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

_OPENAI_COMPATIBLE_PROVIDERS = {
    "openai",
    "xai",
    "deepseek",
    "qwen",
    "glm",
    "openrouter",
    "ollama",
}

_PROVIDER_API_KEY_ENVS = {
    "openai": "OPENAI_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "glm": "ZHIPU_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_RUNTIME_PROBE_TIMEOUT = 20.0
_RUNTIME_PROBE_PROMPT = [{"role": "user", "content": "Reply with OK."}]


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
    field_help: dict[str, str]


def _build_main_model_options(provider: str, model_options: dict) -> list[dict[str, str]]:
    main_options: list[dict[str, str]] = []
    seen_values: set[str] = set()

    for mode in ("quick", "deep"):
        for option in model_options.get(mode, []):
            value = str(option.get("value", ""))
            if value in seen_values:
                continue
            seen_values.add(value)
            main_options.append(option)

    return main_options


def _read_provider_api_key(provider: str) -> str | None:
    env_key = _PROVIDER_API_KEY_ENVS.get(provider.lower())
    if env_key is None:
        return None
    return os.getenv(env_key)


def _raise_probe_failure(field_label: str, model: str, detail: str) -> None:
    normalized_detail = detail.strip()
    detail_lower = normalized_detail.lower()

    if "model_not_found" in detail_lower or "no available distributor" in detail_lower:
        reason = "当前网关不支持这个模型"
    elif "api key" in detail_lower or "unauthorized" in detail_lower or "authentication" in detail_lower:
        reason = "API 密钥无效或未配置"
    elif "timeout" in detail_lower:
        reason = "运行前探测超时"
    elif (
        "502" in detail_lower
        or "503" in detail_lower
        or "internal_server_error" in detail_lower
        or "unknown provider" in detail_lower
        or "rate limit" in detail_lower
        or "temporarily unavailable" in detail_lower
    ):
        reason = "运行前探测遇到瞬时网关错误"
        raise TransientModelProbeError(
            f"模型探测警告：{model}。{reason}，将交给运行时容错继续处理。"
            f"\n{field_label}原始错误：{normalized_detail}"
        )
    else:
        reason = "运行前探测失败"

    raise UnsupportedModelError(
        f"模型不可用：{model}。{reason}，请改用其他模型或检查当前提供方配置。"
        f"\n{field_label}原始错误：{normalized_detail}"
    )


def _probe_openai_compatible_runtime(payload: SubmissionPayload, model: str, field_label: str) -> None:
    provider = payload.llm_provider.lower()
    api_key = _read_provider_api_key(provider)
    base_url = resolve_provider_base_url(provider, payload.backend_url)

    if provider != "ollama" and not api_key:
        raise UnsupportedModelError(
            f"模型不可用：{model}。缺少 { _PROVIDER_API_KEY_ENVS[provider] }，无法完成运行前探测。"
        )

    client = OpenAI(
        api_key=api_key or "ollama",
        base_url=base_url,
        timeout=_RUNTIME_PROBE_TIMEOUT,
    )
    try:
        client.chat.completions.create(
            model=model,
            messages=_RUNTIME_PROBE_PROMPT,
            max_tokens=1,
        )
    except (APIStatusError, APIError) as exc:
        _raise_probe_failure(field_label, model, str(exc))
    except Exception as exc:  # pragma: no cover - defensive mapping
        _raise_probe_failure(field_label, model, str(exc))


def _probe_azure_runtime(payload: SubmissionPayload, model: str, field_label: str) -> None:
    azure_endpoint = resolve_provider_base_url("azure", payload.backend_url)
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("OPENAI_API_VERSION", "2025-03-01-preview")

    if not azure_endpoint:
        raise UnsupportedModelError(
            f"模型不可用：{model}。缺少 AZURE_OPENAI_ENDPOINT，无法完成运行前探测。"
        )
    if not api_key:
        raise UnsupportedModelError(
            f"模型不可用：{model}。缺少 AZURE_OPENAI_API_KEY，无法完成运行前探测。"
        )

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        timeout=_RUNTIME_PROBE_TIMEOUT,
    )
    try:
        client.chat.completions.create(
            model=model,
            messages=_RUNTIME_PROBE_PROMPT,
            max_tokens=1,
        )
    except (APIStatusError, APIError) as exc:
        _raise_probe_failure(field_label, model, str(exc))
    except Exception as exc:  # pragma: no cover - defensive mapping
        _raise_probe_failure(field_label, model, str(exc))


def probe_runtime_model_availability(payload: SubmissionPayload, model: str, field_label: str) -> None:
    provider = payload.llm_provider.lower()

    if provider in _OPENAI_COMPATIBLE_PROVIDERS:
        _probe_openai_compatible_runtime(payload, model, field_label)
        return

    if provider == "azure":
        _probe_azure_runtime(payload, model, field_label)
        return


def preflight_validate_submission(payload: SubmissionPayload) -> None:
    checked_models: set[str] = set()
    for field_label, model in (
        ("快速模型", payload.quick_think_llm),
        ("深度模型", payload.deep_think_llm),
    ):
        normalized_model = model.strip()
        if not normalized_model:
            raise UnsupportedModelError(f"{field_label}不能为空。")
        if not validate_model(payload.llm_provider, normalized_model):
            raise UnsupportedModelError(
                f"模型不可用：{normalized_model}。当前网关不支持这个模型，请改用 gpt-5.4 或检查网关配置。"
            )
        if normalized_model in checked_models:
            continue
        checked_models.add(normalized_model)
        try:
            probe_runtime_model_availability(payload, normalized_model, field_label)
        except TransientModelProbeError as exc:
            print(f"[preflight-warning] {exc}")


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
    for provider, provider_mode_options in model_options.items():
        provider_mode_options["main"] = _build_main_model_options(provider, provider_mode_options)
    model_options["azure"] = {
        "quick": [{"label": "自定义部署名称", "value": ""}],
        "deep": [{"label": "自定义部署名称", "value": ""}],
        "main": [{"label": "自定义部署名称", "value": ""}],
    }
    model_options["openrouter"] = {
        "quick": [{"label": "自定义模型 ID", "value": ""}],
        "deep": [{"label": "自定义模型 ID", "value": ""}],
        "main": [{"label": "自定义模型 ID", "value": ""}],
    }
    defaults = {
        "ticker": "SPY",
        "analysis_date": date.today().isoformat(),
        "output_language": "English",
        "analysts": [analyst.value for _, analyst in ANALYST_ORDER],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": get_provider_base_url("openai"),
        "main_model": "gpt-5.2",
        "quick_think_llm": "gpt-5.2",
        "deep_think_llm": "gpt-5.2",
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
        field_help=FIELD_HELP,
    )


def new_submission_id() -> str:
    return uuid4().hex
