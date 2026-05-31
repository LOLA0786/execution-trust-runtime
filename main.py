#!/usr/bin/env python3
"""
main.py

Entry point that runs the polished business-focused CXO demo from tests.demo.full_demo.
Preserves all prior enforcement (stable Merkle, FirewalledExecutor, proxies, scoping, decorators).
"""
from tests.demo.full_demo import run_full_demo
from tests.demo.live_demo import run_live_demo
import logging
logging.basicConfig(level=logging.INFO)


def main():
    """Entry point. Use `python main.py --live` for the interactive live demo (Salesforce + Slack Reject)."""
    import sys
    if "--live" in sys.argv or "-l" in sys.argv:
        run_live_demo()
    else:
        run_full_demo()


if __name__ == "__main__":
    main()

