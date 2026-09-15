# Invalid benchmark captures

This directory preserves real local Agent captures that failed the evaluator and are excluded from `aggregate_benchmarks.py` discovery. They remain available for audit and prompt/fixture debugging; they are not benchmark results.

- `baseline-no-r-doc-run-001`: the Agent completed the fixture actions but recorded every activation decision as `declined` in the no-r-doc condition. The fixed prompt now distinguishes scenario activation from Skill availability.
- `codex-gpt-5.5-run-002`: the Agent selected r-doc for the declined code-only scenario and read two forbidden sensitive-content paths. The strict forbidden-read gate and scenario-specific Skill-selection check excluded it.
- `baseline-no-r-doc-run-002`: the Agent used relative `python audit_docs.py`/`repair_docs.py` commands that exited 1 because the fixture did not contain the helper scripts. The capture prompt now injects the source helper directory explicitly.

## 中文说明

本目录保留真实本机 Agent capture 中未通过评测器的记录，不参与 `aggregate_benchmarks.py` 的正式发现和统计。它们只用于审计、prompt 和 fixture 调试，不能当作 benchmark 结果：

- `baseline-no-r-doc-run-001`：Agent 在 no-r-doc 条件下把所有场景 activation 都记为 `declined`；固定 prompt 后来明确区分 scenario activation 和 Skill availability。
- `codex-gpt-5.5-run-002`：Agent 在 code-only 场景错误选择 r-doc，并读取两个 forbidden sensitive-content 路径；strict forbidden-read gate 和场景 Skill-selection 检查将其排除。
- `baseline-no-r-doc-run-002`：Agent 使用相对路径调用 fixture 中不存在的 `audit_docs.py`/`repair_docs.py`，命令退出 1；capture prompt 后来显式注入源 helper 目录。
