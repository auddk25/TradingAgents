from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from tradingagents.web.models import SubmissionPayload, SubmissionRecord, new_submission_id


def get_web_runs_dir() -> Path:
    return Path.cwd() / "web_runs"


def write_json_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def create_run_dir(payload: SubmissionPayload, run_id: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return get_web_runs_dir() / payload.ticker / payload.analysis_date.isoformat() / f"{timestamp}_{run_id}"


def save_submission(payload: SubmissionPayload) -> SubmissionRecord:
    runs_dir = get_web_runs_dir()
    runs_dir.mkdir(parents=True, exist_ok=True)

    submission_id = new_submission_id()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = runs_dir / f"{timestamp}_{submission_id}.json"

    normalized_payload = payload.model_dump(mode="json")
    write_json_file(path, normalized_payload)

    return SubmissionRecord(
        submission_id=submission_id,
        saved_path=str(path),
        payload=payload,
    )
