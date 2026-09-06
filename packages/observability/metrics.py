from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class TradingMetrics:
    """Prometheus metrics with bounded labels for platform operations."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry(auto_describe=True)
        self.http_requests = Counter(
            "trading_http_requests_total",
            "HTTP requests handled by the control API",
            ("method", "route", "status"),
            registry=self.registry,
        )
        self.http_latency = Histogram(
            "trading_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ("method", "route"),
            registry=self.registry,
        )
        self.http_in_flight = Gauge(
            "trading_http_requests_in_flight",
            "HTTP requests currently being handled",
            registry=self.registry,
        )
        self.risk_decisions = Counter(
            "trading_risk_decisions_total",
            "Risk gateway decisions",
            ("decision", "reason"),
            registry=self.registry,
        )
        self.execution_outcomes = Counter(
            "trading_execution_outcomes_total",
            "Execution service outcomes",
            ("status",),
            registry=self.registry,
        )
        self.exchange_errors = Counter(
            "trading_exchange_errors_total",
            "Exchange adapter errors",
            ("exchange", "operation"),
            registry=self.registry,
        )
        self.accounting_transactions = Counter(
            "trading_accounting_transactions_total",
            "Accounting transactions posted",
            ("transaction_type",),
            registry=self.registry,
        )

    def observe_risk(self, decision: str, reason: str) -> None:
        self.risk_decisions.labels(decision=decision, reason=reason).inc()

    def observe_execution(self, status: str) -> None:
        self.execution_outcomes.labels(status=status).inc()

    def observe_exchange_error(self, operation: str, exchange: str = "binance_testnet") -> None:
        self.exchange_errors.labels(exchange=exchange, operation=operation).inc()

    def observe_accounting_transaction(self, transaction_type: str) -> None:
        self.accounting_transactions.labels(transaction_type=transaction_type).inc()

    def exposition(self) -> bytes:
        return generate_latest(self.registry)


metrics = TradingMetrics()
