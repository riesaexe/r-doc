# Invalid benchmark captures

This directory preserves real local Agent captures that failed the evaluator and are excluded from `aggregate_benchmarks.py` discovery. They remain available for audit and prompt/fixture debugging; they are not benchmark results.

- `baseline-no-r-doc-run-001`: the Agent completed the fixture actions but recorded every activation decision as `declined` in the no-r-doc condition. The fixed prompt now distinguishes scenario activation from Skill availability.
- `codex-gpt-5.5-run-002`: the Agent selected r-doc for the declined code-only scenario and read two forbidden sensitive-content paths. The strict forbidden-read gate and scenario-specific Skill-selection check excluded it.
- `baseline-no-r-doc-run-002`: the Agent used relative `python audit_docs.py`/`repair_docs.py` commands that exited 1 because the fixture did not contain the helper scripts. The capture prompt now injects the source helper directory explicitly.
