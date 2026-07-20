"""cohermes · cg — curated learnings (D12/D13): promote understanding, not memory.

The antidote to semantic drift. An agent (or human) promotes a *confirmed,
distilled* learning — "this subsystem works like…", "approach X failed", "always
do Y" — into the shared brain, so every teammate's agent shares that understanding.

A learning is stored as **both**:
  · a typed ``Insight`` node — attributed, confidence-scored, with a validity
    ``status`` (active/superseded) so the brain models *was-true* vs *is-true* (D13);
  · **ingested prose** (a chunk) — so agents can retrieve and *explain* it, not just
    list it.

Curated promotion only (D12): this is a deliberate call, never a raw-memory dump.
"""
import datetime

from cg import graph, ingest


def record(title: str, insight: str, developer: str, about: str | None = None,
           confidence: float = 0.8, supersedes: str | None = None) -> dict:
    """Promote a curated learning. ``title`` names the Insight node; ``insight`` is
    the full text; ``about`` (optional) links it to a topic/artifact it informs;
    ``supersedes`` (optional) retires an earlier Insight by name."""
    today = datetime.date.today().isoformat()

    graph.upsert_entity(title, "Insight", description=insight, insight=insight,
                        developer=developer, confidence=confidence,
                        status="active", recorded_at=today)
    # ingest the prose so the learning is retrievable, not just structured
    ingest.ingest_text(insight, source=f"learning:{title}")

    links = []
    if about:
        # ensure the topic node exists (relation/create needs both endpoints)
        graph.upsert_entity(about, "Topic", description=about)
        graph.relate(title, about, "informs")
        links.append(f"informs {about}")
    if supersedes:
        graph.upsert_entity(supersedes, "Insight", status="superseded")
        graph.relate(title, supersedes, "supersedes")
        links.append(f"supersedes {supersedes}")

    return {"insight": title, "by": developer, "confidence": confidence, "links": links}


def active_learnings() -> list:
    """All Insight nodes not marked superseded (what the team currently believes)."""
    kg = graph.fetch()
    out = []
    for n in kg.get("nodes", []):
        p = n.get("properties", {}) or {}
        if p.get("entity_type") == "Insight" and p.get("status") != "superseded":
            out.append({"title": n["id"], "by": p.get("developer"),
                        "confidence": p.get("confidence")})
    return out


if __name__ == "__main__":
    print("recording a curated learning ...")
    out = record(
        title="MCP record_decision is trace-only",
        insight=("Context Graph's built-in record_decision MCP tool writes only an "
                 "edge trace, not a typed node. For a cross-linkable Decision node, "
                 "use the cohermes record_decision tool instead."),
        developer="dima", about="cohermes tool architecture", confidence=0.95)
    print(" ", out)
    print("active learnings:", [l["title"] for l in active_learnings()])
