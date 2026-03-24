from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine

from db.sqlite.bootstrap import default_seed_dir, default_sqlite_path, ensure_sqlite_database

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_agent_client import (
    default_runs_parent_dir,
    load_cached_access_token,
    save_access_token,
    token_file_path,
)
from scripts.trading_run_store import ensure_trading_agent_runs_schema


PLACEHOLDER_TOKEN_MARKERS = (
    "your-token",
    "your-secret",
    "your-fintools",
    "placeholder",
)


def _is_placeholder_token(token: str | None) -> bool:
    if not token:
        return False
    normalized = token.strip().lower()
    return any(marker in normalized for marker in PLACEHOLDER_TOKEN_MARKERS)


def resolve_runtime_token(access_token: str | None = None, require_token: bool = True) -> dict:
    runs_dir = default_runs_parent_dir()
    token_path = token_file_path(runs_dir)

    token_value = None
    token_source = None
    token_persisted = False

    if access_token:
        if _is_placeholder_token(access_token):
            raise RuntimeError("Invalid FINTOOLS access token: explicit placeholder token was provided.")
        save_access_token(runs_dir, access_token)
        token_value = access_token.strip()
        token_source = "explicit"
        token_persisted = True
    else:
        cached_token = load_cached_access_token(runs_dir)
        if cached_token:
            if _is_placeholder_token(cached_token):
                raise RuntimeError(
                    "Invalid FINTOOLS access token cache at {0}. Replace the placeholder token with a real cached token.".format(
                        token_path
                    )
                )
            token_value = cached_token.strip()
            token_source = "cache"
        else:
            env_token = os.environ.get("FINTOOLS_ACCESS_TOKEN")
            if env_token:
                if _is_placeholder_token(env_token):
                    raise RuntimeError("Invalid FINTOOLS access token: environment variable contains a placeholder token.")
                save_access_token(runs_dir, env_token)
                token_value = env_token.strip()
                token_source = "env"
                token_persisted = True

    if require_token and not token_value:
        raise RuntimeError(
            "Missing FINTOOLS access token. Provide a real token first; expected cache file: {0}".format(token_path)
        )

    return {
        "token": token_value,
        "token_ready": bool(token_value),
        "token_source": token_source,
        "token_persisted": token_persisted,
        "token_path": str(token_path),
        "runs_dir": str(runs_dir),
    }


def ensure_backtests_database_ready() -> Path:
    backtests_db_path = default_sqlite_path()
    backtests_db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{backtests_db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    try:
        ensure_sqlite_database(engine, seed_dir=default_seed_dir())
    finally:
        engine.dispose()
    return backtests_db_path


def ensure_runtime_ready(access_token: str | None = None, require_token: bool = True) -> dict:
    token_state = resolve_runtime_token(access_token=access_token, require_token=require_token)
    runtime_root = Path(token_state["runs_dir"]).parent
    runs_db_path = ensure_trading_agent_runs_schema()
    backtests_db_path = ensure_backtests_database_ready()

    return {
        "ready": bool(token_state["token_ready"]),
        "runtime_root": str(runtime_root),
        "runs_dir": token_state["runs_dir"],
        "token_path": token_state["token_path"],
        "token_ready": token_state["token_ready"],
        "token_source": token_state["token_source"],
        "token_persisted": token_state["token_persisted"],
        "runs_db_path": str(runs_db_path),
        "runs_db_ready": Path(runs_db_path).exists(),
        "backtests_db_path": str(backtests_db_path),
        "backtests_db_ready": Path(backtests_db_path).exists(),
    }
