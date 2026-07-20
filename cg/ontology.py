"""cohermes · cg — the 4-artifact shared ontology (M1).

Defines the object types and cross-links that make a team's project one connected
'brain': Decision / Task / Commit / Review, chained

    Decision --motivates--> Task --implemented_by--> Commit --reviewed_in--> Review --enacts--> Decision

Decision carries the `developer` attribution stamp (D2). Installed with
POST /ontology (workspace-scoped by header). Pure JSON — no Context Graph import;
the server validates on save.

Run:  python -m cg.ontology        (install + verify into the configured workspace)
"""
import json
import requests

from cg import config

# CG ontology JSON (matches context_graph.ontology.schema Ontology.to_dict).
ONTOLOGY = {
    "name": "team-agent-dev",
    "version": 1,
    "object_types": [
        {"name": "Decision",
         "description": "A design/process choice and its rationale (the why).",
         "properties": [
             {"name": "title", "kind": "string", "required": True},
             {"name": "rationale", "kind": "text", "required": True,
              "description": "why this choice was made"},
             {"name": "status", "kind": "enum",
              "enum_values": ["proposed", "accepted", "superseded"]},
             {"name": "developer", "kind": "string", "required": True,
              "description": "who recorded it (D2 attribution stamp)"},
             {"name": "decided_at", "kind": "date"},
         ]},
        {"name": "Task", "description": "A unit of work.",
         "properties": [
             {"name": "title", "kind": "string", "required": True},
             {"name": "state", "kind": "enum",
              "enum_values": ["open", "in_progress", "in_review", "done"]},
             {"name": "assignee", "kind": "string",
              "description": "developer the task is assigned to"},
             {"name": "created_at", "kind": "date"},
         ]},
        {"name": "Commit", "description": "A git commit.",
         "properties": [
             {"name": "sha", "kind": "string", "required": True},
             {"name": "message", "kind": "text"},
             {"name": "author", "kind": "string"},
             {"name": "committed_at", "kind": "date"},
         ]},
        {"name": "Review", "description": "A code/PR review.",
         "properties": [
             {"name": "pr", "kind": "string", "description": "pull request id/url"},
             {"name": "verdict", "kind": "enum",
              "enum_values": ["approved", "changes_requested", "rejected"]},
             {"name": "reviewer", "kind": "string"},
             {"name": "summary", "kind": "text"},
         ]},
        {"name": "Module",
         "description": "A first-party code module and what it's for (backfilled).",
         "properties": [
             {"name": "path", "kind": "string"},
             {"name": "purpose", "kind": "text", "description": "what the module does"},
         ]},
        {"name": "Insight",
         "description": "A curated, durable learning about the project (D12) — "
                        "agent- or human-recorded, with provenance (D13).",
         "properties": [
             {"name": "insight", "kind": "text", "required": True,
              "description": "the distilled, confirmed learning"},
             {"name": "developer", "kind": "string", "required": True,
              "description": "who recorded it (D2 attribution)"},
             {"name": "confidence", "kind": "float",
              "description": "how confident, 0..1 (D13)"},
             {"name": "status", "kind": "enum",
              "enum_values": ["active", "superseded"]},
             {"name": "recorded_at", "kind": "date"},
         ]},
    ],
    "link_types": [
        {"name": "motivates", "source_types": ["Decision"], "target_types": ["Task"],
         "cardinality": "1:N", "description": "a decision motivates work"},
        {"name": "implemented_by", "source_types": ["Task"], "target_types": ["Commit"],
         "cardinality": "1:N", "description": "a task is implemented by commits"},
        {"name": "reviewed_in", "source_types": ["Commit"], "target_types": ["Review"],
         "cardinality": "N:1", "description": "commits are reviewed in a review"},
        {"name": "enacts", "source_types": ["Review"], "target_types": ["Decision"],
         "cardinality": "N:M", "description": "a review enacts/produces decisions"},
        {"name": "depends_on", "source_types": ["Task"], "target_types": ["Task"],
         "cardinality": "N:M", "description": "task dependency"},
        {"name": "informs", "source_types": ["Insight"], "target_types": [],
         "cardinality": "N:M", "description": "a learning informs a topic/artifact"},
        {"name": "supersedes", "source_types": ["Insight"], "target_types": ["Insight"],
         "cardinality": "N:M", "description": "a learning supersedes an earlier one"},
    ],
}


def install() -> dict:
    """POST the ontology into the configured workspace. Idempotent (replaces)."""
    r = requests.post(f"{config.SERVER_URL}/ontology", headers=config.headers(),
                      json={"ontology": ONTOLOGY}, timeout=30)
    r.raise_for_status()
    return r.json()


def summary() -> dict:
    return requests.get(f"{config.SERVER_URL}/ontology", headers=config.headers(),
                        timeout=30).json()


def main():
    print(f"installing ontology into '{config.WORKSPACE}' @ {config.SERVER_URL} ...")
    install()
    s = summary()
    print("object types:", [o["name"] for o in s.get("object_types", [])])
    print("link types  :", [f"{l['name']} ({'/'.join(l['source_types'])}→{'/'.join(l['target_types'])})"
                            for l in s.get("link_types", [])])


if __name__ == "__main__":
    main()
