"""cohermes · cg — the textual layer: ingest project prose as retrievable context.

The structured spine (Decision/Task/Commit/Review nodes) is precise but terse.
Real project context — architecture, design rationale, current status — lives in
prose. Ingesting it as documents makes CG **chunk** it, embed it, and auto-extract
entities that link back to the source, so an agent asking "explain the auth
architecture" gets real content, not a one-line decision headline.
"""
import requests

from cg import config

_T = 120


def ingest_text(text: str, source: str = "cohermes-note") -> dict:
    """Ingest a prose note (architecture/design/status) into the shared brain.
    CG chunks + embeds it and extracts entities linked to the chunks."""
    r = requests.post(f"{config.SERVER_URL}/documents/texts", headers=config.headers(),
                      json={"texts": [text], "file_sources": [source]}, timeout=_T)
    r.raise_for_status()
    return r.json()


def doc_status() -> dict:
    """Counts of ingested documents by status (pending/processing/processed/failed)."""
    d = requests.get(f"{config.SERVER_URL}/documents", headers=config.headers(), timeout=30).json()
    return {k: len(v) for k, v in (d.get("statuses") or {}).items()}
