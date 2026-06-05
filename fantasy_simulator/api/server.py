#!/usr/bin/env python3
"""Eldoria simulation API — Godot / Steam clients call this; rules stay in Python.

Run:
  cd fantasy_simulator
  pip install -r requirements-api.txt
  uvicorn api.server:app --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.session_store import SessionStore, package_root, turn_payload
from utils.temporal import TemporalMode

API_VERSION = 1
APP_NAME = "Eldoria Simulation API"

app = FastAPI(title=APP_NAME, version=str(API_VERSION))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_store = SessionStore()

Mode = Literal["rule", "llm", "hybrid"]
Temporal = Literal["classic", "nex", "precision"]


class NewSessionRequest(BaseModel):
    seed: Optional[int] = None
    mode: Mode = "rule"
    temporal_mode: Temporal = "classic"


class NewSessionResponse(BaseModel):
    api_version: int = API_VERSION
    session_id: str
    temporal_mode: str
    mode: str


class TurnRequest(BaseModel):
    session_id: str
    action: str = Field(..., min_length=1, max_length=512)
    temporal_mode: Optional[Temporal] = None
    time_scale: float = Field(1.0, ge=0.0, le=10.0)
    mode: Optional[Mode] = None
    enemy_id: Optional[str] = None


class HealthResponse(BaseModel):
    api_version: int
    status: str
    package_root: str


@app.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        api_version=API_VERSION,
        status="ok",
        package_root=str(package_root()),
    )


@app.post("/v1/session/new", response_model=NewSessionResponse)
def new_session(body: NewSessionRequest) -> NewSessionResponse:
    session_id, _ = _store.create(
        seed=body.seed,
        mode=body.mode,
        temporal_mode=body.temporal_mode,
    )
    return NewSessionResponse(
        session_id=session_id,
        temporal_mode=body.temporal_mode,
        mode=body.mode,
    )


@app.get("/v1/session/{session_id}/status")
def session_status(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "report": session.status_report(),
        "world": session.state.get("world", {}),
    }


@app.post("/v1/turn")
def run_turn(body: TurnRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    temporal: TemporalMode = (
        body.temporal_mode
        if body.temporal_mode is not None
        else session.default_temporal_mode
    )
    if body.mode is not None:
        session.mode = body.mode

    result = session.run_turn(
        action=body.action,
        enemy_id=body.enemy_id,
        temporal_mode=temporal,
        time_scale=body.time_scale,
    )
    payload = turn_payload(session, result)
    payload["session_id"] = body.session_id
    return payload


@app.delete("/v1/session/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    if not _store.delete(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    return {"status": "deleted", "session_id": session_id}
