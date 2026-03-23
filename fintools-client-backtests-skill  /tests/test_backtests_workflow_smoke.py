from datetime import date, datetime
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


SKILL_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = SKILL_ROOT / "backtests" / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db.models import AgentTrading, Base, Pool, PoolStock, Rule, RulePool, Simulator, SimulatorConfig, Stock
from end_points.config.db_init import DatabaseWrapper
from end_points.get_rule.operations.get_rule_opts import assignPoolToAgent, ensureRemoteAgentRule, runRuleAgent
from end_points.get_simulator.operations.get_simulator_opts import addSimulator, runSimulator


class BacktestsWorkflowSmokeTests(unittest.TestCase):
    def _build_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = scoped_session(sessionmaker(bind=engine))
        return DatabaseWrapper(session, engine=engine), session

    def test_agent_id_rule_pool_run_smoke(self):
        db, session = self._build_db()
        try:
            session.add_all(
                [
                    Pool(name="alpha"),
                    Stock(code="600519", name="Kweichow Moutai", se="sh"),
                ]
            )
            session.commit()
            pool = session.query(Pool).filter(Pool.name == "alpha").one()
            session.add(PoolStock(pool_id=pool.id, stock_code="600519"))
            session.commit()

            ensure_result = ensureRemoteAgentRule(
                db,
                {
                    "agent_id": "105",
                    "name": "Agent 105",
                    "description": "Remote trading agent 105",
                    "info": "https://example.com/api/v1/agents/105/a2a/",
                },
            )
            self.assertEqual(ensure_result["code"], "SUCCESS")
            rule_id = ensure_result["data"]["id"]

            bind_result = assignPoolToAgent(db, "105", {"pool_name": "alpha"})
            self.assertEqual(bind_result["code"], "SUCCESS")

            with patch(
                "end_points.get_rule.operations.agent_utils.execute_agent_with_skill_adapter",
                new=AsyncMock(return_value={"result": {"action": "buy"}}),
            ):
                run_result = runRuleAgent(db, rule_id)

            self.assertEqual(run_result["code"], "SUCCESS")
            self.assertEqual(run_result["data"]["stock_count"], 1)
            trading = session.query(AgentTrading).filter(AgentTrading.rule_id == rule_id).one()
            self.assertEqual(trading.stock, "600519")
        finally:
            session.remove()

    def test_simulator_can_run_from_existing_agent_trading_without_pool(self):
        db, session = self._build_db()
        try:
            rule = Rule(
                name="remote_205",
                type="remote_agent",
                info="https://example.com/api/v1/agents/205/a2a/",
                description="",
                agent_id="205",
            )
            session.add(rule)
            session.commit()
            session.add_all(
                [
                    Stock(code="600519", name="Kweichow Moutai", se="sh"),
                    SimulatorConfig(id=1, profit_threshold=0, stop_loss=5, max_holding_days=5),
                    AgentTrading(
                        rule_id=rule.id,
                        stock="600519",
                        trading_date=datetime(2026, 3, 23),
                        trading_type="indicating",
                    ),
                ]
            )
            session.commit()

            add_result = addSimulator(
                db,
                {"rule_id": rule.id, "start_date": date(2026, 1, 2), "init_money": 100000},
            )
            self.assertEqual(add_result["code"], "SUCCESS")
            sim_id = add_result["data"]

            stock_data = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2026-03-23", "2026-03-24", "2026-03-25", "2026-03-26"]),
                    "open": [10.0, 10.1, 10.2, 10.3],
                    "high": [10.1, 10.2, 10.3, 10.4],
                    "low": [9.9, 10.0, 10.1, 10.2],
                    "close": [10.0, 10.1, 10.2, 10.3],
                    "volume": [1, 1, 1, 1],
                    "turnover": [1, 1, 1, 1],
                    "turnover_rate": [1, 1, 1, 1],
                    "shake_rate": [1, 1, 1, 1],
                    "change_rate": [1, 1, 1, 1],
                    "change_amount": [1, 1, 1, 1],
                }
            )

            with patch(
                "end_points.get_simulator.operations.get_simulator_utils.stockDataFrameFromDataTool",
                return_value=stock_data,
            ):
                run_result = runSimulator(db, {}, sim_id)

            self.assertEqual(run_result["code"], "SUCCESS")
            sim = session.query(Simulator).filter(Simulator.id == sim_id).one()
            self.assertIsNotNone(sim.earning_info)
            self.assertEqual(session.query(RulePool).filter(RulePool.rule_id == rule.id).count(), 0)
        finally:
            session.remove()


if __name__ == "__main__":
    unittest.main()
