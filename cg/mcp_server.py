"""cohermes · cg — the cohermes MCP server (agent-facing tools).

A small local stdio MCP server the preset adds alongside CG's own `context-graph`
server. It exposes the richer cohermes operations agents need — the node+trace
decision record (D10), the artifact writers + cross-links (so agents build the
full chain, not just traces), and the textual layer (`ingest_context`). Every tool
talks to CG over HTTP via the cg.* helpers; nothing imports Context Graph.

Run (usually launched by a project's .mcp.json):  python -m cg.mcp_server
"""
from mcp.server.fastmcp import FastMCP

from cg import artifacts, config, decisions, ingest, learnings
from cg import orient as _orient

mcp = FastMCP("cohermes")


@mcp.tool()
def orient(topic: str) -> str:
    """START HERE for any task. Returns a briefing from the team's shared brain on
    `topic`: relevant prior decisions, active team learnings, and project/architecture
    context — so you begin aligned with what the team already knows and decided,
    instead of re-deriving it."""
    return _orient.brief(topic)


@mcp.tool()
def record_decision(title: str, rationale: str, developer: str, concerns: str,
                    status: str = "accepted") -> str:
    """Record a decision — ALWAYS use THIS tool for that.

    It writes a first-class **typed Decision node** (which cross-links into the
    Decision→Task→Commit→Review chain) AND emits a trace so precedent search finds
    it. Do NOT use context-graph's `record_decision` — that one writes only an edge
    trace, no node, so the decision can't be linked into the chain. `concerns` =
    what the decision is about; `developer` = who you act for (attribution)."""
    decisions.record(title, rationale, developer, concerns, status)
    return f"recorded Decision node '{title}' (+ precedent trace), by {developer}"


@mcp.tool()
def record_task(title: str, state: str = "open", assignee: str = "") -> str:
    """Create/update a Task node (state: open|in_progress|in_review|done)."""
    artifacts.task(title, state=state, assignee=assignee or None)
    return f"task '{title}' [{state}]" + (f" → {assignee}" if assignee else "")


@mcp.tool()
def record_commit(sha: str, message: str, author: str) -> str:
    """Create/update a Commit node."""
    artifacts.commit(sha, message, author)
    return f"commit {sha} by {author}"


@mcp.tool()
def record_review(name: str, reviewer: str, summary: str,
                  verdict: str = "", pr: str = "") -> str:
    """Create/update a Review node (verdict: approved|changes_requested|rejected)."""
    artifacts.review(name, reviewer=reviewer, summary=summary,
                     verdict=verdict or None, pr=pr or None)
    return f"review '{name}' by {reviewer}" + (f" [{verdict}]" if verdict else "")


@mcp.tool()
def link(source: str, target: str, relation: str) -> str:
    """Link two artifacts. relation ∈ motivates | implemented_by | reviewed_in |
    enacts | depends_on (forms the Decision→Task→Commit→Review→Decision chain)."""
    fn = {"motivates": artifacts.motivates, "implemented_by": artifacts.implemented_by,
          "reviewed_in": artifacts.reviewed_in, "enacts": artifacts.enacts}.get(relation)
    if fn is None:
        from cg import graph
        graph.relate(source, target, relation)
    else:
        fn(source, target)
    return f"{source} --{relation}--> {target}"


@mcp.tool()
def ingest_context(text: str, source: str = "cohermes-note") -> str:
    """Ingest project PROSE (architecture, design rationale, status) into the shared
    brain as retrievable chunks + extracted entities. Use this for depth beyond
    one-line decisions — so teammates' agents can *explain* the system, not just
    list its decisions. Extraction runs async; content becomes queryable shortly."""
    ingest.ingest_text(text, source=source)
    return f"ingested {len(text)} chars as '{source}' → chunks + extracted entities (async)"


@mcp.tool()
def record_learning(title: str, insight: str, developer: str, about: str = "",
                    confidence: float = 0.8, supersedes: str = "") -> str:
    """Promote a CURATED, confirmed learning about the project into the shared brain
    (the drift-killer): a durable insight like "subsystem X works like…", "approach
    Y failed", "always do Z". Stored as an attributed, confidence-scored Insight node
    AND retrievable prose. Use `about` to link the topic it informs, `supersedes` to
    retire a stale learning. Promote deliberately — do NOT dump raw session notes."""
    out = learnings.record(title, insight, developer, about=about or None,
                           confidence=confidence, supersedes=supersedes or None)
    tail = (" · " + ", ".join(out["links"])) if out["links"] else ""
    return f"recorded learning '{title}' (conf {confidence}, by {developer}){tail}"


