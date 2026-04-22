"""Entry point for a full eval run.

Usage:
    python tests/eval/run_eval.py \
        --target https://ca-flowcasemcp-dev-web.<hash>.norwayeast.azurecontainerapps.io \
        --email admin@atea.no \
        --password <...> \
        --judge-model gpt-5.4

Required env vars (or CLI flags):
    AZURE_OPENAI_ENDPOINT  — e.g. https://kateecosystem-resource.cognitiveservices.azure.com/
    AZURE_OPENAI_API_KEY   — same key used by the web orchestrator

Writes results to tests/eval/results/{timestamp}.{md,json}.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

# Allow running as a script without installing the package: add the
# repo root to sys.path so `tests.eval.*` imports resolve.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.eval.client import login, send_chat
from tests.eval.judge import Judge
from tests.eval.machine_checks import run_machine_checks
from tests.eval.render import write_outputs
from tests.eval.schema import GoldItem, GoldSet, ItemResult, RunSummary


async def run(args: argparse.Namespace) -> int:
    gold_path = Path(args.gold)
    gold = GoldSet(**yaml.safe_load(gold_path.read_text(encoding="utf-8")))

    if args.only:
        wanted = set(args.only)
        gold = GoldSet(items=[it for it in gold.items if it.id in wanted])
        if not gold.items:
            print(f"No gold items match --only {args.only}", file=sys.stderr)
            return 2

    judge = Judge(
        azure_endpoint=args.azure_openai_endpoint,
        api_key=args.azure_openai_api_key,
        model=args.judge_model,
    )

    summary = RunSummary(
        run_id=str(uuid.uuid4()),
        target=args.target,
        judge_model=args.judge_model,
        num_items=len(gold.items),
    )

    # Allow long reads — MCP bulk scans (data_export, CV fetches) can take
    # 30-60 s per turn especially on the first few requests after a restart.
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as http:
        print(f"Logging in as {args.email}…", file=sys.stderr)
        token = await login(http, args.target, args.email, args.password)

        for i, item in enumerate(gold.items, start=1):
            print(
                f"[{i}/{len(gold.items)}] {item.id} ({item.agent}) … ",
                end="",
                file=sys.stderr,
                flush=True,
            )
            try:
                transcript = await send_chat(
                    http, args.target, token, item.agent, item.question
                )
            except Exception as exc:
                print(
                    f"chat failed: {type(exc).__name__}: {exc!r}",
                    file=sys.stderr,
                )
                empty = _empty_transcript(
                    item, f"{type(exc).__name__}: {exc!r}"
                )
                summary.items.append(
                    ItemResult(
                        gold=item,
                        transcript=empty,
                        machine=run_machine_checks(item, empty),
                    )
                )
                continue

            machine = run_machine_checks(item, transcript)
            try:
                judgement = await judge.score(item, transcript)
            except Exception as exc:
                print(f"judge failed: {exc}", file=sys.stderr)
                judgement = None

            print(
                f"{transcript.elapsed_seconds}s "
                f"({machine.passed}/{machine.total} machine checks"
                f"{f', overall {judgement.overall}/5' if judgement else ''})",
                file=sys.stderr,
            )

            summary.items.append(
                ItemResult(
                    gold=item,
                    transcript=transcript,
                    machine=machine,
                    judgement=judgement,
                )
            )

    summary.finished_at = datetime.now(timezone.utc)
    md_path, json_path = write_outputs(summary, Path(args.output_dir))
    print(f"\nResults: {md_path}", file=sys.stderr)
    print(f"        {json_path}", file=sys.stderr)

    agg = summary.aggregate
    if agg:
        print(
            f"\nAggregate: overall={agg.get('overall')}, "
            f"correctness={agg.get('correctness')}, "
            f"completeness={agg.get('completeness')}, "
            f"honesty={agg.get('honesty')}, "
            f"presentation={agg.get('presentation')}",
            file=sys.stderr,
        )
    return 0


def _empty_transcript(item: GoldItem, error: str):  # type: ignore[no-untyped-def]
    from tests.eval.schema import Transcript

    return Transcript(agent=item.agent, question=item.question, errors=[error])


def _argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run Flowcase agent evaluation")
    p.add_argument(
        "--target",
        default=os.environ.get("EVAL_TARGET", "").rstrip("/"),
        help="Base URL of the web backend (with scheme, without trailing /).",
    )
    p.add_argument("--email", default=os.environ.get("EVAL_EMAIL", ""))
    p.add_argument("--password", default=os.environ.get("EVAL_PASSWORD", ""))
    p.add_argument(
        "--gold",
        default=str(Path(__file__).with_name("gold.yaml")),
        help="Path to the gold YAML file.",
    )
    p.add_argument(
        "--output-dir",
        default=str(Path(__file__).with_name("results")),
    )
    p.add_argument(
        "--judge-model",
        default=os.environ.get("EVAL_JUDGE_MODEL", "gpt-5.4"),
    )
    p.add_argument(
        "--azure-openai-endpoint",
        default=os.environ.get(
            "AZURE_OPENAI_ENDPOINT",
            "https://kateecosystem-resource.cognitiveservices.azure.com/",
        ),
    )
    p.add_argument(
        "--azure-openai-api-key",
        default=os.environ.get("AZURE_OPENAI_API_KEY", ""),
    )
    p.add_argument(
        "--only",
        nargs="+",
        help="Run only the given gold IDs (space-separated).",
    )
    return p


def main() -> int:
    args = _argparser().parse_args()
    if not args.target or not args.email or not args.password:
        print(
            "Missing --target/--email/--password (or EVAL_TARGET/EMAIL/PASSWORD env).",
            file=sys.stderr,
        )
        return 2
    if not args.azure_openai_api_key:
        print(
            "Missing --azure-openai-api-key (or AZURE_OPENAI_API_KEY env).",
            file=sys.stderr,
        )
        return 2
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
