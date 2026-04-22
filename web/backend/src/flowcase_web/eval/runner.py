"""Execute an evaluation run in-process and persist results to Cosmos."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import httpx
import yaml

from flowcase_web.config import Settings
from flowcase_web.eval import storage as eval_storage
from flowcase_web.eval.checks import run_machine_checks
from flowcase_web.eval.client import login, send_chat
from flowcase_web.eval.judge import Judge
from flowcase_web.eval.schema import (
    EvalRun,
    GoldItem,
    GoldSet,
    ItemResult,
    Transcript,
)

logger = logging.getLogger(__name__)


def _default_gold_path() -> Path:
    # Image layout: /app/gold.yaml (copied by the Dockerfile).
    env_path = Path("/app/gold.yaml")
    if env_path.exists():
        return env_path
    # Source tree fallback when running from a dev checkout.
    return Path(__file__).resolve().parents[4] / "tests" / "eval" / "gold.yaml"


def load_gold(path: Path | None = None) -> GoldSet:
    p = Path(path) if path else _default_gold_path()
    return GoldSet(**yaml.safe_load(p.read_text(encoding="utf-8")))


async def run_eval(
    *,
    run_id: str | None = None,
    settings: Settings,
    triggered_by: str,
    only: Iterable[str] | None = None,
    judge_model: str | None = None,
    gold_path: Path | None = None,
    target: str | None = None,
) -> str:
    """Kick off an eval run. Returns the run id; progress is streamed to
    Cosmos as each item completes, so the UI can poll."""
    gold = load_gold(gold_path)
    if only:
        wanted = set(only)
        gold = GoldSet(items=[it for it in gold.items if it.id in wanted])

    target_url = (target or f"http://127.0.0.1:{_self_port(settings)}").rstrip("/")
    judge = Judge(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        model=judge_model or "gpt-5.4",
    )

    run = EvalRun(
        id=run_id or str(uuid.uuid4()),
        target=target_url,
        judge_model=judge.model,
        num_items=len(gold.items),
        triggered_by=triggered_by,
    )
    await eval_storage.save(run)

    # Fire-and-forget — caller returns run id; work continues asynchronously.
    asyncio.create_task(
        _execute(run=run, settings=settings, gold=gold.items, judge=judge)
    )
    return run.id


def _self_port(settings: Settings) -> int:  # noqa: ARG001 — may read settings later
    import os

    return int(os.environ.get("PORT", "8001"))


async def _execute(
    *,
    run: EvalRun,
    settings: Settings,
    gold: list[GoldItem],
    judge: Judge,
) -> None:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as http:
            token = await login(
                http, run.target, settings.admin_email, settings.admin_password
            )

            for item in gold:
                try:
                    transcript = await send_chat(
                        http, run.target, token, item.agent, item.question
                    )
                except Exception as exc:
                    transcript = Transcript(
                        agent=item.agent,
                        question=item.question,
                        errors=[f"{type(exc).__name__}: {exc!r}"],
                    )

                machine = run_machine_checks(item, transcript)
                try:
                    judged = await judge.score(item, transcript)
                except Exception as exc:
                    logger.exception("Judge failed for %s", item.id)
                    judged = None
                    transcript.errors.append(f"judge_failed: {exc!r}")

                run.items.append(
                    ItemResult(
                        gold=item,
                        transcript=transcript,
                        machine=machine,
                        judgement=judged,
                    )
                )
                run.completed_items = len(run.items)
                await eval_storage.save(run)

        run.status = "succeeded"
    except Exception as exc:
        logger.exception("Eval run %s crashed", run.id)
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc!r}"
    finally:
        run.finished_at = datetime.now(timezone.utc)
        await eval_storage.save(run)
