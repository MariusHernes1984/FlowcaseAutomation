"""Pydantic models for gold items, transcripts and judge results.

Keeps the runner/judge/render modules free of ad-hoc dicts so typos
fail at import time rather than at run time.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class GoldItem(BaseModel):
    id: str
    agent: str
    question: str
    must_call_tools: list[str] = Field(default_factory=list)
    must_call_tools_any: list[str] = Field(default_factory=list)
    must_include_args: dict[str, Any] = Field(default_factory=dict)
    must_mention_any: list[str] = Field(default_factory=list)
    must_mention_all: list[str] = Field(default_factory=list)
    must_not_mention: list[str] = Field(default_factory=list)
    qualitative: list[str] = Field(default_factory=list)


class GoldSet(BaseModel):
    items: list[GoldItem]


class ToolInvocation(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_preview: str = ""
    truncated: bool = False


class Transcript(BaseModel):
    agent: str
    question: str
    final_text: str = ""
    tool_calls: list[ToolInvocation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    elapsed_seconds: float = 0.0


Pass = Literal["pass", "fail", "skip"]


class MachineCheck(BaseModel):
    name: str
    status: Pass
    detail: str = ""


class MachineChecks(BaseModel):
    checks: list[MachineCheck]

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == "fail")

    @property
    def total(self) -> int:
        return sum(1 for c in self.checks if c.status != "skip")


class CriterionResult(BaseModel):
    criterion: str
    met: bool
    reason: str = ""


class JudgeScores(BaseModel):
    correctness: int = Field(ge=1, le=5)
    completeness: int = Field(ge=1, le=5)
    honesty: int = Field(ge=1, le=5)
    presentation: int = Field(ge=1, le=5)

    @property
    def average(self) -> float:
        return (
            self.correctness
            + self.completeness
            + self.honesty
            + self.presentation
        ) / 4


class JudgeResult(BaseModel):
    scores: JudgeScores
    criteria_results: list[CriterionResult] = Field(default_factory=list)
    overall: int = Field(ge=1, le=5)
    notes: str = ""
    judge_model: str = ""
    judge_raw: str = ""


class ItemResult(BaseModel):
    gold: GoldItem
    transcript: Transcript
    machine: MachineChecks
    judgement: JudgeResult | None = None


class RunSummary(BaseModel):
    run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    target: str
    judge_model: str
    num_items: int
    items: list[ItemResult] = Field(default_factory=list)

    @property
    def aggregate(self) -> dict[str, float]:
        if not self.items or not all(it.judgement for it in self.items):
            return {}
        scores = [it.judgement.scores for it in self.items if it.judgement]
        return {
            "correctness": round(sum(s.correctness for s in scores) / len(scores), 2),
            "completeness": round(sum(s.completeness for s in scores) / len(scores), 2),
            "honesty": round(sum(s.honesty for s in scores) / len(scores), 2),
            "presentation": round(sum(s.presentation for s in scores) / len(scores), 2),
            "overall": round(
                sum((it.judgement.overall if it.judgement else 0) for it in self.items)
                / max(len(self.items), 1),
                2,
            ),
        }
