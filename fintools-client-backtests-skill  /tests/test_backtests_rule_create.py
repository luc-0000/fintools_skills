import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


SKILL_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = SKILL_ROOT / "backtests" / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db.models import Base, Rule
from end_points.config.db_init import DatabaseWrapper
from end_points.get_rule.operations.get_rule_opts import ensureRemoteAgentRule
from end_points.get_rule.rule_schema import RuleCreateArgs


class BacktestsRuleCreateTests(unittest.TestCase):
    def _build_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = scoped_session(sessionmaker(bind=engine))
        return DatabaseWrapper(session, engine=engine), session

    def test_rule_create_args_allows_blank_description(self):
        args = RuleCreateArgs(
            name="remote_agent_105",
            type="remote_agent",
            description="",
            info="https://example.com/api/v1/agents/105/a2a/",
            agent_id="105",
        )
        self.assertIsNone(args.description)

    def test_ensure_remote_agent_rule_creates_missing_rule(self):
        db, session = self._build_db()
        try:
            result = ensureRemoteAgentRule(
                db,
                {
                    "agent_id": "105",
                    "name": "Agent 105",
                    "description": "Remote trading agent 105",
                    "info": "https://example.com/api/v1/agents/105/a2a/",
                },
            )
            self.assertEqual(result["code"], "SUCCESS")
            self.assertTrue(result["data"]["created"])
            rule = session.query(Rule).filter(Rule.agent_id == "105").one()
            self.assertEqual(rule.type, "remote_agent")
            self.assertEqual(rule.info, "https://example.com/api/v1/agents/105/a2a/")
        finally:
            session.remove()

    def test_ensure_remote_agent_rule_reuses_existing_rule(self):
        db, session = self._build_db()
        try:
            rule = Rule(
                name="remote_agent_105",
                type="remote_agent",
                description="existing",
                info="https://example.com/api/v1/agents/105/a2a/",
                agent_id="105",
            )
            session.add(rule)
            session.commit()

            result = ensureRemoteAgentRule(
                db,
                {
                    "agent_id": "105",
                    "name": "Agent 105",
                    "description": "Remote trading agent 105",
                    "info": "https://example.com/api/v1/agents/105/a2a/",
                },
            )
            self.assertEqual(result["code"], "SUCCESS")
            self.assertFalse(result["data"]["created"])
            self.assertEqual(session.query(Rule).filter(Rule.agent_id == "105").count(), 1)
        finally:
            session.remove()


if __name__ == "__main__":
    unittest.main()
