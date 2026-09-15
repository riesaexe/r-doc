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
  "skill_version": "0.2.14",
  "captured_at": "2026-09-15T00:00:00Z",
  "source": "manual-real-agent-run",
  "trace_path": "trace.jsonl"
}
```

`condition` is either `with-r-doc` or `baseline-no-r-doc`. The baseline still records the case-contract version so results remain comparable; it does not imply that r-doc was loaded. `trace.jsonl` must be the actual captured interaction trace, not a generated placeholder. `evidence.json` must follow the versioned case contract and contain the real prompt, paths, commands, reports, and diffs. Never store secrets in a trace or evidence file.

### Trace JSONL contract

The trace is a normalized JSONL record, not an arbitrary marker. Every line is a JSON object with `schema_version: 1` and a contiguous zero-based `sequence`. The first line is a `trace_start` event whose `run_id`, `profile`, `condition`, `agent`, `model`, and `skill_version` must match `run.json`; the last line is `trace_end`.

Between those boundary events, each case is represented exactly once by `scenario_start` and `scenario_end`. Action events must stay inside their active scenario and use one of these forms:

```json
{"schema_version":1,"sequence":2,"event":"path_checked","scenario_id":"trace-public-interface-change","path":"docs/README.md"}
{"schema_version":1,"sequence":3,"event":"file_read","scenario_id":"trace-public-interface-change","path":"docs/README.md"}
{"schema_version":1,"sequence":4,"event":"command","scenario_id":"trace-public-interface-change","name":"audit_docs.py","exit_code":0}
{"schema_version":1,"sequence":5,"event":"file_written","scenario_id":"trace-public-interface-change","path":"docs/api.md"}
```

The aggregator derives `paths_checked`, `files_read`, `commands`, and `files_written` from these events. It rejects malformed JSONL, missing or unknown scenarios, broken sequencing, manifest/header mismatches, secret-like trace values, and any difference between derived evidence and `evidence.json`. File lists are compared as sets; command labels and exit codes are compared in order. The derived per-scenario values are retained as `runs[*].trace_derived` in `summary.json` for audit inspection.

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

The aggregator never trusts a hand-written `result.json`; it re-runs the evaluator from `evidence.json` and cross-validates the structured trace. It requires the run manifest, trace file, matching Skill/case version, and all evaluator checks before including a run.

The reported metrics mean:

- `activation_accuracy`: percentage of scenarios whose activation decision matched the case.
- `audit_compliance`: percentage of scenarios whose deterministic verification checks passed.
- `unnecessary_reads`: unique files read outside the scenario's `allowed_files_read` set.
- `forbidden_reads`: unique files read inside the scenario's `forbidden_files_read` set.
- `required_reads_missing`: required files that were not recorded as read.
- `task_success`: percentage of scenarios with an overall passing result, including machine checks and human-review statuses.

`required_files_read` must be a subset of `allowed_files_read`, and the allowed and forbidden sets may not overlap. This prevents a legitimate read such as `docs/api.md` or `docs/testing.md` from being mislabeled as unnecessary merely because it was not a minimum required read.

`summary.json` keeps profile metrics nested under `conditions` and adds `paired_comparisons`. A paired comparison matches the same `agent`, `model`, and `run_id` across both conditions, then reports per-condition averages, with-r-doc minus baseline deltas, per-metric mean/median/standard deviation, and whether at least three matched pairs are available. Only runs whose manifest and trace both pass validation enter these aggregates; invalid runs remain visible in `runs` with their errors. Compare at least three pairs before drawing a conclusion; `summary.json` is a historical record, not a replacement for inspecting traces and individual results.

## Audit performance baseline

The separate performance harness measures deterministic audit time on generated 100-, 1000-, and 5000-document fixtures:

```bash
python skills/r-doc/scripts/benchmark_audit.py \
  --sizes 100,1000,5000 \
  --iterations 10 \
  --warmup 0 \
  --output benchmarks/performance-baseline.json
```

The stored wall-clock values are local trend data with Python and platform metadata. The default is now ten measured iterations; the report includes a linearly interpolated empirical p95, `max_seconds`, and a low-sample flag. With fewer than ten samples the p95 remains a noisy estimate, so the maximum is retained for transparent inspection. These values are not a CI pass/fail threshold; rerun them on representative machines before making scale claims. The earlier three-sample 100→1000 snapshot grew about 12.8x, while the refreshed ten-sample median is about 9.4x and its p95 about 10.1x. The spread reinforces that scale behavior needs repeated, representative measurements; any mild super-linear interpretation remains an observation, not a complexity guarantee.

返回：[开发文档索引](../docs/development/README.md) · [Agent 评测契约](../skills/r-doc/references/agent-evaluation.md)
