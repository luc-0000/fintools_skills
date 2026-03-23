import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


SKILL_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = SKILL_ROOT / "backtests" / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db.models import Base, Pool, Rule, RulePool
from end_points.config.db_init import DatabaseWrapper
from end_points.get_rule.operations.get_rule_opts import assignPoolToAgent, getAgentPoolChoices


class BacktestsAgentPoolBindingTests(unittest.TestCase):
    def _build_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = scoped_session(sessionmaker(bind=engine))
        return DatabaseWrapper(session, engine=engine), session

    def test_get_agent_pool_choices_marks_assigned_pools(self):
        db, session = self._build_db()
        try:
            rule = Rule(
                name="remote_105",
                type="remote_agent",
                info="https://example.com/api/v1/agents/105/a2a/",
                description="",
                agent_id="105",
            )
            pool_a = Pool(name="growth")
            pool_b = Pool(name="value")
            session.add_all([rule, pool_a, pool_b])
            session.commit()
            session.add(RulePool(rule_id=rule.id, pool_id=pool_a.id))
            session.commit()

            result = getAgentPoolChoices(db, "105")

            self.assertEqual(result["code"], "SUCCESS")
            self.assertEqual(result["data"]["assigned_pool_ids"], [pool_a.id])
            items = {item["name"]: item for item in result["data"]["items"]}
            self.assertTrue(items["growth"]["assigned"])
            self.assertFalse(items["value"]["assigned"])
        finally:
            session.remove()

    def test_assign_pool_to_agent_by_pool_name(self):
        db, session = self._build_db()
        try:
            pool = Pool(name="alpha")
            session.add(pool)
            session.commit()

            result = assignPoolToAgent(db, "105", {"pool_name": "alpha"})

            self.assertEqual(result["code"], "SUCCESS")
            self.assertTrue(result["data"]["created_rule"])
            rule = session.query(Rule).filter(Rule.agent_id == "105").one()
            binding = session.query(RulePool).filter(RulePool.rule_id == rule.id, RulePool.pool_id == pool.id).one()
            self.assertIsNotNone(binding)
            self.assertEqual(result["data"]["pool_name"], "alpha")
        finally:
            session.remove()

    def test_assign_pool_to_agent_by_pool_id_reuses_existing_rule(self):
        db, session = self._build_db()
        try:
            rule = Rule(
                name="remote_105",
                type="remote_agent",
                info="https://example.com/api/v1/agents/105/a2a/",
                description="",
                agent_id="105",
            )
            pool = Pool(name="alpha")
            session.add_all([rule, pool])
            session.commit()

            result = assignPoolToAgent(db, "105", {"pool_id": pool.id})

            self.assertEqual(result["code"], "SUCCESS")
            self.assertFalse(result["data"]["created_rule"])
            self.assertEqual(session.query(Rule).filter(Rule.agent_id == "105").count(), 1)
            self.assertEqual(session.query(RulePool).filter(RulePool.rule_id == rule.id, RulePool.pool_id == pool.id).count(), 1)
        finally:
            session.remove()


if __name__ == "__main__":
    unittest.main()
