"""LLM-as-judge — grades a transcript against a gold item's criteria.

Uses Azure OpenAI on the kateecosystem-resource endpoint where the
stronger models live. Falls back to whatever model is passed in.
"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import AsyncAzureOpenAI

from tests.eval.schema import (
    CriterionResult,
    GoldItem,
    JudgeResult,
    JudgeScores,
    Transcript,
)

JUDGE_SYSTEM_PROMPT = """You are a rigorous QA evaluator for Atea's
Flowcase agents. You review how an agent handled a user question, with
full visibility into the tool calls it made and the final text it
produced.

Respond ONLY with strict JSON (no markdown fences, no commentary) using
this exact schema:

{
  "scores": {
    "correctness": <1-5 int>,
    "completeness": <1-5 int>,
    "honesty": <1-5 int>,
    "presentation": <1-5 int>
  },
  "overall": <1-5 int>,
  "criteria_results": [
    { "criterion": "<verbatim criterion>", "met": true|false, "reason": "<short>" }
  ],
  "notes": "<1-3 sentences on key strengths/weaknesses>"
}

Scoring guide (1 = terrible, 5 = excellent):
- correctness: called the right tools with sensible arguments, no made-up data
- completeness: answered what was actually asked
- honesty: surfaced zero-result cases, flagged uncertainty, didn't hallucinate
- presentation: clear Norwegian, structured, actionable
"""


def _build_user_prompt(item: GoldItem, transcript: Transcript) -> str:
    tool_lines: list[str] = []
    for tc in transcript.tool_calls:
        preview = (tc.result_preview or "").strip()
        if len(preview) > 1500:
            preview = preview[:1500] + "…"
        tool_lines.append(
            f"- {tc.name}(args={_pretty(tc.arguments)})\n"
            f"  result: {preview or '(empty)'}"
        )
    tools_block = "\n".join(tool_lines) or "(no tool calls)"

    return f"""User question ({item.agent}): {item.question}

AGENT TOOL CALLS:
{tools_block}

AGENT FINAL TEXT:
{transcript.final_text.strip() or '(empty)'}

QUALITATIVE CRITERIA TO EVALUATE (each must be judged true/false):
{chr(10).join(f'- {c}' for c in item.qualitative) or '- (none; score the general quality only)'}
"""


def _pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(obj)


class Judge:
    def __init__(
        self,
        *,
        azure_endpoint: str,
        api_key: str,
        api_version: str = "2024-10-21",
        model: str = "gpt-5.4",
    ) -> None:
        self._client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def score(self, item: GoldItem, transcript: Transcript) -> JudgeResult:
        user_prompt = _build_user_prompt(item, transcript)
        # GPT-5.4 uses `max_completion_tokens`; older deployments still
        # want `max_tokens`. Try the newer param first and fall back.
        common: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
        }
        try:
            response = await self._client.chat.completions.create(
                **common, max_completion_tokens=1200
            )
        except Exception as exc:
            if "max_tokens" in str(exc).lower() or "unsupported" in str(exc).lower():
                response = await self._client.chat.completions.create(
                    **common, max_tokens=1200
                )
            else:
                raise
        raw = response.choices[0].message.content or ""
        return _parse_judge_output(raw, judge_model=self._model, fallback_criteria=item.qualitative)


_JSON_BLOB_RE = re.compile(r"\{[\s\S]*\}")


def _parse_judge_output(
    raw: str, *, judge_model: str, fallback_criteria: list[str]
) -> JudgeResult:
    match = _JSON_BLOB_RE.search(raw.strip())
    payload: dict[str, Any] | None = None
    if match:
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            payload = None

    if not payload:
        # Judge failed to produce parseable JSON — record a neutral 3 with the
        # raw output in notes so we can diagnose later without exploding.
        return JudgeResult(
            scores=JudgeScores(
                correctness=3, completeness=3, honesty=3, presentation=3
            ),
            criteria_results=[
                CriterionResult(criterion=c, met=False, reason="judge output unparseable")
                for c in fallback_criteria
            ],
            overall=3,
            notes="Judge did not return parseable JSON; see raw output below.",
            judge_model=judge_model,
            judge_raw=raw,
        )

    scores_data = payload.get("scores") or {}
    try:
        scores = JudgeScores(
            correctness=int(scores_data.get("correctness", 3)),
            completeness=int(scores_data.get("completeness", 3)),
            honesty=int(scores_data.get("honesty", 3)),
            presentation=int(scores_data.get("presentation", 3)),
        )
    except Exception:
        scores = JudgeScores(correctness=3, completeness=3, honesty=3, presentation=3)

    criteria_data = payload.get("criteria_results") or []
    criteria: list[CriterionResult] = []
    for row in criteria_data:
        if not isinstance(row, dict):
            continue
        criteria.append(
            CriterionResult(
                criterion=str(row.get("criterion", "")),
                met=bool(row.get("met", False)),
                reason=str(row.get("reason", "")),
            )
        )

    overall_raw = payload.get("overall", round(scores.average))
    try:
        overall = int(overall_raw)
    except (TypeError, ValueError):
        overall = round(scores.average)
    overall = max(1, min(5, overall))

    return JudgeResult(
        scores=scores,
        criteria_results=criteria,
        overall=overall,
        notes=str(payload.get("notes", "")).strip(),
        judge_model=judge_model,
        judge_raw=raw,
    )
