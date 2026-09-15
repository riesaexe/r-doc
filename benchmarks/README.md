# Agent benchmark records

This directory stores empirical Agent runs for r-doc. It is deliberately separate from `skills/r-doc/evals/example-evidence.json`: the example proves that the evaluator accepts the schema, while this directory is only for evidence captured from real runs.

## Layout

```text
benchmarks/
├── README.md
├── summary.json
├── performance-baseline.json
├── codex-gpt-5.5/
│   └── run-001/
│       ├── run.json
│       ├── trace.jsonl
│       ├── evidence.json
│       ├── result.json
│       ├── final-response.md
│       └── codex-events.jsonl
└── baseline-no-r-doc/
    └── run-001/
        ├── run.json
        ├── trace.jsonl
        ├── evidence.json
        ├── result.json
        ├── final-response.md
        └── codex-events.jsonl
```

If no valid real Agent run has been captured, `summary.json` stays `pending`; it must not be read as a benchmark score.

## Capturing a real run

Each `run.json` must contain:

```json
{
  "schema_version": 1,
  "profile": "codex-gpt-5.5",
  "run_id": "run-001",
  "condition": "with-r-doc",
  "agent": "Codex",
  "model": "gpt-5.5",
  "skill_version": "0.2.15",
  "captured_at": "2026-09-15T00:00:00Z",
  "source": "manual-real-agent-run",
  "trace_path": "trace.jsonl"
}
```

`condition` is either `with-r-doc` or `baseline-no-r-doc`. The baseline still records the case-contract version so results remain comparable; it does not imply that r-doc was loaded. `trace.jsonl` must be the actual captured interaction trace, not a generated placeholder. `evidence.json` must follow the versioned case contract and contain the real prompt, paths, commands, reports, and diffs. Never store secrets in a trace or evidence file.

### Trace JSONL contract

The trace is a normalized JSONL record, not an arbitrary marker. Every line is a JSON object with `schema_version: 2` and a contiguous zero-based `sequence`. The first line is a `trace_start` event whose `run_id`, `profile`, `condition`, `agent`, `model`, and `skill_version` must match `run.json`; the last line is `trace_end`.

Between those boundary events, each case is represented exactly once by `scenario_start` and `scenario_end`. Each scenario must also contain exactly one `prompt`, `activation_decision`, `skill_selected`, `governance_report`, `final_response`, and `diff_snapshot`, plus one `review` event for every review dimension. Action events must stay inside their active scenario.

```json
{"schema_version":2,"sequence":2,"event":"prompt","scenario_id":"trace-public-interface-change","text":"..."}
{"schema_version":2,"sequence":3,"event":"activation_decision","scenario_id":"trace-public-interface-change","decision":"activated"}
{"schema_version":2,"sequence":4,"event":"skill_selected","scenario_id":"trace-public-interface-change","skill":"r-doc"}
{"schema_version":2,"sequence":5,"event":"path_checked","scenario_id":"trace-public-interface-change","path":"docs/README.md"}
{"schema_version":2,"sequence":6,"event":"file_read","scenario_id":"trace-public-interface-change","path":"docs/README.md"}
{"schema_version":2,"sequence":7,"event":"command","scenario_id":"trace-public-interface-change","name":"audit_docs.py","exit_code":0}
{"schema_version":2,"sequence":8,"event":"file_written","scenario_id":"trace-public-interface-change","path":"docs/api.md"}
{"schema_version":2,"sequence":9,"event":"governance_report","scenario_id":"trace-public-interface-change","text":"..."}
{"schema_version":2,"sequence":10,"event":"final_response","scenario_id":"trace-public-interface-change","text":"..."}
{"schema_version":2,"sequence":11,"event":"diff_snapshot","scenario_id":"trace-public-interface-change","text":"..."}
{"schema_version":2,"sequence":12,"event":"review","scenario_id":"trace-public-interface-change","dimension":"context_economy","status":"pass","basis":"..."}
```

The event field set is closed by event type, so arbitrary fields such as a trace `note` are rejected. The aggregator derives activation, skill selection, prompt, reports, final response, diff, reviews, paths, reads, commands, and writes from these events and cross-checks them against `evidence.json`. It rejects malformed JSONL, missing or unknown scenarios, broken sequencing, manifest/header mismatches, secret-like trace values, and any difference between derived evidence and `evidence.json`. The derived per-scenario values are retained as `runs[*].trace_derived` in `summary.json` for audit inspection. This remains a structural consistency check rather than cryptographic provenance; `codex-events.jsonl` preserves a sanitized raw CLI capture for manual review.

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

Forbidden reads are always reported in the per-scenario metrics. Ordinary evaluation lowers a passing `context_economy` review to `partial`; `evaluate_agent.py --strict` and the aggregator's strict evaluation fail the run, so a run that reads `.env` or `secrets.md` cannot still count as a clean benchmark result.

`summary.json` keeps profile metrics nested under `conditions` and adds `paired_comparisons`. A paired comparison matches the same `agent`, `model`, and `run_id` across both conditions, then reports per-condition averages, with-r-doc minus baseline deltas, per-metric mean/median/standard deviation, and 95% Student-t intervals. `trend_readiness` requires three pairs, `statistical_readiness` requires five, and `strong_evidence_readiness` requires ten. Only runs whose manifest, strict evaluator, and trace gates pass validation enter these aggregates; invalid runs remain visible in `runs` with their errors.

Capture a real Codex run with `python benchmarks/capture_codex.py --profile codex-gpt-5.5 --run-id run-001 --condition with-r-doc --model gpt-5.5`, then capture the matched baseline under the `baseline-no-r-doc` profile with the same run ID: `python benchmarks/capture_codex.py --profile baseline-no-r-doc --run-id run-001 --condition baseline-no-r-doc --model gpt-5.5`. The capture tool stores agent-produced evidence and trace plus a sanitized raw CLI event stream; it does not synthesize evidence from the case definitions.

Failed real captures are preserved under `benchmarks/invalid-captures/` for audit and prompt debugging, but their directories are intentionally outside the official `*/run-*/evidence.json` discovery pattern and never enter profile or paired statistics.

## Audit performance baseline

The separate performance harness measures deterministic audit time on generated 100-, 1000-, and 5000-document fixtures:

```bash
python skills/r-doc/scripts/benchmark_audit.py \
  --sizes 100,1000,5000 \
  --iterations 10 \
  --warmup 0 \
  --output benchmarks/performance-baseline.json
```

The stored wall-clock values are local trend data with Python and platform metadata. The default is now ten measured iterations; the report includes a linearly interpolated empirical p95, `max_seconds`, and a low-sample flag. With fewer than ten samples the p95 remains a noisy estimate, so the maximum is retained for transparent inspection. These values are not a CI pass/fail threshold; rerun them on representative machines before making scale claims. The refreshed local snapshot has 100→1000 median growth of about 12.2x and p95 growth of about 14.5x; 1000→5000 median growth is about 4.1x. The spread reinforces that scale behavior needs repeated, representative measurements; any mild super-linear interpretation remains an observation, not a complexity guarantee.

返回：[开发文档索引](../docs/development/README.md) · [Agent 评测契约](../skills/r-doc/references/agent-evaluation.md)
