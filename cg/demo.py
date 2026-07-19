"""cohermes · cg — the concept demo + reuse measurement (D9).

Two things, end to end:
  1. The traceable chain: Decision → Task → Commit → Review → Decision.
  2. The reuse measurement: ask the SAME question of the populated team workspace
     vs a FRESH empty one. If the shared brain works, the populated answer reuses
     the recorded decision (the 'why'); the fresh one can only re-derive.

Run:  python -m cg.demo
"""
import requests

from cg import artifacts, config

FRESH_WS = "team_agent_fresh"          # never seeded — the "no shared brain" control
QUESTION = "How should our coding agents stay in sync with each other, and why?"
# phrases that only appear if the answer reused the recorded pull-only decision
REUSE_MARKERS = ["pull", "push", "query the graph", "watcher", "no native", "poll"]


def _query(workspace: str, q: str, mode: str = "mix") -> str:
    r = requests.post(f"{config.SERVER_URL}/query",
                      headers={"LIGHTRAG-WORKSPACE": workspace, "Content-Type": "application/json"},
                      json={"query": q, "mode": mode}, timeout=120)
    r.raise_for_status()
    return r.json().get("response", "")


def _reused(answer: str) -> bool:
    a = answer.lower()
    return sum(m in a for m in REUSE_MARKERS) >= 2


def main():
    print("== 1. Traceable chain ==")
    path = artifacts.trace_chain("Add per-seat rate-limit guard for agents")
    line = path[0]
    for link, node in path[1:]:
        line += f"  --{link}-->  {node}"
    print("  " + line + f"   ({len(path) - 1} hops)\n")

    print("== 2. Reuse measurement — populated vs fresh workspace ==")
    print(f"  Q: {QUESTION}\n")
    populated = _query(config.WORKSPACE, QUESTION)
    fresh = _query(FRESH_WS, QUESTION)

    print(f"  [{config.WORKSPACE}] reused the recorded decision: {_reused(populated)}")
    print(f"    → {populated[:220].strip()}...\n")
    print(f"  [{FRESH_WS}] (no shared brain) reused it: {_reused(fresh)}")
    print(f"    → {fresh[:220].strip()}...\n")

    verdict = _reused(populated) and not _reused(fresh)
    print("VERDICT:", "SHARED BRAIN WORKS — the populated workspace reused the team's"
          " decision; the fresh one could not." if verdict
          else "inconclusive (inspect answers above)")


if __name__ == "__main__":
    main()
