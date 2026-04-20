from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


SUMMARY_ROOT_NAME = "memory_runs"
SUMMARY_REFLECTION = (
    "This prior summary is reference only. "
    "If current evidence conflicts with the summary, prefer current evidence."
)
SUMMARY_SECTION_HEADINGS = [
    "Rating",
    "Chinese Summary",
    "Short-Term View",
    "Long-Term Ownership View",
    "What The Market Is Pricing",
    "Gap Between Price And Future Path",
    "Risk Triggers",
    "Future Business Path",
    "What Could Beat Expectations",
    "What Could Miss Expectations",
    "Strategic Ownership View",
]


def normalize_ticker(ticker: str) -> str:
    """Normalize a ticker into a filesystem-safe directory name."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", (ticker or "").strip().upper())
    return safe or "UNKNOWN"


def get_memory_root(base_dir: Path | str | None = None) -> Path:
    """Return the root folder used for summary memory storage."""
    base_path = Path(base_dir) if base_dir is not None else Path.cwd()
    return base_path / SUMMARY_ROOT_NAME


def get_ticker_memory_dir(ticker: str, base_dir: Path | str | None = None) -> Path:
    """Return the ticker-scoped memory directory."""
    return get_memory_root(base_dir) / normalize_ticker(ticker)


def get_latest_summary_path(ticker: str, base_dir: Path | str | None = None) -> Path:
    return get_ticker_memory_dir(ticker, base_dir) / "latest_summary.md"


def get_summary_history_dir(ticker: str, base_dir: Path | str | None = None) -> Path:
    return get_ticker_memory_dir(ticker, base_dir) / "summaries"


def get_summary_snapshot_dir(ticker: str, base_dir: Path | str | None = None) -> Path:
    return get_ticker_memory_dir(ticker, base_dir) / "snapshots"


def load_latest_summary(ticker: str, base_dir: Path | str | None = None) -> str:
    """Load the current carry-forward summary for a ticker."""
    path = get_latest_summary_path(ticker, base_dir)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_latest_summary(
    ticker: str,
    summary_text: str,
    base_dir: Path | str | None = None,
) -> Path:
    """Write the current carry-forward summary for a ticker."""
    path = get_latest_summary_path(ticker, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary_text or "", encoding="utf-8")
    return path


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _truncate_words(text: str, limit: int = 24) -> str:
    compact = _compact_text(text)
    if not compact:
        return ""
    words = compact.split()
    if len(words) <= limit:
        return compact
    return " ".join(words[:limit]).rstrip(",;:") + "..."


def _match_heading(line: str, heading: str) -> bool:
    normalized = line.strip().lstrip("#").strip()
    normalized = re.sub(r"^\d+[\.)]\s*", "", normalized)
    normalized = re.sub(r"^[-*]\s*", "", normalized)
    lowered = normalized.lower()
    heading_lower = heading.lower()
    return lowered == heading_lower or lowered.startswith(f"{heading_lower}:")


def _extract_section(text: str, heading: str) -> str:
    if not text:
        return ""

    lines = text.splitlines()
    capture = False
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not capture:
            if _match_heading(stripped, heading):
                capture = True
                remainder = stripped.lstrip("#").strip()[len(heading):].lstrip(" :")
                if remainder:
                    collected.append(remainder)
            continue

        if any(_match_heading(stripped, other) for other in SUMMARY_SECTION_HEADINGS):
            break
        collected.append(stripped)

    return _compact_text("\n".join(collected))


def _first_nonempty(*values: str) -> str:
    for value in values:
        compact = _compact_text(value)
        if compact:
            return compact
    return ""


def build_run_summary(final_state: Mapping[str, Any]) -> str:
    """Create a short carry-forward summary from the final state."""
    final_decision = str(final_state.get("final_trade_decision", "") or "")
    trader_plan = str(final_state.get("trader_investment_plan", "") or "")

    investment_state = final_state.get("investment_debate_state", {}) or {}
    research_decision = str(investment_state.get("judge_decision", "") or "")

    risk_state = final_state.get("risk_debate_state", {}) or {}
    portfolio_decision = str(risk_state.get("judge_decision", "") or "")

    rating = _first_nonempty(
        _extract_section(final_decision, "Rating"),
        _extract_section(research_decision, "Rating"),
        _extract_section(portfolio_decision, "Rating"),
    )
    short_term = _first_nonempty(
        _extract_section(final_decision, "Short-Term View"),
        _extract_section(trader_plan, "tactical direction"),
        trader_plan,
    )
    long_term = _first_nonempty(
        _extract_section(final_decision, "Long-Term Ownership View"),
        _extract_section(research_decision, "Strategic Ownership View"),
        research_decision,
    )
    pricing = _first_nonempty(
        _extract_section(final_decision, "What The Market Is Pricing"),
        _extract_section(research_decision, "What The Market Is Pricing"),
    )
    key_risk = _first_nonempty(
        _extract_section(final_decision, "Risk Triggers"),
        _extract_section(final_decision, "Gap Between Price And Future Path"),
        _extract_section(research_decision, "What Could Miss Expectations"),
        _extract_section(portfolio_decision, "Risk Triggers"),
    )
    change_view = _first_nonempty(
        _extract_section(final_decision, "Gap Between Price And Future Path"),
        _extract_section(research_decision, "What Could Beat Expectations"),
    )

    bullets = []
    if rating:
        bullets.append(f"- Rating: {_truncate_words(rating, 12)}")
    if short_term:
        bullets.append(f"- Short-term action: {_truncate_words(short_term, 20)}")
    if long_term:
        bullets.append(f"- Long-term view: {_truncate_words(long_term, 20)}")
    if pricing:
        bullets.append(f"- Market pricing: {_truncate_words(pricing, 20)}")
    if key_risk:
        bullets.append(f"- Key risk: {_truncate_words(key_risk, 18)}")
    if change_view:
        bullets.append(f"- What changes the view: {_truncate_words(change_view, 18)}")

    return "\n".join(bullets).strip()


def build_reference_summary_block(summary_text: str) -> str:
    """Format the prior summary as prompt reference text."""
    summary = _compact_text(summary_text)
    if not summary:
        return ""
    return (
        "Prior run summary (reference only):\n"
        f"{summary}\n\n"
        f"{SUMMARY_REFLECTION}"
    )


def persist_summary_memory(
    ticker: str,
    summary_text: str,
    *,
    metadata: Mapping[str, Any] | None = None,
    base_dir: Path | str | None = None,
    timestamp: str | None = None,
) -> dict[str, Path]:
    """Write latest, historical, and snapshot summary artifacts for a ticker."""
    normalized_ticker = normalize_ticker(ticker)
    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    summary = summary_text or ""
    ticker_dir = get_ticker_memory_dir(normalized_ticker, base_dir)
    history_dir = get_summary_history_dir(normalized_ticker, base_dir)
    snapshot_dir = get_summary_snapshot_dir(normalized_ticker, base_dir)
    ticker_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    latest_path = get_latest_summary_path(normalized_ticker, base_dir)
    latest_path.write_text(summary, encoding="utf-8")

    summary_path = history_dir / f"{stamp}.md"
    summary_path.write_text(summary, encoding="utf-8")

    snapshot_payload: dict[str, Any] = {
        "ticker": normalized_ticker,
        "timestamp": stamp,
        "summary_text": summary,
    }
    if metadata:
        snapshot_payload.update(dict(metadata))

    snapshot_path = snapshot_dir / f"{stamp}.json"
    snapshot_path.write_text(
        json.dumps(snapshot_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "latest_summary": latest_path,
        "summary": summary_path,
        "snapshot": snapshot_path,
    }
