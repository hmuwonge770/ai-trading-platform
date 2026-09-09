"""Governance integration for production readiness."""
from dataclasses import dataclass

from .production_readiness import (
    ProductionReadinessAssessment,
    ProductionReadinessObservation,
    ProductionReadinessPolicy,
    assess_production_readiness,
)


@dataclass(frozen=True, slots=True)
class ProductionReadinessGovernanceContext:
    observation: ProductionReadinessObservation
    policy: ProductionReadinessPolicy = ProductionReadinessPolicy()


class AutonomousProductionReadinessIntegration:
    """Compose evidence gates without activating production execution."""

    @staticmethod
    def assess(context: ProductionReadinessGovernanceContext) -> ProductionReadinessAssessment:
        return assess_production_readiness(context.observation, context.policy)
