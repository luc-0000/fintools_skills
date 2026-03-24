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

from db.models import Base, Pool
from end_points.config.db_init import DatabaseWrapper
from end_points.get_pool.operations.get_pool_opts import getPoolList


class BacktestsPoolListTests(unittest.TestCase):
    def _build_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = scoped_session(sessionmaker(bind=engine))
        return DatabaseWrapper(session, engine=engine), session

    def test_get_pool_list_returns_existing_rows_when_latest_date_refresh_fails(self):
        db, session = self._build_db()
        try:
            session.add(Pool(name="test", stocks=2))
            session.commit()

            with patch(
                "end_points.get_pool.operations.get_pool_opts.update_latest_date",
                side_effect=RuntimeError("attempt to write a readonly database"),
            ):
                result = getPoolList(db)

            self.assertEqual(result["code"], "SUCCESS")
            self.assertEqual(result["data"]["total"], 1)
            self.assertEqual(result["data"]["items"][0]["name"], "test")
            self.assertEqual(result["data"]["items"][0]["stocks"], 2)
        finally:
            session.remove()


if __name__ == "__main__":
    unittest.main()
