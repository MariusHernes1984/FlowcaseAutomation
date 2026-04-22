"""Render a RunSummary as Markdown for humans + JSON for machines."""

from __future__ import annotations

from pathlib import Path

from tests.eval.schema import ItemResult, RunSummary


def write_outputs(summary: RunSummary, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = summary.started_at.strftime("%Y-%m-%d-%H%M%S")
    json_path = output_dir / f"{stamp}.json"
    md_path = output_dir / f"{stamp}.md"
    json_path.write_text(
        summary.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )
    md_path.write_text(_render_markdown(summary), encoding="utf-8")
    return md_path, json_path


def _render_markdown(summary: RunSummary) -> str:
    lines: list[str] = []
    lines.append(f"# Flowcase eval — {summary.started_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append(f"- **Target:** `{summary.target}`")
    lines.append(f"- **Judge model:** `{summary.judge_model}`")
    lines.append(f"- **Items:** {summary.num_items}")
    if summary.finished_at:
        dt = (summary.finished_at - summary.started_at).total_seconds()
        lines.append(f"- **Elapsed:** {dt:.1f}s")
    agg = summary.aggregate
    if agg:
        lines.append("")
        lines.append("## Aggregated scores")
        lines.append("")
        lines.append("| Metric | Avg (1-5) |")
        lines.append("|---|---|")
        for k in ("correctness", "completeness", "honesty", "presentation", "overall"):
            if k in agg:
                lines.append(f"| {k.capitalize()} | **{agg[k]}** |")

    lines.append("")
    lines.append("## Per-item results")
    lines.append("")
    lines.append("| ID | Agent | Overall | C | K | H | P | Machine | Seconds |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for it in summary.items:
        j = it.judgement
        overall = f"{j.overall}" if j else "—"
        c = f"{j.scores.correctness}" if j else "—"
        k = f"{j.scores.completeness}" if j else "—"
        h = f"{j.scores.honesty}" if j else "—"
        p = f"{j.scores.presentation}" if j else "—"
        m = f"{it.machine.passed}/{it.machine.total}"
        lines.append(
            f"| {it.gold.id} | {it.gold.agent} | **{overall}** | {c} | {k} | {h} | {p} | {m} | {it.transcript.elapsed_seconds} |"
        )

    for it in summary.items:
        lines.append("")
        lines.append("---")
        lines.append("")
        _render_item(it, lines)

    return "\n".join(lines)


def _render_item(it: ItemResult, out: list[str]) -> None:
    g = it.gold
    j = it.judgement
    out.append(f"### {g.id} — {g.agent}")
    out.append("")
    out.append(f"**Question:** {g.question}")
    out.append("")

    out.append("**Tool calls:**")
    if it.transcript.tool_calls:
        for tc in it.transcript.tool_calls:
            out.append(f"- `{tc.name}` — `{_one_line(tc.arguments)}`")
    else:
        out.append("- _(none)_")
    out.append("")

    out.append("**Final text:**")
    out.append("")
    out.append("```")
    txt = it.transcript.final_text.strip() or "(empty)"
    out.append(txt if len(txt) < 3000 else txt[:3000] + "\n…(truncated)")
    out.append("```")

    if it.transcript.errors:
        out.append("")
        out.append(f"**Stream errors:** {it.transcript.errors}")

    out.append("")
    out.append("**Machine checks:**")
    for c in it.machine.checks:
        marker = "✅" if c.status == "pass" else "❌" if c.status == "fail" else "⚪"
        out.append(f"- {marker} `{c.name}` — {c.detail}")

    if j:
        out.append("")
        out.append(
            f"**Judge ({j.judge_model}):** overall **{j.overall}/5** · "
            f"C{j.scores.correctness} K{j.scores.completeness} "
            f"H{j.scores.honesty} P{j.scores.presentation}"
        )
        if j.notes:
            out.append("")
            out.append(f"> {j.notes}")
        if j.criteria_results:
            out.append("")
            out.append("**Criteria:**")
            for cr in j.criteria_results:
                m = "✅" if cr.met else "❌"
                reason = f" — {cr.reason}" if cr.reason else ""
                out.append(f"- {m} {cr.criterion}{reason}")


def _one_line(obj: object) -> str:
    import json as _json

    s = _json.dumps(obj, ensure_ascii=False)
    return s if len(s) < 200 else s[:200] + "…"
