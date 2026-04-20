from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator
import time

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from tradingagents.web.models import FormOptionsResponse, RunEvent, RunRecord, SubmissionPayload, SubmissionRecord, build_form_options
from tradingagents.web.runner import get_run, start_run
from tradingagents.web.storage import save_submission

STATIC_DIR = Path(__file__).parent / "static"

load_dotenv()
load_dotenv(".env.enterprise", override=False)

app = FastAPI(title="TradingAgents Web MVP")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<html><body><h1>TradingAgents Web MVP</h1></body></html>")


@app.get("/api/form-options", response_model=FormOptionsResponse)
def get_form_options():
    return build_form_options()


@app.post("/api/submissions", response_model=SubmissionRecord)
def create_submission(payload: SubmissionPayload):
    return save_submission(payload)


@app.post("/api/runs", response_model=RunRecord)
def create_run(payload: SubmissionPayload):
    return start_run(payload).to_record()


@app.get("/api/runs/{run_id}", response_model=RunRecord)
def get_run_status(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run.to_record()


def encode_sse_event(event: RunEvent) -> str:
    payload = {
        "event": event.event,
        "step": event.step,
        "message": event.message,
        "timestamp": event.timestamp,
        **event.data,
    }
    return f"event: {event.event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def stream_run_events(run_id: str) -> Iterator[str]:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    sent = 0
    while True:
        while sent < len(run.events):
            event = run.events[sent]
            sent += 1
            yield encode_sse_event(event)

        if run.status in {"completed", "failed"}:
            break
        time.sleep(0.1)


@app.get("/api/runs/{run_id}/events")
def get_run_events(run_id: str):
    return StreamingResponse(stream_run_events(run_id), media_type="text/event-stream")


def main():
    uvicorn.run(
        "tradingagents.web.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
