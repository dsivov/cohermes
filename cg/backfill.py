"""cohermes · cg — curated backfill: seed the brain from a real codebase (D11).

Not a repo-dump. Following the curation principle, we ingest the *durable why* —
each first-party module's **purpose** (from its docstring) and the project's design
docs — as retrievable prose + typed ``Module`` nodes. The raw code stays in git;
the brain gets the architecture, not a mirror.

Uses only stdlib ``ast`` (no imports of the target code). Run:

    python -m cg.backfill /path/to/repo --package cg --docs README.md cg/README.md
"""
import argparse
import ast
import os

from cg import graph, ingest


def module_summary(py_path: str) -> tuple[str, list[str]]:
    """(docstring, public top-level names) for a .py file, via ast (no import)."""
    with open(py_path) as fh:
        tree = ast.parse(fh.read())
    doc = (ast.get_docstring(tree) or "").strip()
    names = [n.name for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and not n.name.startswith("_")]
    return doc, names


def backfill(repo: str, package: str = "cg", docs: list[str] | None = None) -> dict:
    pkg_dir = os.path.join(repo, package)
    modules, notes = [], 0

    for fname in sorted(os.listdir(pkg_dir)):
        if not fname.endswith(".py") or fname == "__init__.py":
            continue
        rel = f"{package}/{fname}"
        doc, names = module_summary(os.path.join(pkg_dir, fname))
        if not doc:
            continue
        purpose = doc.splitlines()[0]
        graph.upsert_entity(rel, "Module", description=purpose, path=rel, purpose=doc)
        # ingest the module's purpose + API as curated prose (retrievable)
        ingest.ingest_text(
            f"Module {rel}: {doc}\n\nPublic API: {', '.join(names) or '(none)'}",
            source=f"module:{rel}")
        modules.append(rel)
        notes += 1

    for d in (docs or []):
        path = os.path.join(repo, d)
        if os.path.exists(path):
            with open(path) as fh:
                ingest.ingest_text(fh.read(), source=f"doc:{d}")
            notes += 1

    return {"modules": modules, "ingested_notes": notes}


def main():
    ap = argparse.ArgumentParser(description="Curated backfill of a codebase into the brain")
    ap.add_argument("repo")
    ap.add_argument("--package", default="cg")
    ap.add_argument("--docs", nargs="*", default=["README.md", "cg/README.md"])
    args = ap.parse_args()
    out = backfill(args.repo, args.package, args.docs)
    print(f"backfilled {len(out['modules'])} modules + {out['ingested_notes']} notes "
          f"into '{ingest.config.WORKSPACE}':")
    for m in out["modules"]:
        print("  Module:", m)


if __name__ == "__main__":
    main()
