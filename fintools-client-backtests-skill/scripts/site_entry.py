#!/usr/bin/env python3
"""Thin entrypoint for the fixed FinTools website."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

import discover_public_site


SITE_URL = "https://warranties-movies-host-repository.trycloudflare.com/"
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
        choices=["resources", "agents", "skills", "stocks", "run-agent"],
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
    result = run_agent(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