def _record_outcome(task: str, output: str) -> None:
    """Land a delegated task's outcome in Context Graph as a searchable decision
    trace (WRITE half of the loop) — so the shared brain accumulates from real work
    and a future orient()/precedent search finds it. Ontology-neutral (a trace, not
    a typed node) so it never forks a project's own decision model. Best-effort."""
    import requests
    first = (task.strip().splitlines() or [""])[0]
    title = ("delegated: " + first)[:90]
    trace = (f"Delegated to opus (ask_claude): {task.strip()[:400]}\n\n"
             f"Outcome:\n{output.strip()[:1500]}")
    try:
        requests.post(
            f"{config.SERVER_URL.rstrip('/')}/graph/decision/emit",
            headers=config.headers(),
            json={"src": title, "tgt": "opus-delegation", "relation_type": "produced",
                  "relation_context": {
                      "decision_trace": trace,
                      "approved_by": config.DEVELOPER or "coordinator",
                      "provenance": "ask_claude", "confidence_score": 0.7}},
            timeout=30)
    except Exception:  # noqa: BLE001 — recording must never break the delegation
        pass


def _ask_claude_blocking(task: str, workdir: str, max_turns: int,
                         record: bool, write: bool) -> str:
    """Blocking body of ask_claude — runs in a worker thread so the MCP server's
    event loop stays responsive (answers keepalives) during the long opus run."""
    import os
    import subprocess

    wd = os.path.abspath(os.path.expanduser(workdir or "."))
    # A2: run Claude Code first-party — scrub anything that would meter it.
    env = {k: v for k, v in os.environ.items() if k not in (
        "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")}

    # 1) READ — ground opus in the shared brain (precedents + learnings + context).
    cmd = ["claude", "-p", task, "--max-turns", str(max_turns)]
    if write:
        # implementation mode: let opus actually edit files / run commands / tests.
        cmd.append("--dangerously-skip-permissions")
    try:
        brief = (_orient.brief(task) or "").strip()
    except Exception:  # noqa: BLE001
        brief = ""
    if brief:
        cmd += ["--append-system-prompt",
                "## Team brain (Context Graph) — reuse this, do not re-derive:\n\n" + brief]

    # 2) WORK — opus, first-party. Timeout matches the raised MCP call window (30 min).
    try:
        proc = subprocess.run(cmd, cwd=wd, env=env,
                              capture_output=True, text=True, timeout=1800)
    except FileNotFoundError:
        return "ERROR: the `claude` CLI is not installed or not on PATH."
    except subprocess.TimeoutExpired:
        return "ERROR: Claude Code timed out (1800s)."
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0 and not out:
        return f"ERROR (claude exit {proc.returncode}): {err[:500]}"
    result = out or err or "(no output)"

    # 3) WRITE — land the outcome in the brain so it accumulates + stays searchable.
    if record and out and not result.startswith("ERROR"):
        _record_outcome(task, result)
    return result


@mcp.tool()
async def ask_claude(task: str, workdir: str = ".", max_turns: int = 20,
                     record: bool = True, write: bool = False) -> str:
    """Delegate a task to Claude Code (opus) — the FIRST-PARTY `claude` binary on the
    Claude subscription — and close the shared-brain loop around it.

    USE THIS FOR ALL SUBSTANTIVE WORK: work plans, architecture, design, decisions,
    analysis, and any code. As the coordinator you must NOT produce these yourself —
    pass the user's request here verbatim and relay the result. This tool:
      1. READS the team brain — pulls Context Graph precedent/context for the task and
         injects it so opus reuses prior decisions instead of re-deriving them;
      2. runs opus (real `claude -p`, first-party, safe arg-passing — no shell strings);
      3. WRITES the outcome back to Context Graph as a searchable trace (set
         `record=False` for throwaway/trivial tasks) so the brain compounds.

    `write`: leave FALSE (default) for read-only work — plans, architecture, design,
    review, analysis (opus reads the repo but does not modify it). Set write=TRUE for
    tasks that must EDIT FILES or RUN COMMANDS — implement / fix / refactor / add
    tests / run the build — which gives opus full autonomy in the project directory.
    `workdir` is the project directory opus runs in (auto-reads CLAUDE.md + the repo).

    Long runs are fine: opus runs off the MCP event loop, so the server stays
    responsive; a big implementation can take many minutes."""
    import asyncio
    return await asyncio.to_thread(
        _ask_claude_blocking, task, workdir, max_turns, record, write)


_DONE_MARKER = "___COHERMES_DONE___"
_DELEGATIONS: dict = {}   # session -> {task, log, record, _recorded}


