"""Cosmos CRUD for eval runs — `evaluations` container, partition /id."""

from __future__ import annotations

import logging
from typing import Any

from azure.cosmos import exceptions as cosmos_exc

from flowcase_web.eval.schema import EvalRun, EvalRunSummary
from flowcase_web.storage import get_handle

logger = logging.getLogger(__name__)


def _container() -> Any:
    return get_handle().evaluations


async def save(run: EvalRun) -> None:
    doc = run.model_dump(mode="json")
    await _container().upsert_item(body=doc)


async def get(run_id: str) -> EvalRun | None:
    try:
        doc = await _container().read_item(item=run_id, partition_key=run_id)
    except cosmos_exc.CosmosResourceNotFoundError:
        return None
    return EvalRun.model_validate(doc)


async def list_recent(*, limit: int = 50) -> list[EvalRunSummary]:
    out: list[EvalRunSummary] = []
    query = "SELECT * FROM e ORDER BY e.started_at DESC"
    async for doc in _container().query_items(query=query):
        run = EvalRun.model_validate(doc)
        out.append(
            EvalRunSummary(
                id=run.id,
                status=run.status,
                target=run.target,
                judge_model=run.judge_model,
                triggered_by=run.triggered_by,
                started_at=run.started_at,
                finished_at=run.finished_at,
                num_items=run.num_items,
                completed_items=run.completed_items,
                aggregate=run.aggregate(),
                error=run.error,
            )
        )
        if len(out) >= limit:
            break
    return out
