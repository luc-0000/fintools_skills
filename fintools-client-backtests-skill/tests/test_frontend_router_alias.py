from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = REPO_ROOT / "backtests" / "frontend"


class FrontendRouterAliasTests(unittest.TestCase):
    def test_router_import_target_exists_and_alias_is_defined(self):
        router_path = FRONTEND_ROOT / "src" / "router" / "index.tsx"
        layout_path = FRONTEND_ROOT / "src" / "layouts" / "ProLayout.tsx"
        vite_config_path = FRONTEND_ROOT / "vite.config.ts"

        router_source = router_path.read_text(encoding="utf-8")
        vite_config = vite_config_path.read_text(encoding="utf-8")

        self.assertTrue(layout_path.exists(), "Expected ProLayout.tsx to exist")
        self.assertIn(
            "import ProLayout from '@/layouts/ProLayout'",
            router_source,
            "Router should import ProLayout through the @ alias",
        )
        self.assertIn(
            "'@': path.resolve(__dirname, './src')",
            vite_config,
            "Vite config should map @ to ./src",
        )


if __name__ == "__main__":
    unittest.main()
