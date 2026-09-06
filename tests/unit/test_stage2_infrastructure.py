import json
import uuid
from datetime import datetime, timezone

from packages.database.base import Base
from packages.database.models import Experiment, Job, MarketCandle, ResearchSession, Strategy, StrategyVersion
from packages.messaging.messages import JobMessage
from packages.messaging.topology import EXCHANGE, JOB_QUEUES, RETRY_DELAY_MS, queue_names


def test_stage2_models_are_registered():
    tables = set(Base.metadata.tables)
    assert {"research_sessions", "strategies", "strategy_versions", "experiments", "backtest_results", "ai_reviews", "research_hypotheses", "market_candles", "jobs"} <= tables


def test_model_defaults_and_constraints_are_declared():
    assert ResearchSession.__table__.c.id.primary_key
    assert StrategyVersion.__table__.c.fingerprint.unique
    assert MarketCandle.__table__.c.open_time is not None
    assert any(c.name == "uq_market_candles_symbol_timeframe_open" for c in MarketCandle.__table__.constraints)
    assert Job.__table__.c.attempts.default.arg == 0
    assert Experiment.__table__.c.parameters.default.arg == {}


def test_job_message_is_json_and_has_stable_identifiers():
    job_id = uuid.uuid4()
    session_id = uuid.uuid4()
    message = JobMessage(job_id=job_id, job_type="experiment.backtest", payload={"x": 1}, session_id=session_id)
    body = json.loads(message.to_bytes())
    assert body["job_id"] == str(job_id)
    assert body["session_id"] == str(session_id)
    assert body["job_type"] == "experiment.backtest"
    assert body["payload"] == {"x": 1}
    datetime.fromisoformat(body["created_at"])


def test_rabbit_topology_is_durable_and_retry_is_delayed():
    assert EXCHANGE == "trading"
    assert len(JOB_QUEUES) == 6
    assert RETRY_DELAY_MS == 5000
    assert queue_names("research.generate").retry == "research.generate.retry"
    assert queue_names("research.generate").dead == "research.generate.dead"
