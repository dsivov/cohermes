# cohermes · `cg` — the Context Graph extension

Turns Hermes's **per-user** memory into a **team-shared brain**. Every developer's
Hermes agent reads project context from, and writes decisions / code reviews /
tasks / commits to, one shared [Context Graph](https://github.com/dsivov/Context_Graph)
over its HTTP + MCP API.

This package is a **client of CG** — it talks to CG only over HTTP and never
imports the Context Graph Python package (a developer running cohermes won't have
CG installed locally).

## Model

- **One project = one CG workspace**, selected by the `LIGHTRAG-WORKSPACE` header
  (`cg/config.py`). Default lab workspace: `team_agent_lab`.
- **The 4-artifact ontology** (`cg/ontology.py`) is the shared shape:
  `Decision –motivates→ Task –implemented_by→ Commit –reviewed_in→ Review –enacts→ Decision`.
  The graph enforces link direction, so the chain can't be wired backwards.

## Setup

```bash
# point at your CG server + project workspace
export COHERMES_CG_URL=http://<cg-host>:9621
export COHERMES_CG_WORKSPACE=<your-project>

python -m cg.ontology     # install the shared ontology (idempotent)
```

## Status

Milestone **M1 (shared ontology)** — done. Next: M2 (the CG-native agent loop
preset), M3 (fill the four artifacts + GitHub review connector), M4 (wire into the
Hermes runtime + the pull-sync watcher).

Design log & decisions: `Context_Graph/docs/TEAM_AGENT_FRAMEWORK.html`.
