"""cohermes · cg — the artifact writers + the cross-link chain (M3).

Task / Commit / Review node-writers and the four cross-links that form the
project chain:

    Decision --motivates--> Task --implemented_by--> Commit --reviewed_in--> Review --enacts--> Decision

Decisions are written by cg.decisions.record (node + trace). These writers cover
the other three node types and the links between all four, so a whole unit of work
becomes one traceable subgraph.

Run:  python -m cg.artifacts     (build a full chain, then trace it)
"""
from cg import decisions, graph


# -- node writers (the D2 attribution stamp rides on assignee/author/reviewer) --

def task(title: str, state: str = "open", assignee: str | None = None) -> dict:
    attrs = {"state": state}
    if assignee:
        attrs["assignee"] = assignee
    return graph.upsert_entity(title, "Task", description=title, **attrs)


def commit(sha: str, message: str, author: str) -> dict:
    return graph.upsert_entity(sha, "Commit", description=message, message=message, author=author)


def review(name: str, verdict: str, reviewer: str, summary: str, pr: str | None = None) -> dict:
    attrs = {"verdict": verdict, "reviewer": reviewer, "summary": summary}
    if pr:
        attrs["pr"] = pr
    return graph.upsert_entity(name, "Review", description=summary, **attrs)


# -- the cross-links (the chain) --

def motivates(decision: str, task_: str):      return graph.relate(decision, task_, "motivates")
def implemented_by(task_: str, commit_: str):  return graph.relate(task_, commit_, "implemented_by")
def reviewed_in(commit_: str, review_: str):   return graph.relate(commit_, review_, "reviewed_in")
def enacts(review_: str, decision: str):       return graph.relate(review_, decision, "enacts")


CHAIN_ORDER = ("motivates", "implemented_by", "reviewed_in", "enacts")


def trace_chain(start: str, order=CHAIN_ORDER) -> list:
    """Follow the chain links from *start*, returning [start, (link, node), ...].

    CG stores edges undirected (endpoints canonicalized), so we build an
    undirected link-indexed adjacency and follow each named link forward,
    avoiding an immediate backtrack.
    """
    kg = graph.fetch()
    adj = {}
    for e in kg["edges"]:
        lk = graph.edge_link(e)
        adj.setdefault((e["source"], lk), []).append(e["target"])
        adj.setdefault((e["target"], lk), []).append(e["source"])
    path, cur, prev = [start], start, None
    for link in order:
        cands = [n for n in adj.get((cur, link), []) if n != prev]
        if not cands:
            break
        prev, cur = cur, cands[0]
        path.append((link, cur))
    return path


if __name__ == "__main__":
    print(f"building a full chain in '{graph.config.WORKSPACE}' ...")
    D = "Add per-seat rate-limit guard for agents"
    decisions.record(
        title=D,
        rationale=("A fleet of always-on agents can exhaust a Claude subscription seat's "
                   "rolling window, so cohermes must pace/limit agent turns per seat."),
        developer="dima", concerns="agent rate limiting")
    T = "Implement per-seat rate-limit guard"
    C = "9f2c1ab"
    R = "review of #42 rate-limit guard"
    task(T, state="done", assignee="dima")
    commit(C, "add per-seat rate-limit guard", author="dima")
    review(R, verdict="approved", reviewer="sarah", summary="LGTM, good pacing default", pr="#42")

    motivates(D, T); implemented_by(T, C); reviewed_in(C, R); enacts(R, D)

    print("\nchain trace from the Decision:")
    path = trace_chain(D)
    line = path[0]
    for link, node in path[1:]:
        line += f"  --{link}-->  {node}"
    print("  " + line)
    print(f"  ({len(path) - 1} hops of the expected 4)")
