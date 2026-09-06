"""AI-assisted quantitative research, isolated from trading execution."""

from packages.researcher.models import ResearchContext, ResearchProposal
from packages.researcher.researcher import AIResearcher

__all__ = ["AIResearcher", "ResearchContext", "ResearchProposal"]
