import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = SKILL_ROOT / "backtests" / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from end_points.common.utils.runtime_readiness import ensure_runtime_ready, resolve_runtime_token
from end_points.get_rule.get_rule_routes import get_runtime_ready, post_runtime_ready, start_rule_execution_endpoint
from fastapi import HTTPException
from scripts.trading_run_store import ensure_trading_agent_runs_schema


class BacktestsRuntimeReadinessTests(unittest.TestCase):
    def test_ensure_runtime_ready_initializes_runs_db_without_token_when_check_only(self):
        with tempfile.TemporaryDirectory(prefix="backtests-runtime-ready-") as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            token_path = runs_dir / ".fintools_access_token"
            runs_db_path = tmp_path / "database" / "trading_agent_runs.db"
            backtests_db_path = tmp_path / "database" / "backtests.sqlite3"

            with patch(
                "end_points.common.utils.runtime_readiness.default_runs_parent_dir",
                return_value=runs_dir,
            ), patch(
                "end_points.common.utils.runtime_readiness.token_file_path",
                return_value=token_path,
            ), patch(
                "end_points.common.utils.runtime_readiness.ensure_trading_agent_runs_schema",
                side_effect=lambda: ensure_trading_agent_runs_schema(runs_db_path),
            ), patch(
                "end_points.common.utils.runtime_readiness.default_sqlite_path",
                return_value=backtests_db_path,
            ), patch(
                "end_points.common.utils.runtime_readiness.default_seed_dir",
                return_value=tmp_path / "missing-seed-dir",
            ), patch(
                "end_points.common.utils.runtime_readiness.load_cached_access_token",
                return_value=None,
            ), patch.dict("os.environ", {}, clear=True):
                result = ensure_runtime_ready(require_token=False)
                self.assertFalse(result["token_ready"])
                self.assertEqual(result["token_path"], str(token_path))
                self.assertEqual(result["runs_db_path"], str(runs_db_path))
                self.assertTrue(runs_db_path.exists())
                self.assertTrue(result["runs_db_ready"])
                self.assertEqual(result["backtests_db_path"], str(backtests_db_path))
                self.assertTrue(backtests_db_path.exists())
                self.assertTrue(result["backtests_db_ready"])

    def test_resolve_runtime_token_persists_explicit_token_into_cache(self):
        with tempfile.TemporaryDirectory(prefix="backtests-runtime-explicit-token-") as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            token_path = runs_dir / ".fintools_access_token"
            runs_dir.mkdir(parents=True, exist_ok=True)

            with patch(
                "end_points.common.utils.runtime_readiness.default_runs_parent_dir",
                return_value=runs_dir,
            ), patch(
                "end_points.common.utils.runtime_readiness.token_file_path",
                return_value=token_path,
            ), patch.dict("os.environ", {}, clear=True):
                result = resolve_runtime_token(access_token="real-token", require_token=True)

            self.assertEqual(result["token"], "real-token")
            self.assertEqual(result["token_source"], "explicit")
            self.assertTrue(result["token_persisted"])
            self.assertEqual(token_path.read_text(encoding="utf-8").strip(), "real-token")

    def test_ensure_runtime_ready_raises_without_token_for_execution(self):
        with tempfile.TemporaryDirectory(prefix="backtests-runtime-missing-token-") as tmpdir:
            tmp_path = Path(tmpdir)
            runs_dir = tmp_path / "runs"
            token_path = runs_dir / ".fintools_access_token"
            runs_db_path = tmp_path / "database" / "trading_agent_runs.db"

            with patch(
                "end_points.common.utils.runtime_readiness.default_runs_parent_dir",
                return_value=runs_dir,
            ), patch(
                "end_points.common.utils.runtime_readiness.token_file_path",
                return_value=token_path,
            ), patch(
                "end_points.common.utils.runtime_readiness.ensure_trading_agent_runs_schema",
                side_effect=lambda: ensure_trading_agent_runs_schema(runs_db_path),
            ), patch(
                "end_points.common.utils.runtime_readiness.load_cached_access_token",
                return_value=None,
            ), patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "Missing FINTOOLS access token"):
                    ensure_runtime_ready(require_token=True)

    def test_runtime_ready_endpoint_reports_check_only_status(self):
        with patch(
            "end_points.get_rule.get_rule_routes.ensure_runtime_ready",
            return_value={"token_ready": False, "runs_db_ready": True},
        ) as mock_ready:
            result = asyncio.run(get_runtime_ready())

        mock_ready.assert_called_once_with(require_token=False)
        self.assertEqual(result["code"], "SUCCESS")
        self.assertFalse(result["data"]["token_ready"])
        self.assertTrue(result["data"]["runs_db_ready"])

    def test_post_runtime_ready_accepts_explicit_token(self):
        with patch(
            "end_points.get_rule.get_rule_routes.ensure_runtime_ready",
            return_value={"token_ready": True, "token_source": "explicit", "token_persisted": True},
        ) as mock_ready:
            result = asyncio.run(post_runtime_ready({"access_token": "real-token", "require_token": True}))

        mock_ready.assert_called_once_with(access_token="real-token", require_token=True)
        self.assertEqual(result["code"], "SUCCESS")
        self.assertTrue(result["data"]["token_ready"])
        self.assertTrue(result["data"]["token_persisted"])

    def test_start_rule_execution_endpoint_returns_400_when_token_missing(self):
        with patch(
            "end_points.get_rule.get_rule_routes.ensure_runtime_ready",
            side_effect=RuntimeError("Missing FINTOOLS access token. Expected cache file: /tmp/token"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(start_rule_execution_endpoint(rule_id=123, db=object()))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Missing FINTOOLS access token", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
