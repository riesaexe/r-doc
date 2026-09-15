# Agent benchmark records

This directory stores empirical Agent runs for r-doc. It is deliberately separate from `skills/r-doc/evals/example-evidence.json`: the example proves that the evaluator accepts the schema, while this directory is only for evidence captured from real runs.

## Layout

```text
benchmarks/
├── README.md
├── summary.json
├── performance-baseline.json
├── codex-gpt-5.6/
│   └── run-001/
│       ├── run.json
│       ├── trace.jsonl
│       ├── evidence.json
│       └── result.json
└── baseline-no-r-doc/
    └── run-001/
        ├── run.json
        ├── trace.jsonl
        ├── evidence.json
        └── result.json
```

The repository currently contains no real Agent run. `summary.json` therefore stays `pending`; it must not be read as a benchmark score.

## Capturing a real run

Each `run.json` must contain:

```json
{
  "schema_version": 1,
  "profile": "codex-gpt-5.6",
  "run_id": "run-001",
  "condition": "with-r-doc",
  "agent": "Codex",
  "model": "gpt-5.6",
  "skill_version": "0.2.12",
  "captured_at": "2026-09-15T00:00:00Z",
  "source": "manual-real-agent-run",
  "trace_path": "trace.jsonl"
}
```

`condition` is either `with-r-doc` or `baseline-no-r-doc`. The baseline still records the case-contract version so results remain comparable; it does not imply that r-doc was loaded. `trace.jsonl` must be the actual captured interaction trace, not a generated placeholder. `evidence.json` must follow the versioned case contract and contain the real prompt, paths, commands, reports, and diffs. Never store secrets in a trace or evidence file.

## Validation and aggregation

After adding real runs, derive each result and the profile summary with:

```bash
python skills/r-doc/scripts/aggregate_benchmarks.py \
  --root benchmarks \
  --write-results
```

Use `--strict` only when every intended run and trace is present:

```bash
python skills/r-doc/scripts/aggregate_benchmarks.py \
  --root benchmarks \
  --write-results \
  --strict
```

The aggregator never trusts a hand-written `result.json`; it re-runs the evaluator from `evidence.json`. It requires the run manifest, trace file, matching Skill/case version, and all evaluator checks before including a run.

The reported metrics mean:

- `activation_accuracy`: percentage of scenarios whose activation decision matched the case.
- `audit_compliance`: percentage of scenarios whose deterministic verification checks passed.
- `unnecessary_reads`: unique files read beyond the scenario's required file set.
- `task_success`: percentage of scenarios with an overall passing result, including machine checks and human-review statuses.

Compare at least three runs per condition before drawing a conclusion. `summary.json` is a historical record, not a replacement for inspecting traces and individual results.

## Audit performance baseline

The separate performance harness measures deterministic audit time on generated 100-, 1000-, and 5000-document fixtures:

```bash
python skills/r-doc/scripts/benchmark_audit.py \
  --sizes 100,1000,5000 \
  --iterations 3 \
  --warmup 0 \
  --output benchmarks/performance-baseline.json
```

The stored wall-clock values are local trend data with Python and platform metadata. They are not a CI pass/fail threshold; rerun them on representative machines before making scale claims.

返回：[开发文档索引](../docs/development/README.md) · [Agent 评测契约](../skills/r-doc/references/agent-evaluation.md)
