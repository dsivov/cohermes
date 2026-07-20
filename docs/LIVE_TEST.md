# cohermes — live-test runbook (2 developers, CLI + UI)

End-to-end validation of cohermes on real machines: two developers, each with a
Claude Code agent, sharing one Context Graph — proving the loop (orient →
query-before-build → work → record-the-why → reuse) live.

## 0 · Prerequisites

- A running **Context Graph** server (this repo's backend), e.g. `http://<cg-host>:9621`.
- **Claude Code** installed and logged in on a **Pro/Max/Team subscription**
  (`claude auth status` → `authMethod: claude.ai`). Not an API key (cohermes A2).
- Python 3.12. (For the Hermes-orchestrated flow, also the Hermes prerequisites.)

## 1 · Install cohermes (each developer)

```bash
git clone https://github.com/dsivov/cohermes && cd cohermes
python -m venv .venv && . .venv/bin/activate
pip install -e .            # installs Hermes + the cg extension + console scripts
```
This gives `hermes`, `cohermes-mcp`, `cohermes-preset`, `cohermes-backfill`,
`cohermes-ontology`, `cohermes-install-hook`. `cg` imports without PYTHONPATH.

## 2 · Point at the shared project brain

```bash
export COHERMES_CG_URL=http://<cg-host>:9621
export COHERMES_CG_WORKSPACE=<your-project>      # one workspace = one project
cohermes-ontology                                # install the shared ontology (once, any dev)
cohermes-backfill /path/to/project --docs README.md   # optional: curated seed (once)
```

## 3 · Wire each developer's project (distinct identity)

```bash
# Dev A
COHERMES_DEVELOPER=alice cohermes-preset /path/to/repo-A --developer alice
# Dev B
COHERMES_DEVELOPER=bob   cohermes-preset /path/to/repo-B --developer bob
```
Writes each repo's `.mcp.json` (context-graph + local cohermes MCP servers), the
`CLAUDE.md` loop stamped with that developer, slash-commands, and MCP pre-approval.

## 4 · CLI test — the two-developer scenario

**Dev A** (in repo-A): `claude` — make a decision on the task; the agent records it
(`record_decision`, stamped `alice`) and may `ingest_context` / `record_learning`.

**Dev B** (in repo-B, later): `claude` — start the related task with `/cg-orient <topic>`.
The agent is briefed from the shared brain: it should surface **Alice's** decision +
any learnings, and build on them (cite, don't re-derive). Verify with the CG WebUI
or `cohermes-... ` queries that Bob's follow-on links to Alice's decision.

Sync (optional): register the pull-watcher as a Hermes routine so Dev B is notified
of Dev A's changes —
```bash
hermes cron create "every 15m" "Summarize what teammates changed in the Context Graph, then post it." \
  --script "$(python -c 'import cg.watch,os;print(os.path.dirname(cg.watch.__file__))')/../scripts/watch-context-graph.py" \
  --deliver slack
```

## 5 · Hermes-orchestrated flow (the runtime hook)

```bash
cohermes-install-hook          # → ~/.hermes/hooks/cohermes/ (auth preflight + orient @ agent:start)
hermes                         # run Hermes; on each task the hook briefs from the brain
```
On `agent:start` the hook writes the orient brief to
`$HERMES_HOME/cohermes/brief-<session>.md` and asserts subscription auth.

## 6 · UI test

- **The shared brain** — open the Context Graph **WebUI** (`<cg-host>:9621/webui`,
  workspace `<your-project>`): watch both developers' decisions, the
  Decision→Task→Commit→Review chain, and Insight learnings appear in **one** graph.
- **Hermes UI** — the Hermes TUI / web dashboard (if orchestrating via Hermes).

## Success criteria

1. Two developers' work lands in **one** shared graph, attributed (alice/bob).
2. Dev B's agent **orients** and **reuses** Dev A's decision instead of re-deriving.
3. Everything runs on **subscription** auth (no metered API billing).
4. The chain is **traceable** and learnings are **retrievable** in the UI.
