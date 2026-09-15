from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SCENARIO_IDS = (
    "initialize-undocumented-project",
    "trace-public-interface-change",
    "reject-code-only-local-refactor",
    "handle-structural-audit-failure",
    "protect-sensitive-content",
    "apply-configuration-driven-governance",
    "close-superseded-document-chain",
    "validate-markdown-anchor",
)


def _document(identifier: str, title: str, body: str = "Benchmark fixture.") -> str:
    return (
        "---\n"
        f"id: {identifier}\n"
        "type: guide\n"
        "status: active\n"
        f"title: {title}\n"
        "created: 2026-01-01\n"
        "updated: 2026-01-01\n"
        "---\n\n"
        f"# {title}\n\n{body}\n"
    )


def _write_project(root: Path, scenario_id: str) -> None:
    if scenario_id == "initialize-undocumented-project":
        return

    (root / "AGENTS.md").write_text(
        "# Benchmark project\n\n[Documentation](docs/README.md)\n",
        encoding="utf-8",
    )
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    documents = {
        "api.md": _document("BENCH-API", "API", "The public response contract."),
        "testing.md": _document("BENCH-TESTING", "Testing", "Verification notes."),
        "security.md": _document("BENCH-SECURITY", "Security", "Redacted handling guidance."),
        "repair.md": _document("BENCH-REPAIR", "Repair", "Structural repair notes."),
        "anchor.md": _document("BENCH-ANCHOR", "锚点 😀", "# 重复标题\n\n# 重复标题\n\n[Broken](missing.md#nope)"),
    }
    if scenario_id == "close-superseded-document-chain":
        documents["old.md"] = (
            "---\n"
            "id: BENCH-OLD\n"
            "type: guide\n"
            "status: superseded\n"
            "title: Old\n"
            "created: 2026-01-01\n"
            "updated: 2026-01-01\n"
            "---\n\n"
            "# Old\n\n[Successor](successor.md)\n"
        )
        documents["successor.md"] = (
            "---\n"
            "id: BENCH-NEW\n"
            "type: guide\n"
            "status: active\n"
            "title: Successor\n"
            "created: 2026-01-01\n"
            "updated: 2026-01-01\n"
            "supersedes: BENCH-OLD\n"
            "---\n\n"
            "# Successor\n\nReplacement guidance.\n"
        )
    selected_names = {
        "trace-public-interface-change": ("api.md", "testing.md"),
        "handle-structural-audit-failure": ("repair.md",),
        "protect-sensitive-content": ("security.md",),
        "validate-markdown-anchor": ("anchor.md",),
        "close-superseded-document-chain": ("old.md", "successor.md"),
    }.get(scenario_id, ())
    for name in selected_names:
        (docs / name).write_text(documents[name], encoding="utf-8")
    links = ["# Documentation", "", "[Back to entrypoint](../AGENTS.md)", ""]
    for name in selected_names:
        links.append(f"- [{name}]({name})")
    (docs / "README.md").write_text("\n".join(links) + "\n", encoding="utf-8")

    if scenario_id == "apply-configuration-driven-governance":
        (root / ".r-doc.yaml").write_text("docs_root: docs\n", encoding="utf-8")
    if scenario_id == "protect-sensitive-content":
        (root / ".env").write_text("TOKEN=redacted-placeholder\n", encoding="utf-8")
        (root / "secrets.md").write_text("# Sensitive fixture\n", encoding="utf-8")


def _skill_version(project_root: Path) -> str:
    return (project_root / "VERSION").read_text(encoding="utf-8-sig").strip()


def _prompt(
    template_path: Path,
    *,
    profile: str,
    run_id: str,
    condition: str,
    model: str,
    skill_version: str,
    script_root: Path,
) -> str:
    template = template_path.read_text(encoding="utf-8")
    values = {
        "profile": profile,
        "run_id": run_id,
        "condition": condition,
        "model": model,
        "skill_version": skill_version,
        "script_root": str(script_root.resolve()),
    }
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


def capture_run(
    *,
    project_root: Path,
    benchmarks_root: Path,
    profile: str,
    run_id: str,
    condition: str,
    model: str,
    timeout: int,
) -> Path:
    run_dir = benchmarks_root / profile / run_id
    if run_dir.exists():
        raise ValueError(f"benchmark run already exists: {run_dir}")
    template_path = project_root / "benchmarks" / "codex-benchmark-prompt.md"
    skill_version = _skill_version(project_root)
    with tempfile.TemporaryDirectory(prefix="rdoc-codex-benchmark-") as directory:
        workspace = Path(directory)
        for scenario_id in SCENARIO_IDS:
            scenario_root = workspace / "scenarios" / scenario_id
            scenario_root.mkdir(parents=True, exist_ok=True)
            _write_project(scenario_root, scenario_id)
        prompt = _prompt(
            template_path,
            profile=profile,
            run_id=run_id,
            condition=condition,
            model=model,
            skill_version=skill_version,
            script_root=project_root / "skills" / "r-doc" / "scripts",
        )
        final_response_path = workspace / "benchmark-final-response.md"
        command = [
            "codex",
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            "-s",
            "danger-full-access",
            "-m",
            model,
            "-o",
            str(final_response_path),
            prompt,
        ]
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        sanitized_events = completed.stdout.replace(str(workspace), "<fixture-root>")
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout)[-2000:]
            raise RuntimeError(f"Codex run failed with exit code {completed.returncode}: {detail}")
        evidence_path = workspace / "benchmark-evidence.json"
        trace_path = workspace / "benchmark-trace.jsonl"
        if not evidence_path.is_file() or not trace_path.is_file():
            missing = [str(path.name) for path in (evidence_path, trace_path) if not path.is_file()]
            raise RuntimeError("Codex run did not produce required capture files: " + ", ".join(missing))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        if not isinstance(evidence, dict):
            raise ValueError("benchmark-evidence.json must contain an object")
        trace_lines = trace_path.read_text(encoding="utf-8").splitlines()
        if not trace_lines:
            raise ValueError("benchmark-trace.jsonl must not be empty")

        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": 2,
            "profile": profile,
            "run_id": run_id,
            "condition": condition,
            "benchmark_kind": "skill-layer-ablation",
            "prompt_contract": "fixed-protocol",
            "activation_ground_truth": "case-contract",
            "grader_kind": "agent-self-review",
            "review_provenance": "agent-generated",
            "agent": "Codex",
            "model": model,
            "skill_version": skill_version,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": "codex-cli-0.132.0",
            "trace_path": "trace.jsonl",
        }
        (run_dir / "run.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shutil.copy2(evidence_path, run_dir / "evidence.json")
        shutil.copy2(trace_path, run_dir / "trace.jsonl")
        if final_response_path.is_file():
            shutil.copy2(final_response_path, run_dir / "final-response.md")
        (run_dir / "codex-events.jsonl").write_text(sanitized_events, encoding="utf-8")
    return run_dir


def main() -> int:
    project_root = Path(__file__).parents[1].resolve()
    parser = argparse.ArgumentParser(description="Capture one real Codex benchmark run for r-doc.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--condition", choices=("with-r-doc", "baseline-no-r-doc"), required=True)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--root", type=Path, default=project_root / "benchmarks")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        run_dir = capture_run(
            project_root=project_root,
            benchmarks_root=args.root.resolve(),
            profile=args.profile,
            run_id=args.run_id,
            condition=args.condition,
            model=args.model,
            timeout=args.timeout,
        )
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"capture failed: {error}", file=sys.stderr)
        return 1
    print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
