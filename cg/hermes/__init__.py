"""cohermes · cg · hermes — native integration with the Hermes runtime.

A Hermes event hook (HOOK.yaml + handler.py) that wires the shared Context Graph
into Hermes's agent lifecycle: subscription-auth preflight + orient (read-from-brain)
on ``agent:start``. Deploy it into ``~/.hermes/hooks/cohermes/``:

    python -m cg.hermes.install
"""
