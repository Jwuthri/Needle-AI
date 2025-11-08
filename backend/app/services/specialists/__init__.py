"""
Specialist agents for the hybrid chatbot architecture.
"""

from app.services.specialists.base_specialist import BaseSpecialist
from app.services.specialists.product_agent import ProductAgent
from app.services.specialists.research_agent import ResearchAgent
from app.services.specialists.analytics_agent import AnalyticsAgent
from app.services.specialists.general_agent import GeneralAgent

__all__ = [
    "BaseSpecialist",
    "ProductAgent",
    "ResearchAgent",
    "AnalyticsAgent",
    "GeneralAgent",
]

