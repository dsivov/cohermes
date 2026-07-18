"""cohermes · cg — the Context Graph extension for Hermes.

Turns Hermes's per-user memory into a team-shared brain: every developer's agent
reads project context from, and writes decisions/reviews/tasks/commits to, one
shared Context Graph over its HTTP/MCP API.

This package talks to CG ONLY over HTTP — it does not import the Context Graph
Python package (a developer running cohermes won't have CG installed locally).

Design log: Context_Graph/docs/TEAM_AGENT_FRAMEWORK.html
"""
