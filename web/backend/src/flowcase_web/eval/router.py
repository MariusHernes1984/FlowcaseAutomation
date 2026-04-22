"""Admin-only endpoints for triggering and inspecting eval runs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from flowcase_web.auth.deps import require_admin
from flowcase_web.config import Settings, get_settings
from flowcase_web.eval import runner
from flowcase_web.eval import storage as eval_storage
from flowcase_web.eval.schema import (
    EvalRun,
    EvalRunSummary,
    TriggerEvalRequest,
)
from flowcase_web.models import User

router = APIRouter()


@router.get("", response_model=list[EvalRunSummary])
async def list_runs(_admin: User = Depends(require_admin)) -> list[EvalRunSummary]:
    return await eval_storage.list_recent(limit=50)


@router.get("/gold", response_model=dict)
async def get_gold(_admin: User = Depends(require_admin)) -> dict:
    gold = runner.load_gold()
    return {
        "count": len(gold.items),
        "items": [
            {
                "id": it.id,
                "agent": it.agent,
                "question": it.question,
                "qualitative": it.qualitative,
            }
            for it in gold.items
        ],
    }


@router.get("/{run_id}", response_model=EvalRun)
async def get_run(run_id: str, _admin: User = Depends(require_admin)) -> EvalRun:
    run = await eval_storage.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_run(
    body: TriggerEvalRequest,
    admin: User = Depends(require_admin),
    settings: Settings = Depends(get_settings),
) -> dict:
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        raise HTTPException(
            status_code=503, detail="Azure OpenAI not configured on this deployment"
        )
    run_id = await runner.run_eval(
        settings=settings,
        triggered_by=admin.email,
        only=body.only,
        judge_model=body.judge_model,
    )
    return {"run_id": run_id}
