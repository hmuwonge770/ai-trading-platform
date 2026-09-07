from packages.autonomy.observability import ExecutionAuditEvent, ExecutionAuditStatus


def test_audit_event_is_immutable_and_deterministic():
    kwargs = dict(
        status=ExecutionAuditStatus.SUBMITTED,
        runtime_mode="enabled",
        client_order_id="client-123",
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
        authorization_hash="a" * 64,
        risk_approved=True,
        occurred_at=1_700_000_000,
        reasons=(),
        exchange_order_id="987654",
    )
    first = ExecutionAuditEvent.create(**kwargs)
    second = ExecutionAuditEvent.create(**kwargs)

    assert first == second
    assert len(first.event_id) == 64
    assert "api_secret" not in first.__repr__()


def test_blocked_event_carries_only_safe_reasons():
    event = ExecutionAuditEvent.create(
        status=ExecutionAuditStatus.BLOCKED,
        runtime_mode="enabled",
        client_order_id="client-456",
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
        authorization_hash="b" * 64,
        risk_approved=False,
        occurred_at=1_700_000_001,
        reasons=("live_authorization_expired",),
    )

    assert event.status is ExecutionAuditStatus.BLOCKED
    assert event.exchange_order_id is None
    assert event.reasons == ("live_authorization_expired",)


def test_audit_event_rejects_invalid_timestamp():
    try:
        ExecutionAuditEvent.create(
            status=ExecutionAuditStatus.DRY_RUN,
            runtime_mode="dry_run",
            client_order_id="",
            strategy_version_id="strategy-v1",
            strategy_fingerprint="fingerprint-1",
            authorization_hash="c" * 64,
            risk_approved=False,
            occurred_at=0,
        )
    except ValueError as exc:
        assert "occurred_at" in str(exc)
    else:
        raise AssertionError("expected invalid timestamp to fail")
