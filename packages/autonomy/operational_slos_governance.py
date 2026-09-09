"""Read-only operational SLO evaluator; it never activates runtime or changes limits."""
from dataclasses import dataclass
from decimal import Decimal
from .operational_slos import OperationalObservation, OperationalSLOPolicy, SLOStatus


@dataclass(frozen=True, slots=True)
class OperationalSLOReport:
    status: SLOStatus
    reasons: tuple[str, ...]
    capacity_headroom_percent: Decimal
    capacity_utilization_percent: Decimal

    @property
    def safe_to_continue(self) -> bool:
        return self.status is SLOStatus.HEALTHY


class AutonomousOperationalSLOGovernance:
    """Evaluates bounded operational health without mutating control state."""

    def __init__(self, policy: OperationalSLOPolicy | None = None) -> None:
        self.policy = policy or OperationalSLOPolicy()

    def evaluate(self, observation: OperationalObservation) -> OperationalSLOReport:
        p = self.policy
        reasons: list[str] = []
        if observation.window.total_seconds() < p.observation_window_seconds:
            reasons.append("insufficient_observation_window")
        if observation.availability_percent < p.min_availability_percent:
            reasons.append("availability_slo_breached")
        if observation.decision_latency_ms > p.max_decision_latency_ms:
            reasons.append("decision_latency_slo_breached")
        if observation.reconciliation_latency_ms > p.max_reconciliation_latency_ms:
            reasons.append("reconciliation_latency_slo_breached")
        if observation.error_rate_percent > p.max_error_rate_percent:
            reasons.append("error_rate_slo_breached")
        if observation.queue_depth > p.max_queue_depth:
            reasons.append("queue_depth_capacity_breached")
        if observation.active_workers > p.max_concurrent_workers:
            reasons.append("worker_concurrency_breached")
        if observation.capacity_headroom_percent < p.min_capacity_headroom_percent:
            reasons.append("capacity_headroom_breached")

        critical = {"availability_slo_breached", "decision_latency_slo_breached", "reconciliation_latency_slo_breached", "error_rate_slo_breached", "queue_depth_capacity_breached", "worker_concurrency_breached", "capacity_headroom_breached"}
        status = SLOStatus.BREACHED if any(r in critical for r in reasons) else (SLOStatus.AT_RISK if reasons else SLOStatus.HEALTHY)
        return OperationalSLOReport(status, tuple(reasons), observation.capacity_headroom_percent, observation.capacity_utilization_percent)
