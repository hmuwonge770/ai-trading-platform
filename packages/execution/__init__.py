"""Execution simulation, service, and exchange adapter boundaries."""

from packages.execution.binance_testnet import BinanceSpotTestnetClient, BinanceTestnetConfig, BinanceTestnetError
from packages.execution.service import ExecutionResult, ExecutionService
from packages.execution.simulator import (
    ExecutionConfig,
    ExecutionSimulator,
    ExecutionStatus,
    SimulatedFill,
    SimulatedOrder,
)

__all__ = [
    "BinanceSpotTestnetClient", "BinanceTestnetConfig", "BinanceTestnetError",
    "ExecutionConfig", "ExecutionResult", "ExecutionService", "ExecutionSimulator",
    "ExecutionStatus", "SimulatedFill", "SimulatedOrder",
]
