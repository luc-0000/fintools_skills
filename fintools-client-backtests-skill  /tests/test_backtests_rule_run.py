import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


SKILL_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = SKILL_ROOT / "backtests" / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db.models import Base, Pool, PoolStock, Rule, RulePool
from end_points.config.db_init import DatabaseWrapper
from end_points.get_rule.operations.get_rule_opts import runRuleAgent


class BacktestsRuleRunTests(unittest.TestCase):
    def _build_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = scoped_session(sessionmaker(bind=engine))
        return DatabaseWrapper(session, engine=engine), session

    def test_run_rule_agent_returns_needs_pool_when_no_pool_assigned(self):
        db, session = self._build_db()
        try:
            rule = Rule(
                name="remote_105",
                type="remote_agent",
                info="https://example.com/api/v1/agents/105/a2a/",
                description="",
                agent_id="105",
            )
            session.add(rule)
            session.commit()

            result = runRuleAgent(db, rule.id)

            self.assertEqual(result["code"], "FAILURE")
            self.assertTrue(result["data"]["needs_pool"])
            self.assertIn("Assign a pool", result["message"])
        finally:
            session.remove()

    def test_run_rule_agent_returns_needs_pool_when_pool_has_no_stocks(self):
        db, session = self._build_db()
        try:
            rule = Rule(
                name="remote_105",
                type="remote_agent",
                info="https://example.com/api/v1/agents/105/a2a/",
                description="",
                agent_id="105",
            )
            pool = Pool(name="pool-a")
            session.add_all([rule, pool])
            session.commit()
            session.add(RulePool(rule_id=rule.id, pool_id=pool.id))
            session.commit()

            result = runRuleAgent(db, rule.id)

            self.assertEqual(result["code"], "FAILURE")
            self.assertTrue(result["data"]["needs_pool"])
            self.assertIn("do not contain any stocks", result["message"])
        finally:
            session.remove()

    def test_run_rule_agent_reports_execution_counts(self):
        db, session = self._build_db()
        try:
            rule = Rule(
                name="remote_105",
                type="remote_agent",
                info="https://example.com/api/v1/agents/105/a2a/",
                description="",
                agent_id="105",
            )
            pool = Pool(name="pool-a")
            session.add_all([rule, pool])
            session.commit()
            session.add_all(
                [
                    RulePool(rule_id=rule.id, pool_id=pool.id),
                    PoolStock(pool_id=pool.id, stock_code="600519"),
                    PoolStock(pool_id=pool.id, stock_code="000001"),
                ]
            )
            session.commit()

            with patch(
                "end_points.get_rule.operations.agent_utils.run_agent_for_stock",
                side_effect=[
                    {"success": True, "stock_code": "600519", "action": "buy"},
                    {"success": False, "stock_code": "000001", "error": "network error"},
                ],
            ):
                result = runRuleAgent(db, rule.id)

            self.assertEqual(result["code"], "FAILURE")
            self.assertEqual(result["data"]["stock_count"], 2)
            self.assertEqual(result["data"]["executed_count"], 1)
            self.assertEqual(result["data"]["failed_count"], 1)
        finally:
            session.remove()


if __name__ == "__main__":
    unittest.main()
