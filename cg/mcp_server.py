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


@mcp.tool()
def ask_claude(task: str, workdir: str = ".", max_turns: int = 20) -> str:
    """Delegate a task to Claude Code (opus) — the FIRST-PARTY `claude` binary on the
    Claude subscription. Runs the real Claude Code CLI and returns its output.

    USE THIS FOR ALL SUBSTANTIVE WORK: work plans, architecture, design, decisions,
    analysis, and any code. As the coordinator you must NOT produce these yourself —
    pass the user's request here verbatim (plus any context) and relay the result.
    `workdir` is the project directory Claude runs in (it auto-reads CLAUDE.md + the
    repo, so you rarely need to paste files). This tool constructs the invocation
    safely, so you never hand-build shell strings."""
    import os
    import subprocess

    wd = os.path.abspath(os.path.expanduser(workdir or "."))
    # A2: run Claude Code first-party — scrub anything that would meter it.
    env = {k: v for k, v in os.environ.items() if k not in (
        "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")}
    try:
        proc = subprocess.run(
            ["claude", "-p", task, "--max-turns", str(max_turns)],
            cwd=wd, env=env, capture_output=True, text=True, timeout=900)
    except FileNotFoundError:
        return "ERROR: the `claude` CLI is not installed or not on PATH."
    except subprocess.TimeoutExpired:
        return "ERROR: Claude Code timed out (900s)."
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0 and not out:
        return f"ERROR (claude exit {proc.returncode}): {err[:500]}"
    return out or err or "(no output)"


@mcp.tool()
def whoami() -> str:
    """Report the workspace and developer this agent acts for."""
    return f"workspace={config.WORKSPACE}, developer={config.DEVELOPER or 'unset'}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
