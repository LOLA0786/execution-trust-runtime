"""
agents/__init__.py
Exports the 3 minimal agents + BaseAgent for smoke tests and AGENTS.md compliance.
"""
from .base_agent import BaseAgent
from .procurement.agent import ProcurementAgent
from .revenue_ops.agent import RevenueOpsAgent
from .chief_of_staff.agent import ChiefOfStaffAgent

__all__ = ["BaseAgent", "ProcurementAgent", "RevenueOpsAgent", "ChiefOfStaffAgent"]

# Convenience singletons for tests
procurement_agent = ProcurementAgent()
revenue_ops_agent = RevenueOpsAgent()
chief_of_staff_agent = ChiefOfStaffAgent()
