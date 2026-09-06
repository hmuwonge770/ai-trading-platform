"""Execution simulation, service, exchange adapter, and authorization boundaries."""

from packages.execution.binance_testnet import BinanceSpotTestnetClient, BinanceTestnetConfig, BinanceTestnetError
from packages.execution.integration import AuthorizationStore, ExecutionAuthorization, PromotionExecutionGateway
from packages.execution.service import ExecutionResult, ExecutionService
from packages.execution.simulator import (
    ExecutionConfig,
    ExecutionSimulator,
    ExecutionStatus,
    SimulatedFill,
    SimulatedOrder,
)

__all__ = [
    "AuthorizationStore", "BinanceSpotTestnetClient", "BinanceTestnetConfig", "BinanceTestnetError",
    "ExecutionAuthorization", "ExecutionConfig", "ExecutionResult", "ExecutionService", "ExecutionSimulator",
    "ExecutionStatus", "PromotionExecutionGateway", "SimulatedFill", "SimulatedOrder",
]
