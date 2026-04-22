# Flowcase agent evaluation

CLI harness that runs a curated set of gold questions against the
deployed Flowcase web backend and scores each response with an
LLM-as-judge (GPT-5.4 on Azure Foundry).

## Installation

```powershell
# From any venv that already has httpx + openai + pydantic (e.g. the
# web backend venv), add pyyaml:
pip install pyyaml

# Or install everything fresh:
pip install -r tests/eval/requirements.txt
```

## Running

```powershell
$env:AZURE_OPENAI_API_KEY = "<kateecosystem key>"
python tests/eval/run_eval.py `
  --target https://ca-flowcasemcp-dev-web.<hash>.norwayeast.azurecontainerapps.io `
  --email marius.hernes@atea.no `
  --password <your password> `
  --judge-model gpt-5.4
```

Flags (with env-var fallbacks):

| Flag | Env var | Default |
|---|---|---|
| `--target` | `EVAL_TARGET` | _(required)_ |
| `--email` | `EVAL_EMAIL` | _(required)_ |
| `--password` | `EVAL_PASSWORD` | _(required)_ |
| `--gold` | — | `tests/eval/gold.yaml` |
| `--output-dir` | — | `tests/eval/results/` |
| `--judge-model` | `EVAL_JUDGE_MODEL` | `gpt-5.4` |
| `--azure-openai-endpoint` | `AZURE_OPENAI_ENDPOINT` | kateecosystem-resource |
| `--azure-openai-api-key` | `AZURE_OPENAI_API_KEY` | _(required)_ |
| `--only` | — | _(run all)_ |

Example for a single question:

```powershell
python tests/eval/run_eval.py --only k01 r01 ...
```

## Output

Each run writes two files to `tests/eval/results/`:

- `YYYY-MM-DD-HHMMSS.md` — human-readable summary with aggregate scores,
  per-item tool calls, machine-check results, and judge reasoning.
- `YYYY-MM-DD-HHMMSS.json` — structured dump, suitable for diffing runs
  or feeding into future dashboards.

## Editing the gold set

`tests/eval/gold.yaml` is the single source of truth. Each item supports:

- `must_call_tools` / `must_call_tools_any` — tool-name guardrails
- `must_include_args` — key/value match against any tool's arguments
- `must_mention_any` / `must_mention_all` / `must_not_mention` — substring
  assertions on the final assistant text
- `qualitative` — free-form criteria graded by the judge on a 1–5
  rubric (correctness, completeness, honesty, presentation).

Keep questions realistic. Prefer 5–10 concrete criteria over vague
one-liners — the judge is more reliable the more specific the prompt.
