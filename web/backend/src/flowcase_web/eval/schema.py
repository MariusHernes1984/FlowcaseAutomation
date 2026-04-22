"""Pydantic models for gold items, transcripts, judge output, and run
summaries. Mirrors tests/eval/schema.py so results are interchangeable."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
            self.correctness + self.completeness + self.honesty + self.presentation
        ) / 4


class JudgeResult(BaseModel):
    scores: JudgeScores
    criteria_results: list[CriterionResult] = Field(default_factory=list)
    overall: int = Field(ge=1, le=5)
    notes: str = ""
    judge_model: str = ""


class ItemResult(BaseModel):
    gold: GoldItem
    transcript: Transcript
    machine: MachineChecks
    judgement: JudgeResult | None = None


RunStatus = Literal["running", "succeeded", "failed"]


class EvalRun(BaseModel):
    """Persisted record of an eval run stored in the Cosmos 'evaluations' container."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    status: RunStatus = "running"
    target: str
    judge_model: str
    gold_version: str = ""
    triggered_by: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    num_items: int = 0
    completed_items: int = 0
    items: list[ItemResult] = Field(default_factory=list)
    error: str | None = None

    def aggregate(self) -> dict[str, float]:
        judged = [it for it in self.items if it.judgement]
        if not judged:
            return {}
        n = len(judged)
        return {
            "correctness": round(sum(it.judgement.scores.correctness for it in judged) / n, 2),
            "completeness": round(sum(it.judgement.scores.completeness for it in judged) / n, 2),
            "honesty": round(sum(it.judgement.scores.honesty for it in judged) / n, 2),
            "presentation": round(sum(it.judgement.scores.presentation for it in judged) / n, 2),
            "overall": round(sum(it.judgement.overall for it in judged) / n, 2),
        }


class EvalRunSummary(BaseModel):
    """Trimmed list-view of an EvalRun."""

    id: str
    status: RunStatus
    target: str
    judge_model: str
    triggered_by: str
    started_at: datetime
    finished_at: datetime | None
    num_items: int
    completed_items: int
    aggregate: dict[str, float] = Field(default_factory=dict)
    error: str | None = None


class TriggerEvalRequest(BaseModel):
    only: list[str] | None = None
    judge_model: str | None = None
