#!/usr/bin/env python3
"""Thin entrypoint for the fixed FinTools website."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib import error, request

import discover_public_site
from run_agent_client import default_runs_parent_dir, load_cached_access_token, token_file_path


SITE_URL = "https://warranties-movies-host-repository.trycloudflare.com/"
BACKTESTS_BASE_URL = "http://127.0.0.1:8888/api/v1"
SCRIPT_DIR = Path(__file__).resolve().parent
RUN_AGENT_CLIENT = SCRIPT_DIR / "run_agent_client.py"


def fail(message):
    raise SystemExit(message)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read resources from the fixed FinTools website or run one of its agents."
    )
    parser.add_argument(
        "action",
        choices=["resources", "agents", "skills", "stocks", "prepare-agent", "run-agent"],
        help="What to do on the fixed FinTools website.",
    )
    parser.add_argument("--agent", help="Agent id or name, for run-agent.")
    parser.add_argument("--stock-code", help="Stock code, for run-agent.")
    parser.add_argument(
        "--agent-type",
        choices=["trading", "deep_research"],
        help="Optional agent type override for run-agent.",
    )
    parser.add_argument(
        "--mode",
        default="streaming",
        choices=["streaming", "polling"],
        help="Execution mode for run-agent.",
    )
    parser.add_argument("--access-token")
    parser.add_argument("--work-dir")
    parser.add_argument("--task-id")
    parser.add_argument(
        "--backtests-base-url",
        default=BACKTESTS_BASE_URL,
        help="Backtests backend API base URL.",
    )
    return parser.parse_args()


def _discover(subject):
    args = argparse.Namespace(
        site_url=SITE_URL,
        subject=subject,
        repo_id=None,
        ticker=None,
        author=None,
        page=None,
        page_size=None,
        keyword=None,
    )
    return discover_public_site.run_query(args)


def summarize_resources():
    payload = _discover("resources")
    data = payload["data"]
    return {
        "site_url": SITE_URL.rstrip("/"),
        "service": data.get("service"),
        "capabilities": data.get("capabilities", {}),
        "public_data": data.get("public_data", []),
        "endpoints": [
            {
                "method": row.get("method"),
                "path": row.get("path"),
                "description": row.get("description"),
                "url": row.get("resolved_url"),
            }
            for row in data.get("endpoints", [])
        ],
    }


def summarize_items(subject, limit=None):
    payload = _discover(subject)
    items = payload["data"].get("items", payload["data"])
    result = []
    for item in items[:limit] if isinstance(items, list) and limit else items:
        if subject == "agents":
            result.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "category": item.get("agent_category"),
                    "market": item.get("market"),
                    "updated_at": item.get("updated_at"),
                    "a2a_url": item.get("a2a_url"),
                }
            )
        elif subject == "skills":
            result.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "updated_at": item.get("updated_at"),
                    "download_url": item.get("download_url"),
                }
            )
        elif subject == "stocks":
            result.append(
                {
                    "symbol": item.get("symbol"),
                    "name": item.get("name"),
                    "exchange": item.get("exchange"),
                }
            )
    return {"site_url": SITE_URL.rstrip("/"), subject: result}


def _normalize_text(value):
    return str(value or "").strip().lower()


def resolve_agent(agent_ref):
    if not agent_ref:
        fail("--agent is required for run-agent")

    payload = _discover("agents")
    items = payload["data"].get("items", [])
    ref = _normalize_text(agent_ref)

    exact_id = [item for item in items if str(item.get("id")) == ref]
    if exact_id:
        return exact_id[0]

    exact_name = [item for item in items if _normalize_text(item.get("name")) == ref]
    if exact_name:
        return exact_name[0]

    partial = [item for item in items if ref in _normalize_text(item.get("name"))]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        fail(
            "Multiple agents matched {0}: {1}".format(
                agent_ref,
                ", ".join("{0}:{1}".format(item.get("id"), item.get("name")) for item in partial),
            )
        )
    fail("Agent not found: {0}".format(agent_ref))


def infer_agent_type(agent_record, override=None):
    if override:
        return override
    category = _normalize_text(agent_record.get("agent_category"))
    if category == "deep_research":
        return "deep_research"
    return "trading"


def _request_json(url, method="GET", payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit("Request failed: {0} {1} -> {2}: {3}".format(method, url, exc.code, body))
    except error.URLError as exc:
        raise SystemExit("Request failed: {0} {1} -> {2}".format(method, url, exc.reason))
    return json.loads(body) if body else {}


def _api_url(base_url, path):
    return base_url.rstrip("/") + path


def _resolve_repo_local_token(args):
    explicit_token = args.access_token or os.environ.get("FINTOOLS_ACCESS_TOKEN")
    if explicit_token:
        return explicit_token, "explicit"

    runs_dir = default_runs_parent_dir()
    cached_token = load_cached_access_token(runs_dir)
    if cached_token:
        return cached_token, "cache"

    return None, str(token_file_path(runs_dir))


def ensure_backtests_runtime(args, require_token=False):
    backend_url = args.backtests_base_url.rstrip("/")
    access_token = args.access_token or os.environ.get("FINTOOLS_ACCESS_TOKEN")
    if require_token:
        token_value, token_source = _resolve_repo_local_token(args)
        if not token_value:
            fail(
                "Missing FINTOOLS access token before opening backtests UI. "
                "Ask the user for FINTOOLS_ACCESS_TOKEN from the FinTools profile page, "
                "save it to the current skill runtime, then retry. Expected cache file: {0}".format(token_source)
            )

    payload = {
        "require_token": require_token,
    }
    if access_token:
        payload["access_token"] = access_token

    readiness = _request_json(
        _api_url(backend_url, "/get_rule/runtime_ready"),
        method="POST",
        payload=payload,
    )
    return readiness.get("data", {})


def prepare_agent(args):
    agent_record = resolve_agent(args.agent)
    backend_url = args.backtests_base_url.rstrip("/")
    health = _request_json(_api_url(backend_url, "/health"))
    runtime_ready = ensure_backtests_runtime(args, require_token=True)
    ensure_payload = {
        "agent_id": str(agent_record.get("id")),
        "name": agent_record.get("name") or "Agent {0}".format(agent_record.get("id")),
        "description": "Remote trading agent {0}".format(agent_record.get("id")),
        "info": agent_record.get("a2a_url"),
    }
    ensure_result = _request_json(
        _api_url(backend_url, "/get_rule/rule/ensure_remote_agent"),
        method="POST",
        payload=ensure_payload,
    )
    pools_result = _request_json(
        _api_url(backend_url, "/get_rule/rule/agent/{0}/pools".format(agent_record.get("id"))),
        method="GET",
    )
    assigned_pool_ids = pools_result.get("data", {}).get("assigned_pool_ids", [])
    has_assigned_pool = bool(assigned_pool_ids)
    return {
        "site_url": SITE_URL.rstrip("/"),
        "backend": {
            "base_url": backend_url,
            "health": health,
        },
        "runtime_ready": runtime_ready,
        "agent": {
            "id": agent_record.get("id"),
            "name": agent_record.get("name"),
            "category": agent_record.get("agent_category"),
            "a2a_url": agent_record.get("a2a_url"),
        },
        "rule": ensure_result.get("data", {}),
        "pools": pools_result.get("data", {}),
        "has_assigned_pool": has_assigned_pool,
    }


def build_run_agent_command(args, agent_record):
    if not args.stock_code:
        fail("--stock-code is required for run-agent")

    command = [
        sys.executable,
        str(RUN_AGENT_CLIENT),
        "--agent-type",
        infer_agent_type(agent_record, args.agent_type),
        "--mode",
        args.mode,
        "--stock-code",
        args.stock_code,
        "--agent-url",
        agent_record["a2a_url"],
    ]
    if args.access_token:
        command.extend(["--access-token", args.access_token])
    if args.work_dir:
        command.extend(["--work-dir", args.work_dir])
    if args.task_id:
        command.extend(["--task-id", args.task_id])
    return command


def run_agent(args):
    agent_record = resolve_agent(args.agent)
    command = build_run_agent_command(args, agent_record)
    completed = subprocess.run(command, check=False)
    return {
        "site_url": SITE_URL.rstrip("/"),
        "agent": {
            "id": agent_record.get("id"),
            "name": agent_record.get("name"),
            "category": agent_record.get("agent_category"),
            "a2a_url": agent_record.get("a2a_url"),
        },
        "command": command,
        "exit_code": completed.returncode,
    }


def main():
    args = parse_args()
    if args.action == "resources":
        print(json.dumps(summarize_resources(), ensure_ascii=True, indent=2))
        return 0
    if args.action == "agents":
        print(json.dumps(summarize_items("agents"), ensure_ascii=True, indent=2))
        return 0
    if args.action == "skills":
        print(json.dumps(summarize_items("skills"), ensure_ascii=True, indent=2))
        return 0
    if args.action == "stocks":
        print(json.dumps(summarize_items("stocks", limit=100), ensure_ascii=True, indent=2))
        return 0
    if args.action == "prepare-agent":
        print(json.dumps(prepare_agent(args), ensure_ascii=True, indent=2))
        return 0
    result = run_agent(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
