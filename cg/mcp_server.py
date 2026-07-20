"""cohermes · cg — the cohermes MCP server (agent-facing tools).

A small local stdio MCP server the preset adds alongside CG's own `context-graph`
server. It exposes the richer cohermes operations agents need — the node+trace
decision record (D10), the artifact writers + cross-links (so agents build the
full chain, not just traces), and the textual layer (`ingest_context`). Every tool
talks to CG over HTTP via the cg.* helpers; nothing imports Context Graph.

Run (usually launched by a project's .mcp.json):  python -m cg.mcp_server
"""
from mcp.server.fastmcp import FastMCP

from cg import artifacts, config, decisions, ingest

mcp = FastMCP("cohermes")


@mcp.tool()
def record_decision(title: str, rationale: str, developer: str, concerns: str,
                    status: str = "accepted") -> str:
    """Record a decision as a first-class NODE **and** a precedent-searchable trace.

    Prefer this over the plain context-graph record_decision: it creates a typed
    Decision node that cross-links into the chain, *and* emits the trace so
    precedent search finds it. `concerns` = what the decision is about; `developer`
    = who you act for (attribution)."""
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
def whoami() -> str:
    """Report the workspace and developer this agent acts for."""
    return f"workspace={config.WORKSPACE}, developer={config.DEVELOPER or 'unset'}"


if __name__ == "__main__":
    mcp.run()
