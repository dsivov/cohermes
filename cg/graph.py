"""cohermes · cg — thin HTTP helpers for CG entity/relation CRUD.

Shared low-level layer used by the artifact writers. Entities are upserted
(edit, falling back to create); relations carry their link name in ``keywords``
so the chain can be traversed.
"""
import requests

from cg import config

_T = 30


def _url(p: str) -> str:
    return f"{config.SERVER_URL}{p}"


def upsert_entity(name: str, entity_type: str, description: str = "", **attrs) -> dict:
    """Create-or-update a typed entity node."""
    data = {"entity_type": entity_type, "description": description or name, **attrs}
    r = requests.post(_url("/graph/entity/edit"), headers=config.headers(),
                      json={"entity_name": name, "updated_data": data}, timeout=_T)
    if r.status_code >= 300:
        r = requests.post(_url("/graph/entity/create"), headers=config.headers(),
                          json={"entity_name": name, "entity_data": data}, timeout=_T)
    r.raise_for_status()
    return r.json()


def relate(src: str, tgt: str, link: str, weight: float = 1.0) -> dict:
    """Create a directed relation carrying ``link`` as its keyword."""
    r = requests.post(_url("/graph/relation/create"), headers=config.headers(),
                      json={"source_entity": src, "target_entity": tgt,
                            "relation_data": {"keywords": link,
                                              "description": f"{src} {link} {tgt}",
                                              "weight": weight}}, timeout=_T)
    if r.status_code == 400 and "already exists" in r.text:
        return {"status": "exists", "source": src, "target": tgt, "keywords": link}
    r.raise_for_status()
    return r.json()


def fetch() -> dict:
    """The whole workspace graph: {nodes:[{id,properties}], edges:[{source,target,properties}]}."""
    return requests.get(_url("/graphs"), headers=config.headers(),
                        params={"label": "*", "max_nodes": 1000, "max_depth": 6},
                        timeout=_T).json()


def edge_link(e: dict) -> str:
    """The link keyword of an edge (from properties.keywords, else its type)."""
    props = e.get("properties", {}) or {}
    return props.get("keywords") or e.get("type") or ""
