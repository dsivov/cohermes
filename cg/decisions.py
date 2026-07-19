"""cohermes · cg — decisions: node + trace, written by one operation (M3).

A Decision is a first-class **node** (type ``Decision``, structured fields, and the
anchor for the Decision→Task→Commit→Review chain). Recording one ALSO emits a
CG **decision-trace** so it lands in ``decisions_vdb`` and stays findable via
precedent search. One call writes both, so they can't drift.

The Decision node and the trace share the same entity NAME (the title), so they
are the same graph node — the trace just adds an rc-bearing edge to it.

Run:  python -m cg.decisions        (self-test: record a decision, then find it)
"""
import datetime

import requests

from cg import config

_T = 30


def record(title: str, rationale: str, developer: str, concerns: str,
           status: str = "accepted", confidence: float = 0.9) -> dict:
    """Record a decision as a node + a trace. ``concerns`` is what the decision is
    about (the trace's tail); ``developer`` is the D2 attribution stamp."""
    today = datetime.date.today().isoformat()

    # 1) the decision-trace first (creates the entities + rc edge → decisions_vdb).
    rc = {"decision_trace": rationale, "approved_by": developer,
          "confidence_score": confidence, "valid_from": today}
    tr = requests.post(f"{config.SERVER_URL}/graph/decision/emit", headers=config.headers(),
                       json={"src": title, "tgt": concerns, "relation_type": "decides",
                             "relation_context": rc}, timeout=_T)
    tr.raise_for_status()

    # 2) stamp the Decision node LAST so our type + structured fields win the merge.
    node = requests.post(f"{config.SERVER_URL}/graph/entity/edit", headers=config.headers(),
                         json={"entity_name": title, "updated_data": {
                             "description": rationale, "entity_type": "Decision",
                             "status": status, "developer": developer, "decided_at": today}},
                         timeout=_T)
    if node.status_code >= 300:  # entity may not support edit-create; fall back to create
        node = requests.post(f"{config.SERVER_URL}/graph/entity/create", headers=config.headers(),
                             json={"entity_name": title, "entity_data": {
                                 "description": rationale, "entity_type": "Decision",
                                 "status": status, "developer": developer, "decided_at": today}},
                             timeout=_T)
    return {"trace": tr.json(), "node": (node.json() if node.status_code < 300 else node.text),
            "node_status": node.status_code}


def precedents(query: str, top_k: int = 5) -> list:
    """Precedent search over recorded decisions (CG decisions_vdb). Returns a list
    of {src_id, tgt_id, relation_context{decision_trace, approved_by, ...}}."""
    r = requests.get(f"{config.SERVER_URL}/graph/decisions/search", headers=config.headers(),
                     params={"q": query, "top_k": top_k}, timeout=_T)
    r.raise_for_status()
    return r.json().get("results", [])


if __name__ == "__main__":
    print(f"recording a decision into '{config.WORKSPACE}' ...")
    out = record(
        title="Adopt pull-only cross-agent sync",
        rationale=("Agents learn of each other's changes by querying the graph fresh, "
                   "not via push. Hermes has no native agent-to-agent event bus, so a "
                   "scheduled watcher polling the Context Graph is the reusable path."),
        developer="dima", concerns="cross-agent sync strategy")
    print("  node_status:", out["node_status"])

    print("\nprecedent search (a DIFFERENT session would run this): 'how should agents stay in sync?'")
    for hit in precedents("how should agents stay in sync?", top_k=3):
        rc = hit.get("relation_context", {})
        print(f"  - {hit.get('src_id')} (by {rc.get('approved_by')}): {str(rc.get('decision_trace'))[:90]}...")
