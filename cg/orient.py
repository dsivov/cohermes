"""cohermes · cg — orient / read-from-brain (D12 loop, closed).

Before an agent builds, it should start from the team's *current understanding*,
not a blank private slate. ``brief(topic)`` synthesizes that: relevant prior
decisions, the active (non-superseded) team learnings, and project/architecture
context retrieved from the shared brain. The agent reads this at task start so it
begins aligned — the fuller drift-reduction we flagged in D12.
"""
import requests

from cg import config, decisions, learnings

_T = 120


def _query(q: str, mode: str = "mix") -> str:
    r = requests.post(f"{config.SERVER_URL}/query",
                      headers={"LIGHTRAG-WORKSPACE": config.WORKSPACE, "Content-Type": "application/json"},
                      json={"query": q, "mode": mode}, timeout=_T)
    r.raise_for_status()
    return r.json().get("response", "")


def brief(topic: str, top_k: int = 4) -> str:
    """A concise briefing on *topic* drawn from the shared brain."""
    out = [f"# Team brief — {topic}"]

    precs = decisions.precedents(topic, top_k=top_k)
    if precs:
        out.append("\n## Prior decisions (reuse these, don't re-derive)")
        for h in precs:
            rc = h.get("relation_context", {})
            out.append(f"- **{h.get('src_id')}** (by {rc.get('approved_by')}): "
                       f"{str(rc.get('decision_trace'))[:160]}")

    active = learnings.active_learnings()
    if active:
        out.append("\n## Active team learnings")
        for l in active:
            c = l.get("confidence")
            out.append(f"- **{l['title']}** (by {l['by']}"
                       + (f", conf {c}" if c is not None else "") + ")")

    ctx = _query(f"Summarize concisely what this project knows about: {topic}")
    if ctx:
        out.append("\n## Project / architecture context\n" + ctx.strip()[:600])

    return "\n".join(out)


if __name__ == "__main__":
    import sys
    print(brief(" ".join(sys.argv[1:]) or "how cohermes records and reuses decisions"))
