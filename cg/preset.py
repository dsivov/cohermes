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
4. **Record the why** — when you make a decision, call `record_decision` with a
   clear `title`, `rationale`, `status`, and the **`developer`** (who you're acting
   for). Advance task/commit/review state as you go. The next agent — or teammate —
   will query this.

Auth: cohermes runs Claude Code on your **Claude subscription**, never metered API
billing. If a preflight ever reports API billing, stop and fix it (`unset
ANTHROPIC_API_KEY`).
"""

COMMANDS = {
    "cg-orient.md": """\
---
description: Orient in the shared Context Graph before starting work
---
Call the `get_manifest` MCP tool for this workspace and read `cg/PLAYBOOK.md`.
Summarize, in a few lines: the object types available, the guardrails/rules in
force, and any governed actions. This is the shared context the whole team works
within — establish it before we build.
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
Record this decision into the shared Context Graph with the `record_decision` MCP
tool: a clear `title`, the `rationale` (the *why*), a `status`, and the `developer`
you are acting for. Decision: **$ARGUMENTS**. Confirm it was written so teammates'
agents can find it.
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
    # pre-approve the CG MCP server so the agent can use it without a trust prompt
    _write(os.path.join(".claude", "settings.local.json"),
           json.dumps({"enableAllProjectMcpServers": True}, indent=2) + "\n")
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
