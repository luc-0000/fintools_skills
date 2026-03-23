#!/usr/bin/env python3

import json
import sqlite3
from datetime import datetime
from pathlib import Path
import zipfile
from uuid import uuid4


VALID_ACTIONS = {"buy", "sell", "hold"}
_ACTION_CONTEXT_MARKERS = (
    "决策结果",
    "action",
    "execution action",
    "compatible execution action",
)
_DECISION_TO_ACTION = {
    "long": "buy",
    "buy": "buy",
    "short": "sell",
    "sell": "sell",
    "hold": "hold",
    "neutral": "hold",
    "sideways": "hold",
}


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_database_dir() -> Path:
    path = skill_root() / ".runtime" / "database"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_trading_agent_runs_db_path() -> Path:
    return runtime_database_dir() / "trading_agent_runs.db"


def ensure_trading_agent_runs_schema(db_path: Path | str | None = None) -> Path:
    path = Path(db_path) if db_path is not None else default_trading_agent_runs_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trading_agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                stock_code TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('buy', 'sell', 'hold')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                raw_result TEXT,
                mode TEXT NOT NULL DEFAULT 'polling',
                agent_id TEXT,
                agent_name TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trading_agent_runs_stock_code
            ON trading_agent_runs (stock_code)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trading_agent_runs_created_at
            ON trading_agent_runs (created_at)
            """
        )
        conn.commit()
    finally:
        conn.close()

    return path


def _normalize_stock_code(stock_code: str) -> str:
    value = str(stock_code or "").strip()
    return value.split(".")[0] if "." in value else value


def _normalize_action_text(text: str | None) -> str | None:
    normalized = " ".join(str(text or "").strip().lower().split())
    if not normalized:
        return None

    if normalized in _DECISION_TO_ACTION:
        return _DECISION_TO_ACTION[normalized]

    if normalized in VALID_ACTIONS:
        return normalized

    has_action_context = any(marker in normalized for marker in _ACTION_CONTEXT_MARKERS)
    if not has_action_context:
        return None

    for action in ("buy", "sell", "hold"):
        if action in normalized:
            return action
    return None


def extract_trading_action(payload) -> str | None:
    if isinstance(payload, str):
        return _normalize_action_text(payload)

    if isinstance(payload, dict):
        final_decision = payload.get("final_decision")
        if isinstance(final_decision, dict):
            action = extract_trading_action(final_decision.get("decision"))
            if action:
                return action
        for key in ("action", "result", "text", "message", "raw_result"):
            if key not in payload:
                continue
            action = extract_trading_action(payload.get(key))
            if action:
                return action
        return None

    if isinstance(payload, (list, tuple)):
        for item in payload:
            action = extract_trading_action(item)
            if action:
                return action

    return None


def extract_trading_action_from_report_path(report_path: str | Path | None) -> str | None:
    if not report_path:
        return None

    path = Path(report_path)
    if not path.exists():
        return None

    if path.suffix.lower() == ".json":
        try:
            return extract_trading_action(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return None

    if path.suffix.lower() != ".zip":
        return None

    try:
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist(), reverse=True):
                if not name.lower().endswith(".json"):
                    continue
                try:
                    payload = json.loads(archive.read(name).decode("utf-8"))
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                    continue
                action = extract_trading_action(payload)
                if action:
                    return action
    except (OSError, zipfile.BadZipFile):
        return None

    return None


def serialize_raw_result(payload) -> str:
    if payload is None:
        return ""
    try:
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return str(payload)


def build_trading_run_id(agent_id: str | None = None, stock_code: str | None = None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    fragments = [timestamp]
    if agent_id:
        fragments.append(str(agent_id).strip())
    if stock_code:
        fragments.append(_normalize_stock_code(stock_code))
    fragments.append(uuid4().hex[:10])
    return "-".join(fragments)


def record_trading_agent_run(
    *,
    stock_code: str,
    mode: str,
    result,
    action: str | None = None,
    agent_id: str | None = None,
    agent_name: str | None = None,
    run_id: str | None = None,
    db_path: Path | str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> dict:
    normalized_stock_code = _normalize_stock_code(stock_code)
    if not normalized_stock_code:
        raise ValueError("stock_code is required")

    normalized_mode = str(mode or "").strip().lower() or "streaming"
    normalized_action = _normalize_action_text(action) or extract_trading_action(result)
    if normalized_action not in VALID_ACTIONS:
        raise ValueError("Trading action is missing or invalid.")

    created_at = created_at or datetime.now()
    updated_at = updated_at or created_at
    run_id = str(run_id or build_trading_run_id(agent_id=agent_id, stock_code=normalized_stock_code)).strip()
    if not run_id:
        raise ValueError("run_id is required")

    path = ensure_trading_agent_runs_schema(db_path)
    raw_result = serialize_raw_result(result)

    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            INSERT INTO trading_agent_runs
            (run_id, stock_code, action, created_at, updated_at, raw_result, mode, agent_id, agent_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                normalized_stock_code,
                normalized_action,
                created_at.isoformat(sep=" ", timespec="seconds"),
                updated_at.isoformat(sep=" ", timespec="seconds"),
                raw_result,
                normalized_mode,
                str(agent_id).strip() if agent_id is not None else None,
                str(agent_name).strip() if agent_name is not None else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "db_path": str(path),
        "run_id": run_id,
        "stock_code": normalized_stock_code,
        "action": normalized_action,
        "mode": normalized_mode,
        "agent_id": str(agent_id).strip() if agent_id is not None else None,
        "agent_name": str(agent_name).strip() if agent_name is not None else None,
        "created_at": created_at.isoformat(sep=" ", timespec="seconds"),
        "updated_at": updated_at.isoformat(sep=" ", timespec="seconds"),
        "raw_result": raw_result,
    }
