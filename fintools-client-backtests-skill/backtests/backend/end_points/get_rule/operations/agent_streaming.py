import logging
from datetime import datetime
from typing import AsyncGenerator

from db.models import Rule
from end_points.common.const.consts import Trade
from end_points.get_rule.operations.agent_utils import (
    get_remote_rule_record,
    get_rule_execution_plan,
    persist_trading_result_and_sync,
)
from end_points.get_rule.operations.skill_agent_adapter import (
    extract_trading_action,
    stream_trading_agent_via_skill,
)

logger = logging.getLogger(__name__)


def _get_remote_agent_config(info: str) -> str:
    return info


async def stream_agent_execution(db, rule_id: int) -> AsyncGenerator[dict, None]:
    """Stream remote agent execution logs for all stocks in the rule's pools."""
    logger.info("=== Starting agent execution for rule_id=%s ===", rule_id)
    try:
        execution_plan = get_rule_execution_plan(db, rule_id)
        if not execution_plan.get("success"):
            event_type = "warning" if execution_plan.get("needs_pool") else "error"
            yield {"type": event_type, "message": execution_plan.get("message", "Execution plan failed")}
            return
        rule_record = execution_plan["rule"]

        yield {
            "type": "start",
            "message": f"Starting execution for rule: {rule_record.name} (ID: {rule_id})",
            "timestamp": datetime.now().isoformat(),
        }
        stock_list = execution_plan["stock_list"]

        yield {
            "type": "info",
            "message": f"Found {len(stock_list)} stocks to process",
            "stocks": stock_list,
        }

        for index, stock_code in enumerate(stock_list, 1):
            yield {
                "type": "stock_start",
                "message": f"[{index}/{len(stock_list)}] Processing {stock_code}...",
                "stock_code": stock_code,
                "progress": f"{index}/{len(stock_list)}",
            }
            try:
                async for log_entry in stream_remote_agent_logs(db, rule_id, stock_code):
                    yield log_entry
            except Exception as exc:
                logger.exception("Error processing stock %s", stock_code)
                yield {
                    "type": "stock_error",
                    "message": f"✗ {stock_code}: {exc}",
                    "stock_code": stock_code,
                    "error": str(exc),
                }

        yield {
            "type": "complete",
            "message": f"Execution complete for rule {rule_id}",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as exc:
        logger.exception("Error in stream_agent_execution")
        yield {"type": "error", "message": f"Fatal error: {exc}"}


async def stream_remote_agent_logs(db, rule_id: int, stock_code: str) -> AsyncGenerator[dict, None]:
    """Stream logs from remote A2A agent execution."""
    rule_info = get_remote_rule_record(db, rule_id)
    if not rule_info.get("success"):
        yield {"type": "error", "message": rule_info["message"], "stock_code": stock_code}
        return
    rule_record = rule_info["rule"]
    base_url = _get_remote_agent_config(rule_info["base_url"])
    logger.info("Using base_url: %s", base_url)

    try:
        yield {
            "type": "log",
            "message": f"Connecting to remote agent at {base_url}...it may take 30~60s...",
            "stock_code": stock_code,
        }

        yield {
            "type": "log",
            "message": f"Using skill agent execution flow for {stock_code}",
            "stock_code": stock_code,
        }
        result = None
        async for adapter_event in stream_trading_agent_via_skill(stock_code, base_url):
            if adapter_event["type"] == "streaming_text":
                yield {
                    "type": "streaming_text",
                    "message": adapter_event["message"],
                    "stock_code": stock_code,
                }
            elif adapter_event["type"] == "result":
                result = adapter_event["result"]

        action = extract_trading_action(result)
        is_indicating = action == Trade.buy
        persist_trading_result_and_sync(
            db,
            rule_record,
            stock_code,
            action,
            result,
            mode="streaming",
            trade_date=datetime.now(),
        )

        result_msg = f"Decision: {'INDICATING' if is_indicating else 'NOT INDICATING'}"
        yield {
            "type": "remote_result",
            "message": f"{result_msg} (action={action or 'unknown'})",
            "stock_code": stock_code,
            "indicating": is_indicating,
        }
        yield {
            "type": "stock_complete",
            "message": f"✓ {stock_code}: {result_msg}",
            "stock_code": stock_code,
        }
    except Exception as exc:
        logger.exception("Error running remote agent")
        yield {
            "type": "error",
            "message": f"Remote agent error: {exc}",
            "stock_code": stock_code,
        }


async def stream_single_stock_execution(db, rule_id: int, stock_code: str) -> AsyncGenerator[dict, None]:
    """Stream remote agent execution logs for a single stock."""
    try:
        rule_info = get_remote_rule_record(db, rule_id)
        if not rule_info.get("success"):
            yield {"type": "error", "message": rule_info["message"], "stock_code": stock_code}
            return
        rule_record = rule_info["rule"]

        yield {
            "type": "start",
            "message": f"Running {stock_code} for rule: {rule_record.name} (ID: {rule_id})",
            "timestamp": datetime.now().isoformat(),
            "stock_code": stock_code,
        }

        async for log_entry in stream_remote_agent_logs(db, rule_id, stock_code):
            yield log_entry

        yield {
            "type": "complete",
            "message": f"Execution complete for {stock_code}",
            "timestamp": datetime.now().isoformat(),
            "stock_code": stock_code,
        }
    except Exception as exc:
        logger.exception("Error in stream_single_stock_execution")
        yield {
            "type": "error",
            "message": f"Fatal error: {exc}",
            "stock_code": stock_code,
        }
