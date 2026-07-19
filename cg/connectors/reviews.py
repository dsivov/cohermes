"""cohermes · cg · connectors — GitHub PR review connector (M3, D8).

Ingests real pull-request reviews into the shared graph as **Review** nodes, linked
to the PR's **Commits** (``reviewed_in``) and — when the PR body names a decision —
to that **Decision** (``enacts``). This is what turns the chain from synthetic into
one fed by actual team activity.

Thin **Review boundary** (D8): the normalized ``PullRequest`` / ``PRReview`` shapes
are provider-independent; only ``_normalize_github`` knows GitHub's JSON. A live
``GitHubSource`` (token) and an offline ``FixtureSource`` return the same shapes, so
a second host (GitLab) is additive — no rewrite.

Run:  python -m cg.connectors.reviews        (ingest the bundled PR #42 fixture)
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from cg import artifacts, config

# GitHub review state → our ontology verdict enum (COMMENTED has no verdict).
_VERDICT = {"APPROVED": "approved", "CHANGES_REQUESTED": "changes_requested",
            "DISMISSED": "rejected", "COMMENTED": None}
_DECISION_RE = re.compile(r"Decision:\s*(.+)", re.IGNORECASE)


@dataclass
class PRReview:
    reviewer: str
    summary: str
    verdict: Optional[str]          # normalized enum or None (a comment-only review)
    commit_sha: Optional[str]


@dataclass
class PullRequest:
    number: int
    title: str
    commits: List[tuple]            # (sha, message, author)
    reviews: List[PRReview]
    decision_ref: Optional[str] = None   # a Decision title parsed from the PR body
    _shas: List[str] = field(default_factory=list)


def _normalize_github(pr: dict, commits: list, reviews: list) -> PullRequest:
    """Provider-specific: GitHub raw JSON → the neutral PullRequest shape."""
    shas = [c["sha"] for c in commits]
    body = pr.get("body") or ""
    m = _DECISION_RE.search(body)
    return PullRequest(
        number=pr["number"], title=pr.get("title", ""),
        commits=[(c["sha"], c["commit"]["message"], c["commit"]["author"]["name"]) for c in commits],
        reviews=[PRReview(reviewer=r["user"]["login"], summary=r.get("body", ""),
                          verdict=_VERDICT.get(r.get("state")), commit_sha=r.get("commit_id"))
                 for r in reviews],
        decision_ref=m.group(1).strip() if m else None,
        _shas=shas,
    )


class FixtureSource:
    """Offline source — reads a GitHub-shaped fixture (no token needed)."""
    def __init__(self, path: str):
        self.path = path

    def fetch(self) -> PullRequest:
        with open(self.path) as fh:
            data = json.load(fh)
        return _normalize_github(data["pull_request"], data["commits"], data["reviews"])


class GitHubSource:
    """Live source — GitHub PR reviews API (needs a token). Same normalizer."""
    def __init__(self, owner: str, repo: str, number: int, token: Optional[str] = None):
        self.owner, self.repo, self.number = owner, repo, number
        self.token = token or os.environ.get("GITHUB_TOKEN")

    def _get(self, path: str):
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        r = requests.get(f"https://api.github.com{path}", headers=h, timeout=30)
        r.raise_for_status()
        return r.json()

    def fetch(self) -> PullRequest:
        base = f"/repos/{self.owner}/{self.repo}/pulls/{self.number}"
        return _normalize_github(self._get(base), self._get(base + "/commits"),
                                 self._get(base + "/reviews"))


def ingest(pr: PullRequest) -> dict:
    """Write the PR's commits, reviews, and their links into the shared graph."""
    for sha, message, author in pr.commits:
        artifacts.commit(sha, message, author)

    written = []
    for rv in pr.reviews:
        rname = f"review of #{pr.number} by {rv.reviewer}"
        artifacts.review(rname, reviewer=rv.reviewer, summary=rv.summary,
                         verdict=rv.verdict, pr=f"#{pr.number}")
        for sha in (pr._shas or [c[0] for c in pr.commits]):
            artifacts.reviewed_in(sha, rname)
        if pr.decision_ref:                       # tie reviews back into the chain
            artifacts.enacts(rname, pr.decision_ref)
        written.append(rname)
    return {"pr": pr.number, "commits": [c[0] for c in pr.commits],
            "reviews": written, "decision_ref": pr.decision_ref}


FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "pr_42.json")


if __name__ == "__main__":
    print(f"ingesting fixture PR into '{config.WORKSPACE}' ...")
    pr = FixtureSource(FIXTURE).fetch()
    print(f"  PR #{pr.number}: {pr.title!r}  · decision_ref={pr.decision_ref!r}")
    for rv in pr.reviews:
        print(f"    review by {rv.reviewer}: verdict={rv.verdict}")
    out = ingest(pr)
    print("  ingested reviews:", out["reviews"])

    # verify the reviews joined the chain
    print("\nchain trace from the Decision (now backed by real PR reviews):")
    path = artifacts.trace_chain(pr.decision_ref)
    line = path[0]
    for link, node in path[1:]:
        line += f"  --{link}-->  {node}"
    print("  " + line)
