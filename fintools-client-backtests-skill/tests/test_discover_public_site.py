import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "discover_public_site.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("discover_public_site", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


class DiscoverPublicSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_discovery_url_uses_requested_site_origin(self):
        url = self.module.discovery_url("https://demo.example.com/some/page")
        self.assertEqual(url, "https://demo.example.com/api/v1/public/info")

    def test_normalize_service_url_rewrites_relative_and_api_urls(self):
        site_origin = "https://demo.example.com"
        self.assertEqual(
            self.module.normalize_service_url("/api/v1/public/skills/91/download", site_origin),
            "https://demo.example.com/api/v1/public/skills/91/download",
        )
        self.assertEqual(
            self.module.normalize_service_url("http://8.153.13.5:8000/api/v1/agents/105/a2a/", site_origin),
            "https://demo.example.com/api/v1/agents/105/a2a/",
        )
        self.assertEqual(
            self.module.normalize_service_url("https://github.com/luc-0000/fintools_skills.git", site_origin),
            "https://github.com/luc-0000/fintools_skills.git",
        )

    def test_fetch_discovery_rewrites_endpoint_urls_to_requested_site(self):
        discovery_payload = {
            "service": "FinTools Public API",
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/api/v1/public/agents",
                    "url": "http://8.153.13.5:8000/api/v1/public/agents",
                }
            ],
        }
        with mock.patch.object(
            self.module.urllib_request,
            "urlopen",
            return_value=_FakeResponse(discovery_payload),
        ):
            result = self.module.fetch_discovery("https://demo.example.com")

        self.assertEqual(result["requested_site_url"], "https://demo.example.com")
        self.assertEqual(result["endpoints"][0]["resolved_url"], "https://demo.example.com/api/v1/public/agents")

    def test_run_query_agents_uses_discovered_endpoint_and_rewrites_nested_urls(self):
        discovery_payload = {
            "service": "FinTools Public API",
            "endpoints": [
                {"method": "GET", "path": "/api/v1/public/agents", "url": "http://8.153.13.5:8000/api/v1/public/agents"}
            ],
        }
        agents_payload = {
            "items": [
                {
                    "id": 105,
                    "name": "quant_agent_vlm",
                    "a2a_url": "http://8.153.13.5:8000/api/v1/agents/105/a2a/",
                    "a2a_endpoints": {
                        "agent_card_url": "http://8.153.13.5:8000/api/v1/agents/105/a2a/.well-known/agent-card.json"
                    },
                }
            ]
        }

        responses = [_FakeResponse(discovery_payload), _FakeResponse(agents_payload)]

        def fake_urlopen(request):
            self.assertTrue(responses)
            return responses.pop(0)

        args = type(
            "Args",
            (),
            {
                "site_url": "https://demo.example.com",
                "subject": "agents",
                "repo_id": None,
                "ticker": None,
                "author": None,
                "page": None,
                "page_size": None,
                "keyword": None,
            },
        )()

        with mock.patch.object(self.module.urllib_request, "urlopen", side_effect=fake_urlopen):
            result = self.module.run_query(args)

        self.assertEqual(result["resolved_url"], "https://demo.example.com/api/v1/public/agents")
        item = result["data"]["items"][0]
        self.assertEqual(item["a2a_url"], "https://demo.example.com/api/v1/agents/105/a2a/")
        self.assertEqual(
            item["a2a_endpoints"]["agent_card_url"],
            "https://demo.example.com/api/v1/agents/105/a2a/.well-known/agent-card.json",
        )

    def test_run_query_resources_returns_endpoint_catalog(self):
        discovery_payload = {
            "service": "FinTools Public API",
            "purpose": "Financial quantitative tooling for external agents.",
            "public_data": ["Listed agents across the market", "Listed skills across the market"],
            "capabilities": {"agent_execution": {"protocol": "A2A"}},
            "recommended_flow": ["Start with GET /api/v1/public/info."],
            "endpoints": [
                {"method": "GET", "path": "/api/v1/public/info", "url": "http://8.153.13.5:8000/api/v1/public/info"}
            ],
        }
        args = type(
            "Args",
            (),
            {
                "site_url": "https://demo.example.com",
                "subject": "resources",
                "repo_id": None,
                "ticker": None,
                "author": None,
                "page": None,
                "page_size": None,
                "keyword": None,
            },
        )()

        with mock.patch.object(
            self.module.urllib_request,
            "urlopen",
            return_value=_FakeResponse(discovery_payload),
        ):
            result = self.module.run_query(args)

        self.assertEqual(result["subject"], "resources")
        self.assertEqual(result["data"]["endpoints"][0]["resolved_url"], "https://demo.example.com/api/v1/public/info")

    def test_main_prints_json(self):
        args = type(
            "Args",
            (),
            {
                "site_url": "https://demo.example.com",
                "subject": "resources",
                "repo_id": None,
                "ticker": None,
                "author": None,
                "page": None,
                "page_size": None,
                "keyword": None,
            },
        )()
        payload = {"subject": "resources", "site_url": "https://demo.example.com", "data": {"service": "FinTools Public API"}}
        with mock.patch.object(self.module, "parse_args", return_value=args), \
             mock.patch.object(self.module, "run_query", return_value=payload), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            result = self.module.main()

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())["data"]["service"], "FinTools Public API")
