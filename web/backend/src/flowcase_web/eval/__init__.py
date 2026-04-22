"""Evaluation sub-system — runs curated gold questions against the live
agents, scores the output with an LLM-as-judge, and stores the
transcripts + scores in Cosmos for the admin dashboard.

The same core types live in tests/eval/ for the CLI harness; the
backend keeps its own copy so the image doesn't depend on the
repo-relative tests/ tree being mounted at runtime.
"""

from flowcase_web.eval.router import router

__all__ = ["router"]
