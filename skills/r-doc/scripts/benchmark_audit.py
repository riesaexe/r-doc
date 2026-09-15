from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import audit_docs


def build_fixture(root: Path, document_count: int) -> None:
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# Benchmark project\n\n[Documentation](docs/README.md)\n", encoding="utf-8")
    links = ["# Benchmark documentation", "\n[Back to entrypoint](../AGENTS.md)", ""]
    for index in range(1, document_count + 1):
        name = f"document-{index:05d}.md"
        title = f"Benchmark document {index:05d}"
        links.append(f"- [{title}]({name})")
        (docs / name).write_text(
            "---\n"
            f"id: BENCH-{index:05d}\n"
            "type: guide\n"
            "status: active\n"
            f"title: {title}\n"
            "created: 2026-01-01\n"
            "updated: 2026-01-01\n"
            "---\n\n"
            f"# {title}\n\nSynthetic performance fixture.\n",
            encoding="utf-8",
        )
    (docs / "README.md").write_text("\n".join(links) + "\n", encoding="utf-8")


def measure_size(document_count: int, iterations: int = 3, warmup: int = 1) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="rdoc-audit-benchmark-") as directory:
        root = Path(directory)
        build_fixture(root, document_count)
        for _ in range(warmup):
            audit_docs.audit(root)
        durations: list[float] = []
        findings_count = 0
        for _ in range(iterations):
            started = time.perf_counter()
            findings = audit_docs.audit(root)
            durations.append(time.perf_counter() - started)
            findings_count = len(findings)
        ordered = sorted(durations)
        p95_index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * 0.95) - 1))
        return {
            "document_count": document_count,
            "iterations": iterations,
            "warmup": warmup,
            "durations_seconds": [round(value, 6) for value in durations],
            "median_seconds": round(statistics.median(durations), 6),
            "p95_seconds": round(ordered[p95_index], 6),
            "findings": findings_count,
        }


def _version(project_root: Path) -> str:
    version_file = project_root / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8-sig").strip()
    return "unknown"


def main() -> int:
    project_root = Path(__file__).parents[3]
    parser = argparse.ArgumentParser(description="Measure r-doc audit time on generated Markdown fixtures.")
    parser.add_argument("--sizes", default="100,1000,5000", help="comma-separated document counts")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--output", type=Path, help="write the benchmark JSON to this path")
    args = parser.parse_args()
    try:
        sizes = [int(item.strip()) for item in args.sizes.split(",") if item.strip()]
    except ValueError as error:
        parser.error(f"invalid --sizes: {error}")
    if not sizes or any(size <= 0 for size in sizes):
        parser.error("--sizes must contain positive integers")
    if args.iterations <= 0 or args.warmup < 0:
        parser.error("--iterations must be positive and --warmup cannot be negative")

    result = {
        "schema_version": 1,
        "tool": "r-doc audit",
        "skill_version": _version(project_root),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "cases": [measure_size(size, args.iterations, args.warmup) for size in sizes],
        "notes": "Wall-clock measurements are a local baseline, not a CI pass/fail threshold.",
    }
    output = args.output
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
