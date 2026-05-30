#!/usr/bin/env python3
"""
main.py

Entry point that runs the polished business-focused CXO demo from tests.demo.full_demo.
Preserves all prior enforcement (stable Merkle, FirewalledExecutor, proxies, scoping, decorators).
"""
from tests.demo.full_demo import run_full_demo
import logging
logging.basicConfig(level=logging.INFO)


def main():
    """Runs the polished business CXO-ready demo matching the refined investor sample output."""
    run_full_demo()


if __name__ == "__main__":
    main()

