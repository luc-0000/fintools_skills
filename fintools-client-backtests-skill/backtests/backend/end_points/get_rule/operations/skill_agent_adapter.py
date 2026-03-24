import asyncio
import io
import json
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from end_points.common.utils.runtime_readiness import resolve_runtime_token

RUN_AGENT_CLIENT_SCRIPT = REPO_ROOT / "scripts" / "run_agent_client.py"
SUMMARY_PATH_PATTERN = re.compile(r"^\[result\] Summary written to: (?P<path>.+)$")


def _resolve_token(access_token: str | None = None) -> str:
    token_state = resolve_runtime_token(access_token=access_token, require_token=True)
    return str(token_state["token"])


class _StreamingQueueWriter:
    def __init__(self, queue: asyncio.Queue):
        self._queue = queue
        self._buffer = ""

    def write(self, text):
        if not text:
            return
        self._buffer += str(text)
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip("\r")
            if line.strip():
                self._queue.put_nowait({"type": "streaming_text", "message": line})

    def flush(self):
        return

    def close(self):
        if self._buffer.strip():
            self._queue.put_nowait({"type": "streaming_text", "message": self._buffer.rstrip("\r")})
        self._buffer = ""


async def execute_trading_agent_via_skill(
    stock_code: str,
    agent_url: str,
    access_token: str | None = None,
    log_buffer: io.StringIO | None = None,
):
    lines: list[str] = []

    def _collect(line: str):
        lines.append(line)
        if log_buffer is not None:
            log_buffer.write(line + "\n")

    return await _run_trading_agent_via_script(
        stock_code=stock_code,
        agent_url=agent_url,
        access_token=access_token,
        on_line=_collect,
    )


async def stream_trading_agent_via_skill(
    stock_code: str,
    agent_url: str,
    access_token: str | None = None,
):
    queue: asyncio.Queue = asyncio.Queue()

    async def _runner():
        try:
            result = await _run_trading_agent_via_script(
                stock_code=stock_code,
                agent_url=agent_url,
                access_token=access_token,
                on_line=lambda line: queue.put_nowait({"type": "streaming_text", "message": line}),
            )
            await queue.put({"type": "result", "result": result})
        except Exception as exc:
            await queue.put({"type": "error", "error": exc})

    task = asyncio.create_task(_runner())
    try:
        while True:
            item = await queue.get()
            if item["type"] == "error":
                raise item["error"]
            yield item
            if item["type"] == "result":
                break
    finally:
        await task


def run_trading_agent_via_skill(
    stock_code: str,
    agent_url: str,
    access_token: str | None = None,
    log_buffer: io.StringIO | None = None,
):
    return asyncio.run(
        execute_trading_agent_via_skill(
            stock_code=stock_code,
            agent_url=agent_url,
            access_token=access_token,
            log_buffer=log_buffer,
        )
    )


def extract_trading_action(result) -> str | None:
    if not isinstance(result, dict):
        return None

    summary = result.get("summary")
    if isinstance(summary, dict):
        action = summary.get("action")
        if isinstance(action, str):
            normalized = action.strip().lower()
            if normalized in {"buy", "sell", "hold"}:
                return normalized

    payload = result.get("result")
    if isinstance(payload, dict):
        action = payload.get("action")
        if isinstance(action, str):
            normalized = action.strip().lower()
            if normalized in {"buy", "sell", "hold"}:
                return normalized

    return None


async def _run_trading_agent_via_script(
    *,
    stock_code: str,
    agent_url: str,
    access_token: str | None = None,
    on_line=None,
):
    token = _resolve_token(access_token)
    clean_stock_code = stock_code.split(".")[0] if "." in stock_code else stock_code
    env = os.environ.copy()
    env["FINTOOLS_ACCESS_TOKEN"] = token
    env["PYTHONUNBUFFERED"] = "1"

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        str(RUN_AGENT_CLIENT_SCRIPT),
        "--agent-type",
        "trading",
        "--mode",
        "streaming",
        "--stock-code",
        clean_stock_code,
        "--agent-url",
        agent_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )

    summary_path: Path | None = None
    output_lines: list[str] = []

    assert process.stdout is not None
    while True:
        raw_line = await process.stdout.readline()
        if not raw_line:
            break
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            continue
        output_lines.append(line)
        if on_line:
            on_line(line)
        match = SUMMARY_PATH_PATTERN.match(line)
        if match:
            summary_path = Path(match.group("path").strip())

    return_code = await process.wait()
    summary = None
    if summary_path and summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            summary = None

    result = {
        "success": return_code == 0,
        "exit_code": return_code,
        "summary": summary,
        "stdout": output_lines,
    }
    if isinstance(summary, dict):
        action = summary.get("action")
        if isinstance(action, str):
            result["result"] = {"action": action}
    return result