@mcp.tool()
def delegate_claude(task: str, workdir: str = ".", write: bool = False,
                    record: bool = True, max_turns: int = 30) -> str:
    """Delegate to opus (first-party `claude`) in a TMUX SESSION YOU CAN WATCH LIVE —
    for long or implementation work. Unlike `ask_claude` (which blocks), this returns
    IMMEDIATELY with the tmux session name; opus keeps working in the background, so
    there is no blocking and no MCP timeout. The human watches with
    `tmux attach -t <session>` (detach: Ctrl-b then d). Call **`check_claude(session)`**
    to fetch the result once it's done. `write=True` lets opus edit files / run tests —
    use it for implement / fix / refactor. Prefer this over ask_claude for anything the
    user wants to observe or that may run more than a couple of minutes."""
    import os
    import subprocess
    import time

    wd = os.path.abspath(os.path.expanduser(workdir or "."))
    work = os.path.join(wd, ".hermes", "cohermes-work")
    os.makedirs(work, exist_ok=True)
    # SINGLE-FLIGHT + predictable name: ONE delegation per project, named after it.
    # A confused coordinator that re-calls gets the SAME session back — never a
    # duplicate/runaway — and the human always knows how to attach.
    proj = "".join(c if (c.isalnum() or c in "-_") else "-"
                   for c in os.path.basename(wd)) or "project"
    sid = "cohermes-" + proj
    taskf = os.path.join(work, sid + ".task")
    brieff = os.path.join(work, sid + ".brief")
    logf = os.path.join(work, sid + ".log")
    runf = os.path.join(work, sid + ".sh")

    if subprocess.run(["tmux", "has-session", "-t", sid],
                      capture_output=True).returncode == 0:
        done = (os.path.exists(logf)
                and _DONE_MARKER in open(logf, encoding="utf-8", errors="replace").read())
        if not done:
            return (f"A delegation is ALREADY running in tmux session '{sid}'. Do NOT start "
                    f"another — watch it: `tmux attach -t {sid}` — and call `check_claude('{sid}')` "
                    f"for its result. One delegation per project at a time.")
        subprocess.run(["tmux", "kill-session", "-t", sid], capture_output=True)  # finished — recycle

    with open(taskf, "w", encoding="utf-8") as fh:
        fh.write(task)
    try:
        brief = (_orient.brief(task) or "").strip()
    except Exception:  # noqa: BLE001
        brief = ""
    with open(brieff, "w", encoding="utf-8") as fh:
        fh.write(("## Team brain (Context Graph) — reuse this, do not re-derive:\n\n" + brief)
                 if brief else "")

    perm = "--dangerously-skip-permissions " if write else ""
    brief_arg = f'--append-system-prompt-file "{brieff}" ' if brief else ""
    # Generate a runscript (no shell-quoting of task/brief — they're read from files).
    script = (
        "#!/usr/bin/env bash\n"
        f"cd {wd}\n"
        "unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN CLAUDE_CODE_USE_BEDROCK "
        "CLAUDE_CODE_USE_VERTEX CLAUDE_CODE_USE_FOUNDRY 2>/dev/null || true\n"
        f'claude -p "$(cat {taskf})" {brief_arg}{perm}--max-turns {max_turns} --verbose 2>&1 | tee {logf}\n'
        f'echo "{_DONE_MARKER} exit=${{PIPESTATUS[0]}}" | tee -a {logf}\n'
        'echo "[opus finished — result captured. detach with Ctrl-b then d]"\n'
        "exec bash\n")
    with open(runf, "w", encoding="utf-8") as fh:
        fh.write(script)
    os.chmod(runf, 0o755)

    try:
        subprocess.run(["tmux", "new-session", "-d", "-s", sid, "-x", "220", "-y", "50",
                        "bash", runf], check=True, capture_output=True, timeout=20)
    except FileNotFoundError:
        return "ERROR: tmux is not installed (needed for delegate_claude)."
    except Exception as e:  # noqa: BLE001
        return f"ERROR launching tmux session: {e}"

    _DELEGATIONS[sid] = {"task": task, "log": logf, "record": record}
    return (f"Delegated to opus in tmux session '{sid}' — running in the background.\n"
            f"  WATCH LIVE:   tmux attach -t {sid}    (detach: Ctrl-b then d)\n"
            f"  progress log: {logf}\n"
            f"  When it's done, call check_claude('{sid}') for the result.")


@mcp.tool()
def check_claude(session: str) -> str:
    """Check a `delegate_claude` tmux session. If opus has FINISHED, returns its output
    (and records it to Context Graph); otherwise returns 'still running' plus a live
    tail of its progress. The human can watch meanwhile: `tmux attach -t <session>`."""
    import os
    import subprocess

    info = _DELEGATIONS.get(session, {})
    logf = info.get("log")
    if not logf or not os.path.exists(logf):
        return (f"No active delegation '{session}' in this session (or its log is gone). "
                f"If you have the log path, read it directly.")
    text = open(logf, encoding="utf-8", errors="replace").read()
    if _DONE_MARKER in text:
        result = text.split(_DONE_MARKER)[0].strip()
        if info.get("record") and result and not info.get("_recorded"):
            _record_outcome(info.get("task", ""), result[-4000:])
            info["_recorded"] = True
        subprocess.run(["tmux", "kill-session", "-t", session],
                       capture_output=True)
        return "DONE — opus finished. Output (tail):\n\n" + result[-6000:]
    tail = "\n".join(text.splitlines()[-25:])
    return (f"Still running — opus is working (tmux attach -t {session} to watch live).\n"
            f"Recent progress:\n\n{tail}")


@mcp.tool()
def whoami() -> str:
    """Report the workspace and developer this agent acts for."""
    return f"workspace={config.WORKSPACE}, developer={config.DEVELOPER or 'unset'}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
