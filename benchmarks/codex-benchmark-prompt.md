# Codex benchmark capture prompt

## 中文说明

这是为可复现实验保留的固定英文 prompt。它属于 Conformance Benchmark / `skill-layer-ablation`，有意公开 scenario activation、读取策略、helper 命令和事件契约，因此不能用于声称 natural activation 或独立 task effectiveness。英文正文必须保持稳定，修改它会改变 benchmark protocol；中文读者可阅读本说明和 [benchmark 总说明](README.md) 获取方法学解释。

You are a benchmark participant. Work only in the temporary project root supplied to this run. The run metadata is:

- profile: {profile}
- run_id: {run_id}
- condition: {condition}
- model: {model}
- r-doc skill version: {skill_version}
- source helper scripts: {script_root}

This is a fixed prompt. It defines a Conformance Benchmark and skill-layer ablation, not a natural activation or independent effectiveness benchmark. Do not change the scenario order or the evidence field names. Do not read or write files outside the scenario directories and the two capture outputs requested below, except for invoking the explicitly named r-doc scripts from the source repository.

Use the provided source helper directory for deterministic checks in both conditions. For example, run `python "{script_root}/audit_docs.py" --root "<scenario-directory>"` and `python "{script_root}/repair_docs.py" --root "<scenario-directory>"`; record the actual command and exit code. Do not guess a relative script name such as `python audit_docs.py` inside a fixture directory.

For the `with-r-doc` condition, use the installed `r-doc` skill for documentation-governance decisions. For the `baseline-no-r-doc` condition, do not load, quote, or use the r-doc skill; perform the same tasks with your normal reasoning and the explicitly requested helper commands. In both conditions, record what actually happened. Never invent a file read, command, write, report, diff, review, or activation decision after the fact. The review events are agent-generated review evidence, not independent human grading.

The condition changes skill availability, not the scenario's activation answer. In both conditions, record `activation: "activated"` for the seven governance scenarios and `activation: "declined"` only for `reject-code-only-local-refactor`. In `with-r-doc`, set `skill_selected` to `"r-doc"` only for activated scenarios and to `"none"` for the declined code-only scenario. In the baseline condition, `skill_selected` is `"none"` for every scenario because r-doc is unavailable; this does not turn the governance scenarios into declined tasks.

Before processing scenarios, create `benchmark-trace.jsonl`. Every line must be one JSON object with `schema_version: 2` and a contiguous zero-based `sequence`. Start with one `trace_start` containing the six run metadata fields above and finish with `trace_end`. For each scenario, emit exactly one `scenario_start` and `scenario_end`, plus trace events for the actual prompt, activation decision, selected skill, paths checked, files read, commands with exit codes, files written, governance report, final response, diff snapshot, and each review dimension. Use only the event fields defined by the r-doc benchmark trace schema.

Use this exact trace field contract: every event has only `schema_version`, `sequence`, and `event` plus the fields listed here. The first line must use the exact key `skill_version` (not `r_doc_skill_version` or any other spelling), for example `{"schema_version":2,"sequence":0,"event":"trace_start","run_id":"{run_id}","profile":"{profile}","condition":"{condition}","agent":"Codex","model":"{model}","skill_version":"{skill_version}"}`. `trace_start` adds `run_id`, `profile`, `condition`, `agent`, `model`, and `skill_version`; `scenario_start` and `scenario_end` add `scenario_id`; `prompt`, `governance_report`, `final_response`, and `diff_snapshot` add `scenario_id` and `text`; `activation_decision` adds `scenario_id` and `decision`; `skill_selected` adds `scenario_id` and `skill`; `path_checked`, `file_read`, and `file_written` add `scenario_id` and `path`; `command` adds `scenario_id`, `exit_code`, and optionally `name` and `command`; `review` adds `scenario_id`, `dimension`, `status`, and `basis`. Do not add `note`, timestamps, tool names, output blobs, or any other fields. Use `decision` values `activated` or `declined`, review statuses `pass`, `partial`, or `fail`, and the dimensions `context_economy`, `preservation`, and `conflict_handling`.

At the end, write `benchmark-evidence.json` with exactly these top-level keys: `schema_version: 3`, `skill_version: "{skill_version}"`, `agent: "Codex"`, `condition: "{condition}"`, and `scenarios`. Do not rename `skill_version`. Include exactly eight scenario objects. Each object must contain `id`, `activation`, `skill_selected`, `prompt`, `paths_checked`, `files_read`, `files_written`, `commands`, `governance_report`, `final_response`, `final_diff`, and a `review` object with `context_economy`, `preservation`, and `conflict_handling`. The evidence must be copied from the trace and from actions actually performed, not reconstructed from the case definitions.

Process these fixed scenarios in order. All paths are relative to the scenario directory.

1. `initialize-undocumented-project`: inspect whether `AGENTS.md` and `docs/` exist, establish the documentation entrypoint and index without deleting existing files, and run `audit_docs.py` successfully.
2. `trace-public-interface-change`: inspect `AGENTS.md` and `docs/README.md`, then the relevant API/testing context, account for a public API response change, and run `audit_docs.py` successfully.
3. `reject-code-only-local-refactor`: treat a private function rename with no public, configuration, architecture, or project-rule impact as code-only; do not activate r-doc and do not read or write documentation files.
4. `handle-structural-audit-failure`: inspect the entrypoint and index, use `repair_docs.py` followed by `audit_docs.py`, preserve facts, and report the repair boundary and remaining semantic decisions.
5. `protect-sensitive-content`: inspect only the entrypoint and index before handling the sensitive-content fixture; do not open or read `.env` or `secrets.md`, do not copy the redacted secret-like value, run `audit_docs.py` successfully, and record the safety decision.
6. `apply-configuration-driven-governance`: inspect the entrypoint, index, and `.r-doc.yaml`, respect its configured root/exclusions/lifecycle settings, and run `audit_docs.py` successfully.
7. `close-superseded-document-chain`: inspect the entrypoint, index, and the superseded/successor documents, verify the declared successor link, and run `audit_docs.py` successfully.
8. `validate-markdown-anchor`: inspect the entrypoint, index, and anchor fixture, report the exact CJK/emoji/duplicate-heading fragment issue, and run `audit_docs.py` successfully.

The runner will retain the normalized trace, evidence, final response, and a sanitized copy of the Codex JSONL event stream. If a required output cannot be produced, stop and explain the missing artifact in the final response instead of fabricating it.
