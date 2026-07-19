"""cohermes · cg — configuration for the Context Graph backend.

One project = one shared CG workspace, selected by the LIGHTRAG-WORKSPACE header.
Override via env: COHERMES_CG_URL, COHERMES_CG_WORKSPACE.
"""
import os

SERVER_URL = os.environ.get("COHERMES_CG_URL", "http://10.0.0.80:9621")
WORKSPACE = os.environ.get("COHERMES_CG_WORKSPACE", "team_agent_lab")

# Per-developer identity (D2). MCP carries no authenticated principal, so identity
# is a per-developer config the agent stamps on its writes (attribution, not auth).
DEVELOPER = os.environ.get("COHERMES_DEVELOPER")   # who this agent acts for
ROLE = os.environ.get("COHERMES_ROLE", "developer")


def headers(extra: dict | None = None) -> dict:
    h = {"LIGHTRAG-WORKSPACE": WORKSPACE, "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h
