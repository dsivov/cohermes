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

## Coordinator + worker

**A2 correction (2026-07).** A2 means agents run on the Claude **subscription**, not metered
API billing — but only the real **first-party `claude` binary draws from plan limits**.
Anthropic's 2026-07 policy change routes third-party OAuth calls (Hermes's own agent loop
included) through paid **extra-usage**, so Hermes-as-a-model is metered *now*. Consequently all
real reasoning must run through the actual `claude` CLI.

So cohermes splits the roles:

- **Coordinator** — a cheap model. Routes work and does **Context Graph interaction** (orient /
  query precedent / record decisions). It never produces the substantive answer itself, and is
  stripped of file/terminal/code tools so it can't try.
- **Worker** — **opus, the first-party `claude` binary** (plan limits). Does all substantive
  work: plans, architecture, design, decisions, code.

Delegation is enforced in code, not by prompt: the **`ask_claude`** tool (`cg/mcp_server.py`)
runs the real `claude -p` via subprocess with list-args (no shell-quoting bugs), A2-scrubs the
env, and returns opus's output — the coordinator's only work channel. See
[`COORDINATOR.md`](COORDINATOR.md) for the coordinator role guide (drop it at a project's
`.hermes/SOUL.md`).

**Coordinator model** (a per-developer, gitignored choice in `<project>/.hermes/config.yaml`):

- **Recommended: Bedrock Gemma 4 31B** — hosted, fast (~6–10s/turn), capable. OpenAI-compatible
  endpoint; **must set `extra_body: { parallel_tool_calls: false }`** (Bedrock Gemma 4 has no
  parallel tool calls and hangs without it). Auth with a Bedrock API key / bearer token.
- **Alternative: a local model** (llama.cpp / Ollama) serving a **≥64K** context window (Hermes's
  floor) — viable but slower/weaker than Bedrock Gemma 4 31B.

The two flavors are both first-party for the actual reasoning: the **Claude Code flavor**
(`cohermes agent`) where opus *is* the agent, and the **Hermes-coordinator flavor** above (cheap
coordinator + Hermes orchestration around opus workers) for automation / multi-agent.

## Setup

```bash
# point at your CG server + project workspace
export COHERMES_CG_URL=http://<cg-host>:9621
export COHERMES_CG_WORKSPACE=<your-project>

python -m cg.ontology     # install the shared ontology (idempotent)
```

## The loop (per developer)

```bash
python -m cg.preset ./my-repo    # writes .mcp.json + CLAUDE.md loop + slash-commands
python -m cg.auth                # assert Claude runs on your subscription, not API billing
```
Then the agent follows: **orient → query-before-build → work → record-the-why**, all
through the `context-graph` MCP tools.

## Cross-agent sync (pull-only, reuses Hermes cron)

Hermes has no agent↔agent bus, so sync is **pull**: `cg/watch.py` polls the graph,
diffs a cursor, and prints what teammates changed. A Hermes routine runs it:

```bash
hermes cron create "every 15m" \
  "Summarize what teammates changed in the Context Graph, then post it." \
  --script ~/.hermes/scripts/watch-context-graph.py --deliver slack
```

## Status

Milestones **M1 (ontology)**, **M2 (loop preset + auth guard)**, **M3 (four artifacts
+ GitHub review connector)**, **M4 (pull-sync watcher)** — done. The full chain
`Decision→Task→Commit→Review→Decision` records, cross-links, and traces; a teammate's
agent finds prior decisions via precedent search instead of re-deriving them.

Later: swap Hermes's per-user `MEMORY.md` for CG as the memory provider (deeper
runtime integration).

Design log & decisions: `Context_Graph/docs/TEAM_AGENT_FRAMEWORK.html`.
