# cohermes

**A team of AI coding agents that share one brain.**

cohermes is an extension of **[Hermes](https://github.com/NousResearch/hermes-agent)**
that swaps its per-user memory for a shared
**[Context Graph](https://github.com/dsivov/Context_Graph)**.

Hermes gives each developer a capable, autonomous personal agent — with memory that
is *private to that user*. cohermes points a whole **team's** agents at **one shared
Context Graph**: every agent reads project context *from* the graph and writes its
decisions, code reviews, tasks, and commits *back into* it. The team reasons over one
living project instead of _N_ amnesiac silos.

> Hermes remembers, per developer. cohermes makes the team remember — together.

## What cohermes adds

|              | Hermes                          | cohermes                                              |
|--------------|---------------------------------|-------------------------------------------------------|
| **Memory**   | per-user, local (`MEMORY.md`)   | **team-shared Context Graph** (governed, queryable)   |
| **Knowledge**| one operator's recall           | decisions · code reviews · tasks · commits, cross-linked |
| **Reuse**    | within your own sessions        | a teammate's *why* is reused, not re-derived          |
| **Sync**     | —                               | pull-only, via Hermes cron (no push bus needed)       |
| **Cost**     | your choice                     | **subscription-only**, enforced (never metered API)   |

Everything Hermes does — its runtime, 40+ tools, terminal backends, orchestration —
is inherited unchanged. cohermes is the [`cg/`](cg/) package on top.

## How it works

- **One project = one CG workspace**, selected by a header; fully isolated.
- **The loop, per developer:** orient → **query-before-build** → work → **record-the-why**,
  through the `context-graph` MCP tools.
- **The chain:** `Decision –motivates→ Task –implemented_by→ Commit –reviewed_in→ Review –enacts→ Decision`,
  all traceable.
- **Sync:** a cron watcher polls the graph and tells your agent what teammates changed.
- **Auth:** runs on your Claude subscription — a preflight guard refuses metered API billing.

## Quick start

```bash
# point at your Context Graph server + your project's workspace
export COHERMES_CG_URL=http://<cg-host>:9621
export COHERMES_CG_WORKSPACE=<your-project>

python -m cg.ontology            # install the shared 4-artifact ontology (once)
python -m cg.preset ./my-repo    # wire a repo: .mcp.json + CLAUDE.md loop + slash-commands
python -m cg.auth                # assert Claude runs on your subscription
```

See [`cg/README.md`](cg/README.md) for module details. The full design log and
decision record live in the companion Context Graph repo
(`docs/TEAM_AGENT_FRAMEWORK.html`).

## Status

Walking-skeleton MVP: the full chain records, cross-links, and traces; a teammate's
agent reuses prior decisions via precedent search instead of re-deriving them —
measured against a fresh control workspace.

## Credits & license

cohermes is a **fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)** (MIT).
The Hermes runtime, tools, and orchestration are the work of Nous Research; the
[`cg/`](cg/) extension is cohermes. The original Hermes README is preserved as
[`README.hermes.md`](README.hermes.md), and the upstream MIT license
(© 2025 Nous Research) is retained unchanged in [`LICENSE`](LICENSE).

Licensed under the MIT License.
