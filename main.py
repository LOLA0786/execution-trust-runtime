#!/usr/bin/env python3
"""
main.py

Entry point for Execution Trust Runtime.
Runs the 3 agents with PrivateVault checkpoints.
Skeleton for demo only.
"""
from agents.base_agent import BaseAgent


def main():
    print("🚀 Execution Trust Runtime Starting...")
    print("Agents: Procurement, Revenue Operations, Chief of Staff")
    print("PrivateVault checkpoints active (world-state integrity + deterministic replay)\n")
    
    # Skeleton demo for all 3 agents
    procurement = BaseAgent("Enterprise Procurement Agent")
    revenue = BaseAgent("Revenue Operations Agent")
    chief = BaseAgent("Executive Chief of Staff Agent")
    
    print("✅ All agents initialized with Execution Trust Runtime gates.")
    print("Run individual demos in tests/demo/ or agents/*/agent.py")
    print("\nContrast demos (WITH vs WITHOUT) available in tests/demo/")


if __name__ == "__main__":
    main()
