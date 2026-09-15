# Naturalistic Effectiveness Benchmark

This benchmark is the second layer of the r-doc evaluation model. It measures whether an agent discovers, activates, and applies r-doc appropriately on a realistic user task. It is intentionally separate from the checked-in `benchmarks/<profile>/run-*/` records.

## What it measures

The naturalistic condition gives the agent only a user task, a fixed fixture, and the normal tool environment:

> We changed the API response field from `user_name` to `display_name`. Synchronize the project so the implementation, API documentation, and tests agree.

The prompt does not disclose an activation answer, required or allowed reads, forbidden paths, command names, command order, or r-doc evidence fields. The matched conditions use the same task, fixture, model, and prompt:

- `with-r-doc`: r-doc is installed and discoverable;
- `baseline-no-r-doc`: r-doc is unavailable, while the same deterministic project tools remain available when the fixture provides them.

This is an ablation of the Skill layer, not a comparison between r-doc tooling and no tooling. The condition and tool availability must be recorded in `run.json`, not smuggled into the user prompt.

## Artifact contract

Store a naturalistic run outside the conformance glob, for example:

```text
benchmarks/naturalistic-runs/
├── codex-gpt-5.5/
│   └── run-001/
│       ├── run.json
│       ├── trace.jsonl
│       ├── final-state.json
│       └── final-response.md
└── baseline-no-r-doc/
    └── run-001/
        ├── run.json
        ├── trace.jsonl
        ├── final-state.json
        └── final-response.md
```

`final-state.json` is an external snapshot of the relevant final files. `trace.jsonl` is a normalized action trace with contiguous `sequence` values and events such as `prompt`, `file_read`, `file_written`, and `command`. The agent must not author its own score, review, or evidence file. Keep raw CLI capture beside the normalized trace when available.

The manifest must identify the layer and grader:

```json
{
  "schema_version": 1,
  "benchmark_kind": "naturalistic-effectiveness",
  "prompt_contract": "naturalistic-user-task",
  "activation_ground_truth": "independent-task-spec",
  "grader_kind": "independent-grader",
  "review_provenance": "independent-grader"
}
```

## Independent grading

Grade a run with the task specification and final-state snapshot:

```bash
python benchmarks/naturalistic/grader.py \
  --task benchmarks/naturalistic/tasks/api-response-field-rename.json \
  --run-dir benchmarks/naturalistic-runs/codex-gpt-5.5/run-001 \
  --json
```

The grader checks the final repository state and trace safety independently. It does not read `evidence.json`, agent-generated review dimensions, or self-reported task scores. A forbidden read or a failed final-state assertion fails the run. The grader output is a measurement artifact, not an instruction to the agent.

## Current status

This repository currently has the conformance/skill-layer-ablation data only. No naturalistic result is claimed until both matched conditions have real captured traces, final-state snapshots, and independent grader output. Do not copy the conformance summary into this directory or treat its `activation_accuracy` as natural activation accuracy.

返回：[benchmark 总说明](../README.md) · [开发文档](../../docs/development/benchmarks.md)

## 中文说明

这是 r-doc 评测模型的第二层：**Naturalistic Effectiveness Benchmark（自然任务效果 benchmark）**。它只向 Agent 提供真实用户任务、固定 fixture 和正常工具环境，不给 activation 答案、required/allowed/forbidden reads、命令顺序或“必须使用 r-doc”的提示。

匹配条件使用同一个 task、fixture、prompt 和 model：`with-r-doc` 表示 r-doc 已安装且可发现，`baseline-no-r-doc` 表示 Skill 不可用，但条件差异必须写入 `run.json`，不能泄露到用户 prompt。该设计测量 discovery、activation、context selection、governance quality 和 task outcome，是 Skill-layer ablation，不是“有工具”对比“无工具”。

每次运行保存 `run.json`、规范化 `trace.jsonl`、外部生成的 `final-state.json` 和 `final-response.md`。独立 grader 不读取 Agent 自评、`evidence.json` 或自报分数，而是检查最终文件断言、trace 完整性和 forbidden reads；最终状态失败或命中 forbidden read 都会失败。当前仓库仍没有可宣称的真实 naturalistic 结果。

返回：[benchmark 总说明](../README.md) · [开发文档](../../docs/development/benchmarks.md)
