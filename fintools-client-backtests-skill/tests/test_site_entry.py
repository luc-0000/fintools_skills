import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "site_entry.py"
)


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    added = False
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
        added = True
    try:
        spec = importlib.util.spec_from_file_location("site_entry", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if added:
            sys.path.remove(scripts_dir)


class SiteEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_summarize_resources_returns_endpoint_catalog(self):
        with mock.patch.object(
            self.module,
            "_discover",
            return_value={
                "data": {
                    "service": "FinTools Public API",
                    "capabilities": {"agent_execution": {"protocol": "A2A"}},
                    "public_data": ["Listed agents across the market"],
                    "endpoints": [
                        {
                            "method": "GET",
                            "path": "/api/v1/public/agents",
                            "description": "Discover all listed public agents with filtering.",
                            "resolved_url": "https://warranties-movies-host-repository.trycloudflare.com/api/v1/public/agents",
                        }
                    ],
                }
            },
        ):
            result = self.module.summarize_resources()

        self.assertEqual(result["service"], "FinTools Public API")
        self.assertEqual(result["endpoints"][0]["path"], "/api/v1/public/agents")

    def test_summarize_agents_keeps_compact_fields(self):
        with mock.patch.object(
            self.module,
            "_discover",
            return_value={
                "data": {
                    "items": [
                        {
                            "id": 105,
                            "name": "quant_agent_vlm",
                            "agent_category": "trading",
                            "market": "stock",
                            "updated_at": "2026-03-20T15:19:27",
                            "a2a_url": "https://warranties-movies-host-repository.trycloudflare.com/api/v1/agents/105/a2a/",
                        }
                    ]
                }
            },
        ):
            result = self.module.summarize_items("agents")

        self.assertEqual(result["agents"][0]["id"], 105)
        self.assertEqual(result["agents"][0]["a2a_url"], "https://warranties-movies-host-repository.trycloudflare.com/api/v1/agents/105/a2a/")

    def test_resolve_agent_supports_id_and_name(self):
        agents_payload = {
            "data": {
                "items": [
                    {"id": 105, "name": "quant_agent_vlm", "agent_category": "trading", "a2a_url": "https://example.com/api/v1/agents/105/a2a/"},
                    {"id": 82, "name": "dr_agent101", "agent_category": "deep_research", "a2a_url": "https://example.com/api/v1/agents/82/a2a/"},
                ]
            }
        }
        with mock.patch.object(self.module, "_discover", return_value=agents_payload):
            by_id = self.module.resolve_agent("105")
            by_name = self.module.resolve_agent("dr_agent101")

        self.assertEqual(by_id["name"], "quant_agent_vlm")
        self.assertEqual(by_name["id"], 82)

    def test_build_run_agent_command_uses_existing_runner(self):
        args = type(
            "Args",
            (),
            {
                "agent": "105",
                "stock_code": "600519",
                "agent_type": None,
                "mode": "streaming",
                "access_token": "secret",
                "work_dir": "/tmp/runs",
                "task_id": None,
            },
        )()
        agent_record = {
            "id": 105,
            "name": "quant_agent_vlm",
            "agent_category": "trading",
            "a2a_url": "https://warranties-movies-host-repository.trycloudflare.com/api/v1/agents/105/a2a/",
        }

        command = self.module.build_run_agent_command(args, agent_record)

        self.assertEqual(command[0], sys.executable)
        self.assertIn(str(self.module.RUN_AGENT_CLIENT), command)
        self.assertIn("--agent-url", command)
        self.assertIn("https://warranties-movies-host-repository.trycloudflare.com/api/v1/agents/105/a2a/", command)

    def test_run_agent_invokes_runner(self):
        args = type(
            "Args",
            (),
            {
                "agent": "105",
                "stock_code": "600519",
                "agent_type": None,
                "mode": "streaming",
                "access_token": None,
                "work_dir": None,
                "task_id": None,
            },
        )()
        agent_record = {
            "id": 105,
            "name": "quant_agent_vlm",
            "agent_category": "trading",
            "a2a_url": "https://warranties-movies-host-repository.trycloudflare.com/api/v1/agents/105/a2a/",
        }
        with mock.patch.object(self.module, "resolve_agent", return_value=agent_record), \
             mock.patch.object(self.module.subprocess, "run", return_value=type("Completed", (), {"returncode": 0})()) as mock_run:
            result = self.module.run_agent(args)

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["agent"]["id"], 105)
        self.assertEqual(mock_run.call_count, 1)

    def test_main_prints_agents_json(self):
        args = type(
            "Args",
            (),
            {
                "action": "agents",
                "agent": None,
                "stock_code": None,
                "agent_type": None,
                "mode": "streaming",
                "access_token": None,
                "work_dir": None,
                "task_id": None,
            },
        )()
        with mock.patch.object(self.module, "parse_args", return_value=args), \
             mock.patch.object(self.module, "summarize_items", return_value={"agents": [{"id": 105, "name": "quant_agent_vlm"}]}), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            exit_code = self.module.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["agents"][0]["id"], 105)
