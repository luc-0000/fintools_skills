from __future__ import annotations

import os
import sys
from pathlib import Path

from db.sqlite.bootstrap import default_sqlite_path

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


def ensure_runtime_ready(access_token: str | None = None, require_token: bool = True) -> dict:
    runs_dir = default_runs_parent_dir()
    token_path = token_file_path(runs_dir)
    runtime_root = Path(runs_dir).parent
    runs_db_path = ensure_trading_agent_runs_schema()
    backtests_db_path = default_sqlite_path()

    token_value = None
    token_source = None

    if access_token:
        if _is_placeholder_token(access_token):
            raise RuntimeError("Invalid FINTOOLS access token: explicit placeholder token was provided.")
        save_access_token(runs_dir, access_token)
        token_value = access_token.strip()
        token_source = "request"
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

    if require_token and not token_value:
        raise RuntimeError(
            "Missing FINTOOLS access token. Provide a real token first; expected cache file: {0}".format(token_path)
        )

    return {
        "ready": bool(token_value),
        "runtime_root": str(runtime_root),
        "runs_dir": str(runs_dir),
        "token_path": str(token_path),
        "token_ready": bool(token_value),
        "token_source": token_source,
        "runs_db_path": str(runs_db_path),
        "runs_db_ready": Path(runs_db_path).exists(),
        "backtests_db_path": str(backtests_db_path),
        "backtests_db_ready": Path(backtests_db_path).exists(),
    }
