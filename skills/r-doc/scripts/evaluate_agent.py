from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rdoc.security import SECRET_PATTERNS, is_safe_example


SCORE_VALUES = {"pass": 1.0, "partial": 0.5, "fail": 0.0}


def load_json(path: Path) -> dict[str, Any]:
    value = json.load(sys.stdin) if str(path) == "-" else json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def load_cases(path: Path) -> dict[str, Any]:
    cases = load_json(path)
    if (
        cases.get("schema_version") != 1
        or not isinstance(cases.get("skill_version"), str)
        or not cases["skill_version"].strip()
        or not isinstance(cases.get("dimensions"), list)
        or not isinstance(cases.get("scenarios"), list)
    ):
        raise ValueError(f"unsupported eval case schema: {path}")
    return cases


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list_of_strings(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _command_texts(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            result.extend(str(item.get(key, "")) for key in ("name", "command"))
    return result


def _evidence_contains_secret(evidence: dict[str, Any]) -> bool:
    serialized = json.dumps(evidence, ensure_ascii=False)
    for pattern, code in SECRET_PATTERNS:
        for match in pattern.finditer(serialized):
            if not is_safe_example(code, match.group(0)):
                return True
    return False


def evaluate(cases: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    dimensions = [item for item in cases["dimensions"] if isinstance(item, str)]
    errors: list[str] = []
    expected_skill_version = cases.get("skill_version")
    if not _non_empty_text(expected_skill_version):
        errors.append("eval cases skill_version is required")
    elif evidence.get("skill_version") != expected_skill_version:
        errors.append(f"evidence skill_version must match cases: {expected_skill_version}")
    if evidence.get("schema_version") != 1:
        errors.append("evidence schema_version must be 1")
    if not _non_empty_text(evidence.get("agent")):
        errors.append("evidence agent is required")
    raw_scenarios = evidence.get("scenarios")
    if not isinstance(raw_scenarios, list):
        errors.append("evidence scenarios must be a list")
        raw_scenarios = []
    indexed: dict[str, dict[str, Any]] = {}
    for item in raw_scenarios:
        if not isinstance(item, dict) or not _non_empty_text(item.get("id")):
            errors.append("each scenario must have a non-empty id")
            continue
        identifier = str(item["id"])
        if identifier in indexed:
            errors.append(f"duplicate scenario evidence: {identifier}")
        indexed[identifier] = item
    if _evidence_contains_secret(evidence):
        errors.append("evaluation evidence contains a possible sensitive value")

    results: list[dict[str, Any]] = []
    expected_ids = set()
    total_score = 0.0
    total_possible = 0.0
    for case in cases["scenarios"]:
        if not isinstance(case, dict) or not _non_empty_text(case.get("id")):
            errors.append("each eval case must have a non-empty id")
            continue
        identifier = str(case["id"])
        expected_ids.add(identifier)
        item = indexed.get(identifier)
        scenario_errors: list[str] = []
        if item is None:
            scenario_errors.append("missing scenario evidence")
            item = {}
        if item.get("activation") != case.get("expected_activation"):
            scenario_errors.append(f"activation must be {case.get('expected_activation')!r}")
        for field in ("prompt", "governance_report", "final_diff"):
            if not _non_empty_text(item.get(field)):
                scenario_errors.append(f"{field} is required")
        for field in ("files_read", "files_written"):
            if not _list_of_strings(item.get(field)):
                scenario_errors.append(f"{field} must be a list of strings")
        if not isinstance(item.get("commands"), list):
            scenario_errors.append("commands must be a list")
        else:
            command_text = " ".join(_command_texts(item["commands"])).casefold()
            for required in case.get("required_commands", []):
                if str(required).casefold() not in command_text:
                    scenario_errors.append(f"required command evidence is missing: {required}")
        read_paths = set(item.get("files_read", [])) if _list_of_strings(item.get("files_read")) else set()
        for required in case.get("required_files_read", []):
            if required not in read_paths:
                scenario_errors.append(f"required read evidence is missing: {required}")
        criteria = item.get("criteria")
        if not isinstance(criteria, dict):
            scenario_errors.append("criteria must be an object")
            criteria = {}
        scenario_score = 0.0
        for dimension in dimensions:
            value = criteria.get(dimension)
            if value not in SCORE_VALUES:
                scenario_errors.append(f"criterion {dimension} must be pass, partial, or fail")
            else:
                scenario_score += SCORE_VALUES[value]
        total_score += scenario_score
        total_possible += float(len(dimensions))
        results.append(
            {
                "id": identifier,
                "status": "fail" if scenario_errors or any(criteria.get(dimension) == "fail" for dimension in dimensions) else ("partial" if any(criteria.get(dimension) == "partial" for dimension in dimensions) else "pass"),
                "score": scenario_score,
                "possible": len(dimensions),
                "errors": scenario_errors,
            }
        )
    for unexpected in sorted(set(indexed) - expected_ids):
        errors.append(f"unexpected scenario evidence: {unexpected}")
    errors.extend(f"{result['id']}: {error}" for result in results for error in result["errors"])
    scenario_statuses = [result["status"] for result in results]
    overall_status = "fail" if errors or "fail" in scenario_statuses else ("partial" if "partial" in scenario_statuses else "pass")
    return {
        "status": overall_status,
        "skill_version": evidence.get("skill_version"),
        "expected_skill_version": expected_skill_version,
        "score": total_score,
        "possible": total_possible,
        "percentage": round(total_score / total_possible * 100, 2) if total_possible else 0.0,
        "scenarios": results,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate evidence from an r-doc agent behavior evaluation.")
    parser.add_argument("--input", required=True, type=Path, help="JSON evidence captured from an agent run")
    parser.add_argument("--cases", type=Path, default=Path(__file__).parents[1] / "evals" / "cases.json")
    parser.add_argument("--strict", action="store_true", help="fail when evidence is incomplete or any criterion is not pass")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    try:
        result = evaluate(load_cases(args.cases), load_json(args.input))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        result = {"status": "fail", "score": 0.0, "possible": 0.0, "percentage": 0.0, "scenarios": [], "errors": [str(error)]}
    strict_failure = any(result["status"] == "fail" or item["status"] != "pass" for item in result["scenarios"])
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"r-doc agent evaluation: {result['status'].upper()} score={result['percentage']}%")
        for error in result["errors"]:
            print(f"ERROR {error}")
    return 1 if result["status"] == "fail" or (args.strict and strict_failure) else 0


if __name__ == "__main__":
    sys.exit(main())
