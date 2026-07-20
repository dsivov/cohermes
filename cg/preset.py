"""cohermes · cg — the CG-native agent loop preset (M2, D3).

Materializes the shared-brain loop into a project by REUSING CG's bootstrap
(GET /workspace/bootstrap): writes the ready ``.mcp.json``, saves the workspace
playbook, and drops a ``CLAUDE.md`` loop + slash-commands so *any* Claude Code
(Hermes-driven or not) follows: orient → query-before-build → work → record-the-why.

Run:  python -m cg.preset /path/to/project [--role developer]
"""
import argparse
import json
import os
import sys

import requests

from cg import config

LOOP_CLAUDE_MD = """\
# cohermes — shared-brain loop

**You act for developer `{developer}` (role: {role}).** Stamp every decision, task,
and review you record with `{developer}` (`approved_by` / `assignee` / `reviewer`),
so teammates know who did what.

This project shares its knowledge through a team **Context Graph** (workspace
`{workspace}`) over the `context-graph` MCP server. You are one of several agents
on this project; the graph is how you stay in sync with the rest of the team.

Follow this loop for every task:

1. **Orient** — before starting, call `get_manifest` (and read `cg/PLAYBOOK.md`) to
   see this project's object types, guardrails, and governed actions.
2. **Query before you build** — call `search_precedents` / `query_auto` to check
   whether the team has already decided or done this. **Reuse the reasoning; do not
   re-derive it.** Cite what you find.
3. **Work** — implement, staying inside the ontology and guardrails.
4. **Record the why** — record decisions ONLY with the **cohermes** `record_decision`
   tool (it writes a typed Decision *node* + a trace). **Do NOT use context-graph's
   `record_decision`** — that writes a trace with no node, so it can't link into the
   chain. Pass a clear `title`, `rationale`, `status`, `concerns`, and the
   **`developer`** you act for. Build the chain with `record_task`/`record_commit`/
   `record_review` + `link` (`motivates`/`implemented_by`/`reviewed_in`/`enacts`).
5. **Add depth** — when you learn or write something about the project's
   architecture, design, or status, call `ingest_context` so it becomes retrievable
   prose in the shared brain — not just a one-line decision. Teammates' agents will
   *explain* the system from it.

Auth: cohermes runs Claude Code on your **Claude subscription**, never metered API
billing. If a preflight ever reports API billing, stop and fix it (`unset
ANTHROPIC_API_KEY`).
"""

COMMANDS = {
    "cg-orient.md": """\
---
description: Orient from the shared brain before starting work ($ARGUMENTS)
argument-hint: <task topic>
---
Call the cohermes `orient` tool with the topic **$ARGUMENTS**. It briefs you from
the team's shared brain: relevant prior decisions, active team learnings, and
project/architecture context. Read it and start aligned — reuse what the team
already decided and learned instead of re-deriving it.
""",
    "cg-precedent.md": """\
---
description: Query the graph for precedent before building ($ARGUMENTS)
argument-hint: <topic or decision to check>
---
Before we build **$ARGUMENTS**, search the shared Context Graph for prior work.
Use `search_precedents` and `query_auto`. Report what the team has already decided
or done that relates — so we reuse the reasoning instead of re-deriving it. If
nothing exists, say so explicitly.
""",
    "cg-decide.md": """\
---
description: Record a decision (the why) into the shared graph
argument-hint: <decision + rationale>
---
Record this decision with the **cohermes** `record_decision` tool (it writes a typed
Decision node + trace) — NOT context-graph's `record_decision`. Pass a clear `title`,
the `rationale` (the *why*), a `status`, `concerns`, and the `developer` you are
acting for. Decision: **$ARGUMENTS**. Confirm it was written.
""",
}


def fetch_bootstrap(role: str = "developer") -> dict:
    r = requests.get(f"{config.SERVER_URL}/workspace/bootstrap",
                     headers=config.headers(), params={"role": role}, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_playbook(role: str = "developer") -> str:
    r = requests.get(f"{config.SERVER_URL}/workspace/playbook",
                     headers=config.headers(), params={"role": role, "format": "md"},
                     timeout=30)
    r.raise_for_status()
    return r.text


def install(target: str, role: str = "developer", developer: str | None = None) -> list[str]:
    """Write the loop preset into *target*. Returns the list of files written."""
    developer = developer or config.DEVELOPER or "this developer"
    boot = fetch_bootstrap(role)

    # add the cohermes MCP server (node+trace record, chain links, ingest_context)
    # alongside CG's own context-graph server, launched as a local stdio process.
    cohermes_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    boot.setdefault("mcp_config", {}).setdefault("mcpServers", {})["cohermes"] = {
        "command": sys.executable,
        "args": ["-m", "cg.mcp_server"],
        "env": {"PYTHONPATH": cohermes_root, "COHERMES_CG_URL": config.SERVER_URL,
                "COHERMES_CG_WORKSPACE": config.WORKSPACE, "COHERMES_DEVELOPER": developer},
    }
    written = []

    def _write(rel, content):
        path = os.path.join(target, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)
        written.append(rel)

    _write(".mcp.json", json.dumps(boot["mcp_config"], indent=2) + "\n")
    try:
        _write("cg/PLAYBOOK.md", fetch_playbook(role))
    except Exception:  # noqa: BLE001 - playbook is best-effort
        pass
    _write("CLAUDE.md", LOOP_CLAUDE_MD.format(
        workspace=config.WORKSPACE, developer=developer, role=role))
    # pre-approve the CG MCP server; and DENY context-graph's trace-only
    # record_decision so agents can only record via the cohermes node+trace tool.
    _write(os.path.join(".claude", "settings.local.json"),
           json.dumps({"enableAllProjectMcpServers": True,
                       "permissions": {"deny": [
                           "mcp__context-graph__record_decision",
                           "mcp__context_graph__record_decision"]}}, indent=2) + "\n")
    for name, body in COMMANDS.items():
        _write(os.path.join(".claude", "commands", name), body)
    return written


def main():
    ap = argparse.ArgumentParser(description="Install the cohermes CG-native loop preset")
    ap.add_argument("target", help="project directory to install into")
    ap.add_argument("--role", default="developer")
    ap.add_argument("--developer", default=None, help="who this agent acts for (D2 identity)")
    args = ap.parse_args()
    written = install(args.target, args.role, args.developer)
    dev = args.developer or config.DEVELOPER or "this developer"
    print(f"installed cohermes loop preset into {args.target} "
          f"(workspace={config.WORKSPACE}, developer={dev}):")
    for w in written:
        print("  +", w)
    print("\nnext: (re)connect the MCP client, then run /cg-orient")


if __name__ == "__main__":
    main()
