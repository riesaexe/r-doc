from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from rdoc.config import load_project_config, relative
from rdoc.notes import apply_archive, plan_archive


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview or apply safe decision-note lifecycle operations.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    archive = subparsers.add_parser("archive", help="move one decision note to the archived lifecycle")
    archive.add_argument("note", type=Path, help="project-relative path to the decision note")
    archive.add_argument("--root", type=Path, default=Path.cwd())
    archive.add_argument("--apply", action="store_true", help="apply the planned archive move")
    archive.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    config, problems = load_project_config(root)
    if problems:
        print("r-doc decision notes: FAIL")
        print("; ".join(problem.message for problem in problems))
        return 1
    try:
        if args.command != "archive":
            raise ValueError(f"unsupported decision-note command: {args.command}")
        plan = plan_archive(root, config, args.note)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        print(f"r-doc decision notes: FAIL\n{error}")
        return 1

    payload = {
        "command": args.command,
        "apply": args.apply,
        "id": plan.identifier,
        "source": relative(root, plan.source),
        "destination": relative(root, plan.destination),
        "changed": False,
    }
    if not args.apply:
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("r-doc decision notes: PLAN")
            print(f"ARCHIVE {payload['source']} -> {payload['destination']} ({plan.identifier})")
            print("No files changed. Re-run with --apply after confirmation.")
        return 0

    try:
        apply_archive(plan)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        print(f"r-doc decision notes: FAIL\n{error}")
        return 1
    payload["changed"] = True
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Archived {payload['source']} to {payload['destination']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
