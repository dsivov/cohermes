#!/usr/bin/env python3
"""Hermes cron `--script` entry for the cohermes pull-watcher (M4, D5).

Deploy: copy to ``~/.hermes/scripts/`` (Hermes runs cron scripts path-jailed there)
with cohermes importable (``pip install -e /path/to/cohermes`` or set PYTHONPATH),
then register a routine — Hermes's own scheduler is the sync mechanism:

    hermes cron create "every 15m" \\
      "Summarize what teammates changed in the team Context Graph, then post it." \\
      --script ~/.hermes/scripts/watch-context-graph.py --deliver slack

The script prints new artifacts to stdout; Hermes feeds that to the agent as
context and delivers the agent's summary to the channel.
"""
from cg.watch import main

if __name__ == "__main__":
    main()
