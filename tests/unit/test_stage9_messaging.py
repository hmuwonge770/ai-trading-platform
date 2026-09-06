from __future__ import annotations

import json
from uuid import uuid4

import pytest

from packages.messaging.jobs import JobSpec
from packages.messaging.messages import JobMessage
from packages.messaging.topology import JOB_QUEUES, queue_names


def test_job_spec_creates_persistent_message_identity():
    session_id = uuid4()
    spec = JobSpec("experiment.backtest", {"symbol": "BTCUSDT"}, session_id=session_id)
    message = spec.message()

    assert message.job_type == "experiment.backtest"
    assert message.session_id == session_id
    assert message.attempt == 1
    assert message.max_attempts == 3
    decoded = json.loads(message.to_bytes())
    assert decoded["job_id"] == str(message.job_id)
    assert decoded["payload"] == {"symbol": "BTCUSDT"}


def test_job_message_round_trip_shape():
    message = JobMessage(uuid4(), "research.generate", {"objective": "trend"})
    value = json.loads(message.to_bytes())
    assert value["job_type"] == message.job_type
    assert value["payload"] == message.payload


def test_all_work_queues_have_retry_and_dead_routes():
    assert len(JOB_QUEUES) == 6
    for queue in JOB_QUEUES:
        names = queue_names(queue)
        assert names.retry == f"{queue}.retry"
        assert names.dead == f"{queue}.dead"


def test_job_spec_rejects_invalid_attempt_budget():
    with pytest.raises(ValueError, match="max_attempts"):
        JobSpec("research.generate", {}, max_attempts=0)

    with pytest.raises(ValueError, match="job_type"):
        JobSpec("", {})
