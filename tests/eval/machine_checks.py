"""Machine-verifiable checks from gold item against a run transcript.

Qualitative checks go to the judge; these are the hard guardrails we
can ground in the tool_calls and the final text without any LLM in the
loop.
"""

from __future__ import annotations

import json
from typing import Any

from tests.eval.schema import GoldItem, MachineCheck, MachineChecks, Transcript


def run_machine_checks(item: GoldItem, transcript: Transcript) -> MachineChecks:
    checks: list[MachineCheck] = []

    called = [tc.name for tc in transcript.tool_calls]

    if item.must_call_tools:
        missing = [t for t in item.must_call_tools if t not in called]
        checks.append(
            MachineCheck(
                name=f"must_call_tools {item.must_call_tools}",
                status="pass" if not missing else "fail",
                detail="OK" if not missing else f"missing: {missing}; called: {called}",
            )
        )

    if item.must_call_tools_any:
        any_hit = any(t in called for t in item.must_call_tools_any)
        checks.append(
            MachineCheck(
                name=f"must_call_tools_any {item.must_call_tools_any}",
                status="pass" if any_hit else "fail",
                detail=f"called: {called}",
            )
        )

    if item.must_include_args:
        matching = _args_match_any_tool(item.must_include_args, transcript)
        checks.append(
            MachineCheck(
                name=f"must_include_args {item.must_include_args}",
                status="pass" if matching else "fail",
                detail="OK" if matching else "no tool call had these args",
            )
        )

    text_lower = (transcript.final_text or "").lower()

    if item.must_mention_any:
        hit = next(
            (n for n in item.must_mention_any if n.lower() in text_lower), None
        )
        checks.append(
            MachineCheck(
                name=f"must_mention_any {item.must_mention_any}",
                status="pass" if hit else "fail",
                detail=f"matched: {hit!r}" if hit else "none found in final text",
            )
        )

    if item.must_mention_all:
        missing = [n for n in item.must_mention_all if n.lower() not in text_lower]
        checks.append(
            MachineCheck(
                name=f"must_mention_all {item.must_mention_all}",
                status="pass" if not missing else "fail",
                detail="OK" if not missing else f"missing: {missing}",
            )
        )

    if item.must_not_mention:
        hit = [n for n in item.must_not_mention if n.lower() in text_lower]
        checks.append(
            MachineCheck(
                name=f"must_not_mention {item.must_not_mention}",
                status="pass" if not hit else "fail",
                detail="OK" if not hit else f"found forbidden: {hit}",
            )
        )

    # Always-on guardrails
    checks.append(
        MachineCheck(
            name="no_stream_errors",
            status="pass" if not transcript.errors else "fail",
            detail="OK" if not transcript.errors else f"errors: {transcript.errors}",
        )
    )
    checks.append(
        MachineCheck(
            name="has_final_text",
            status="pass" if transcript.final_text.strip() else "fail",
            detail=f"{len(transcript.final_text)} chars",
        )
    )

    return MachineChecks(checks=checks)


def _args_match_any_tool(expected: dict[str, Any], transcript: Transcript) -> bool:
    """Check whether any tool call's arguments (or nested `params`) contain every
    expected key/value pair."""
    for tc in transcript.tool_calls:
        if _contains(tc.arguments, expected):
            return True
        params = tc.arguments.get("params") if isinstance(tc.arguments, dict) else None
        if isinstance(params, dict) and _contains(params, expected):
            return True
    return False


def _contains(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    for k, v in expected.items():
        if k not in actual:
            return False
        if isinstance(v, (dict, list)):
            # Serialise for loose comparison
            if json.dumps(actual[k], sort_keys=True) != json.dumps(v, sort_keys=True):
                return False
        else:
            if actual[k] != v:
                return False
    return True
