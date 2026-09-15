from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rdoc.security import SECRET_PATTERNS, is_safe_example


SCORE_VALUES = {"pass": 1.0, "partial": 0.5, "fail": 0.0}
MACHINE_RULE_BINDINGS = {
    "activation_boundary": ("activation_matches",),
    "deterministic_verification": (
        "required_paths_present",
        "required_files_present",
        "required_commands_ordered_and_successful",
    ),
    "safety": ("no_unsafe_secret_matches",),
    "repair_discipline": ("required_commands_ordered_and_successful",),
}


MachineCheck = Callable[[dict[str, bool]], bool]


def _activation_matches(values: dict[str, bool]) -> bool:
    return values["activation_ok"]


def _required_paths_present(values: dict[str, bool]) -> bool:
    return values["paths_ok"]


def _required_files_present(values: dict[str, bool]) -> bool:
    return values["reads_ok"]


def _required_commands_ordered_and_successful(values: dict[str, bool]) -> bool:
    return values["commands_ok"]


def _no_unsafe_secret_matches(values: dict[str, bool]) -> bool:
    return not values["evidence_has_secret"]


MACHINE_CHECK_IMPLEMENTATIONS: dict[str, MachineCheck] = {
    "activation_matches": _activation_matches,
    "required_paths_present": _required_paths_present,
    "required_files_present": _required_files_present,
    "required_commands_ordered_and_successful": _required_commands_ordered_and_successful,
    "no_unsafe_secret_matches": _no_unsafe_secret_matches,
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.load(sys.stdin) if str(path) == "-" else json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _validate_machine_rule_contract(machine_rules: object, path: Path) -> None:
    if not isinstance(machine_rules, dict):
        raise ValueError(f"eval machine_rules must be an object: {path}")

    bound_dimensions = set(MACHINE_RULE_BINDINGS)
    if set(machine_rules) != bound_dimensions:
        raise ValueError(f"eval machine rule dimensions are out of sync with code: {path}")

    bound_checks = {check for checks in MACHINE_RULE_BINDINGS.values() for check in checks}
    implemented_checks = set(MACHINE_CHECK_IMPLEMENTATIONS)
    if implemented_checks != bound_checks:
        raise ValueError(f"machine check implementation registry is out of sync with code bindings: {path}")

    for dimension, expected_checks in MACHINE_RULE_BINDINGS.items():
        rule = machine_rules[dimension]
        checks = rule.get("checks") if isinstance(rule, dict) else None
        if not isinstance(checks, list) or len(checks) != len(set(checks)) or set(checks) != set(expected_checks):
            raise ValueError(f"eval machine rule {dimension} is out of sync with code: {path}")
        if not all(isinstance(check, str) and check in implemented_checks for check in checks):
            raise ValueError(f"eval machine rule {dimension} contains an unimplemented check: {path}")
        if (
            not isinstance(rule, dict)
            or rule.get("type") != "all"
            or not isinstance(rule.get("description"), str)
            or not rule["description"].strip()
        ):
            raise ValueError(f"eval machine rule {dimension} is invalid: {path}")


def load_cases(path: Path) -> dict[str, Any]:
    cases = load_json(path)
    if (
        cases.get("schema_version") != 2
        or not isinstance(cases.get("skill_version"), str)
        or not cases["skill_version"].strip()
        or not isinstance(cases.get("dimensions"), list)
        or not all(isinstance(item, str) and item.strip() for item in cases["dimensions"])
        or not isinstance(cases.get("machine_dimensions"), list)
        or not all(isinstance(item, str) and item.strip() for item in cases["machine_dimensions"])
        or not isinstance(cases.get("review_dimensions"), list)
        or not all(isinstance(item, str) and item.strip() for item in cases["review_dimensions"])
        or not isinstance(cases.get("machine_rules"), dict)
        or not isinstance(cases.get("scenarios"), list)
    ):
        raise ValueError(f"unsupported eval case schema: {path}")
    dimensions = set(cases["dimensions"])
    machine_dimensions = set(cases["machine_dimensions"])
    review_dimensions = set(cases["review_dimensions"])
    if machine_dimensions | review_dimensions != dimensions or machine_dimensions & review_dimensions:
        raise ValueError(f"eval dimension partition is invalid: {path}")
    machine_rules = cases["machine_rules"]
    if set(machine_rules) != machine_dimensions:
        raise ValueError(f"eval machine rule partition is invalid: {path}")
    _validate_machine_rule_contract(machine_rules, path)
    for case in cases["scenarios"]:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"].strip():
            raise ValueError(f"eval scenario must have a non-empty id: {path}")
        for field in ("required_paths_checked", "required_files_read", "required_command_sequence"):
            values = case.get(field)
            if not isinstance(values, list) or not all(isinstance(item, str) and item.strip() for item in values):
                raise ValueError(f"eval scenario {case['id']} has invalid {field}: {path}")
    return cases


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list_of_strings(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _command_label(value: dict[str, Any]) -> str:
    return " ".join(str(value.get(key, "")) for key in ("name", "command") if value.get(key)).strip()


def _evidence_contains_secret(evidence: dict[str, Any]) -> bool:
    serialized = json.dumps(evidence, ensure_ascii=False)
    for pattern, code in SECRET_PATTERNS:
        for match in pattern.finditer(serialized):
            if not is_safe_example(code, match.group(0)):
                return True
    return False


def evaluate(cases: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    dimensions = [item for item in cases["dimensions"] if isinstance(item, str)]
    review_dimensions = [item for item in cases["review_dimensions"] if isinstance(item, str)]
    errors: list[str] = []
    expected_skill_version = cases.get("skill_version")
    if not _non_empty_text(expected_skill_version):
        errors.append("eval cases skill_version is required")
    elif evidence.get("skill_version") != expected_skill_version:
        errors.append(f"evidence skill_version must match cases: {expected_skill_version}")
    if evidence.get("schema_version") != 2:
        errors.append("evidence schema_version must be 2")
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
        activation_ok = item.get("activation") == case.get("expected_activation")
        for field in ("prompt", "governance_report", "final_diff"):
            if not _non_empty_text(item.get(field)):
                scenario_errors.append(f"{field} is required")
        list_fields_valid: dict[str, bool] = {}
        for field in ("paths_checked", "files_read", "files_written"):
            list_fields_valid[field] = _list_of_strings(item.get(field))
            if not _list_of_strings(item.get(field)):
                scenario_errors.append(f"{field} must be a list of strings")
        paths_ok = list_fields_valid["paths_checked"]
        for required in case.get("required_paths_checked", []):
            if not paths_ok or required not in set(item.get("paths_checked", [])):
                scenario_errors.append(f"required path-check evidence is missing: {required}")
                paths_ok = False
        reads_ok = list_fields_valid["files_read"]
        read_paths = set(item.get("files_read", [])) if reads_ok else set()
        for required in case.get("required_files_read", []):
            if required not in read_paths:
                scenario_errors.append(f"required read evidence is missing: {required}")
                reads_ok = False

        commands_ok = True
        command_entries: list[dict[str, Any]] = []
        raw_commands = item.get("commands")
        if not isinstance(raw_commands, list):
            scenario_errors.append("commands must be a list")
            commands_ok = False
        else:
            for index, command in enumerate(raw_commands):
                if not isinstance(command, dict) or not _non_empty_text(_command_label(command)):
                    scenario_errors.append(f"command {index} must include a name or command")
                    commands_ok = False
                    continue
                if not isinstance(command.get("exit_code"), int) or isinstance(command.get("exit_code"), bool):
                    scenario_errors.append(f"command {index} must include an integer exit_code")
                    commands_ok = False
                    continue
                command_entries.append(command)
            sequence = case.get("required_command_sequence", [])
            if not isinstance(sequence, list) or not all(isinstance(item, str) and item.strip() for item in sequence):
                scenario_errors.append("required_command_sequence must be a list of non-empty strings")
                commands_ok = False
                sequence = []
            cursor = -1
            for required in sequence:
                matches = [
                    (index, command)
                    for index, command in enumerate(command_entries)
                    if required.casefold() in _command_label(command).casefold()
                ]
                successful = [
                    (index, command)
                    for index, command in matches
                    if index > cursor and command["exit_code"] == 0
                ]
                if successful:
                    cursor = successful[0][0]
                    continue
                if not matches:
                    scenario_errors.append(f"required command evidence is missing: {required}")
                elif not any(command["exit_code"] == 0 for _, command in matches):
                    code = matches[0][1]["exit_code"]
                    scenario_errors.append(f"required command must exit 0: {required} (exit_code={code})")
                else:
                    scenario_errors.append(f"required command evidence is out of order: {required}")
                commands_ok = False

        review = item.get("review")
        if not isinstance(review, dict):
            scenario_errors.append("review must be an object")
            review = {}
        review_scores: dict[str, str] = {}
        for dimension in review_dimensions:
            assessment = review.get(dimension)
            if not isinstance(assessment, dict):
                scenario_errors.append(f"review {dimension} must be an object")
                continue
            value = assessment.get("status")
            if value not in SCORE_VALUES:
                scenario_errors.append(f"review {dimension} status must be pass, partial, or fail")
            elif not _non_empty_text(assessment.get("basis")):
                scenario_errors.append(f"review {dimension} basis is required")
            else:
                review_scores[dimension] = value
        unexpected_reviews = sorted(set(review) - set(review_dimensions))
        for dimension in unexpected_reviews:
            scenario_errors.append(f"unexpected review dimension: {dimension}")

        check_values = {
            "activation_ok": activation_ok,
            "paths_ok": paths_ok,
            "reads_ok": reads_ok,
            "commands_ok": commands_ok,
            "evidence_has_secret": _evidence_contains_secret(item),
        }
        available_checks = {
            name: implementation(check_values)
            for name, implementation in MACHINE_CHECK_IMPLEMENTATIONS.items()
        }
        machine_checks = {
            dimension: "pass"
            if all(available_checks[check] for check in cases["machine_rules"][dimension]["checks"])
            else "fail"
            for dimension in cases["machine_dimensions"]
        }
        for dimension, status in machine_checks.items():
            if status == "fail":
                scenario_errors.append(f"machine check {dimension} failed")

        scenario_score = 0.0
        for dimension in dimensions:
            value = machine_checks.get(dimension, review_scores.get(dimension))
            if value in SCORE_VALUES:
                scenario_score += SCORE_VALUES[value]
        total_score += scenario_score
        total_possible += float(len(dimensions))
        dimension_statuses = [*machine_checks.values(), *review_scores.values()]
        results.append(
            {
                "id": identifier,
                "status": "fail" if scenario_errors or "fail" in dimension_statuses else ("partial" if "partial" in dimension_statuses else "pass"),
                "score": scenario_score,
                "possible": len(dimensions),
                "machine_checks": machine_checks,
                "review": review_scores,
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
        "machine_rules": cases["machine_rules"],
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
