"""cohermes · cg — the pull-sync watcher (M4, D5).

Cross-agent sync is **pull-only, reusing Hermes's cron scheduler** (the one native
sync primitive — Hermes has no agent↔agent bus). This script polls the shared
Context Graph, diffs against a stored cursor, and prints the new artifacts to
stdout. A Hermes cron job runs it as its ``--script`` (its stdout becomes the
agent's context) and ``--deliver``s a summary to the team channel — mirroring
Hermes's own ``news-digest`` / ``kanban_watchers`` pattern:

    hermes cron create "every 15m" \\
      "Summarize what teammates changed in the Context Graph and post it." \\
      --script ~/.hermes/scripts/watch-context-graph.py --deliver slack

Pull-only = awareness, not writes: agents still write continuously; this just
tells a teammate's agent *what's new* without a push bus.

Run:  python -m cg.watch        (report new artifacts since the last run)
"""
import json
import os

from cg import config, graph

CURSOR = os.environ.get(
    "COHERMES_CURSOR", os.path.expanduser("~/.cohermes/cursor.json"))
_ARTIFACT_TYPES = ["Decision", "Task", "Commit", "Review"]


def _load_cursor() -> set:
    try:
        with open(CURSOR) as fh:
            return set(json.load(fh).get("seen_nodes", []))
    except FileNotFoundError:
        return set()


def _save_cursor(ids: set) -> None:
    os.makedirs(os.path.dirname(CURSOR) or ".", exist_ok=True)
    with open(CURSOR, "w") as fh:
        json.dump({"workspace": config.WORKSPACE, "seen_nodes": sorted(ids)}, fh)


def _who(props: dict) -> str:
    return props.get("developer") or props.get("author") or props.get("reviewer") or "?"


def poll() -> str:
    """Poll CG, diff vs cursor, advance it, and return a human-readable report."""
    kg = graph.fetch()
    nodes = {n["id"]: (n.get("properties", {}) or {}) for n in kg.get("nodes", [])}
    seen = _load_cursor()

    if not seen:  # first run — establish a baseline, don't spam every existing node
        _save_cursor(set(nodes))
        return (f"[cohermes] baseline established for '{config.WORKSPACE}': "
                f"{len(nodes)} artifacts tracked. Nothing to report yet.")

    new_ids = [nid for nid in nodes if nid not in seen]
    _save_cursor(seen | set(nodes))
    if not new_ids:
        return f"[cohermes] '{config.WORKSPACE}': no new artifacts since last check."

    lines = [f"[cohermes] {len(new_ids)} new artifact(s) in the team Context Graph "
             f"'{config.WORKSPACE}':"]
    shown = set()
    for t in _ARTIFACT_TYPES:
        for nid in new_ids:
            if nodes[nid].get("entity_type") == t:
                lines.append(f"  · {t}: {nid}  (by {_who(nodes[nid])})")
                shown.add(nid)
    other = [nid for nid in new_ids if nid not in shown]
    if other:
        lines.append(f"  · plus {len(other)} other node(s): {', '.join(other[:5])}"
                     + (" …" if len(other) > 5 else ""))
    return "\n".join(lines)


def main():
    print(poll())


if __name__ == "__main__":
    main()
