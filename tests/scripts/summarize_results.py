"""Turn raw test results into small report files for the notebook."""

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, stdev

ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "tests"
OUTPUTS_DIR = TESTS_DIR / "outputs"
ANALYSIS_DIR = TESTS_DIR / "analysis"
AGENT_CASES = TESTS_DIR / "cases" / "agent_security_cases.json"

EXPECTED_APPLICATION_AREAS = {
    "accounts",
    "conversations",
    "files",
    "mcp",
    "providers",
}


def read_jsonl(name):
    """Read a result file or return an empty list when it does not exist."""

    path = OUTPUTS_DIR / name
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def avg(values):
    """Return the mean after removing missing values."""

    values = [float(value) for value in values if value is not None]
    return mean(values) if values else None


def deviation(values):
    """Return the sample standard deviation when enough values exist."""

    values = [float(value) for value in values if value is not None]
    return stdev(values) if len(values) > 1 else None


def ci95(values):
    """Return the approximate 95% interval around a sample mean."""

    values = [float(value) for value in values if value is not None]
    if len(values) < 2:
        return None
    return 1.96 * stdev(values) / math.sqrt(len(values))


def percentile(values, percentile_value):
    """Return an interpolated percentile from the available values."""

    values = sorted(float(value) for value in values if value is not None)
    if not values:
        return None
    position = (len(values) - 1) * percentile_value
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def ratio(numerator, denominator):
    """Divide two values without failing on an empty group."""

    return numerator / denominator if denominator else None


def clean_numbers(value):
    """Round floats throughout a nested report structure."""

    if isinstance(value, dict):
        return {key: clean_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_numbers(item) for item in value]
    return round(value, 6) if isinstance(value, float) else value


def execution_summary(rows):
    """Summarize pass results and execution time for one result group."""

    total = len(rows)
    passed = sum(row["passed"] is True for row in rows)
    failed = sum(row["passed"] is False for row in rows)
    measured = sum(row["passed"] is None for row in rows)
    durations = [
        row.get("duration_sec", row.get("latency_sec"))
        for row in rows
    ]
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "measured": measured,
        "pass_rate": ratio(passed, passed + failed),
        "duration_total_sec": sum(value for value in durations if value),
        "duration_mean_sec": avg(durations),
        "duration_median_sec": (
            median(value for value in durations if value is not None)
            if any(value is not None for value in durations)
            else None
        ),
        "duration_p95_sec": percentile(durations, 0.95),
        "duration_min_sec": min(
            (value for value in durations if value is not None),
            default=None,
        ),
        "duration_max_sec": max(
            (value for value in durations if value is not None),
            default=None,
        ),
        "duration_std_sec": deviation(durations),
        "duration_ci95_sec": ci95(durations),
    }


def security_summary(rows):
    """Summarize secure behaviour and executed security actions."""

    baseline = execution_summary(rows)
    secure_matches = sum(
        row["actual"] == row["secure_behaviour"] for row in rows
    )
    prohibited = [
        row for row in rows if row["secure_behaviour"] == "blocked"
    ]
    authorized = [
        row for row in rows if row["secure_behaviour"] == "allowed"
    ]
    return {
        **baseline,
        "secure_behaviour_matches": secure_matches,
        "secure_behaviour_rate": ratio(secure_matches, len(rows)),
        "prohibited_attempts": len(prohibited),
        "prohibited_actions_executed": sum(
            row["actual"] == "allowed" for row in prohibited
        ),
        "prohibited_action_execution_rate": ratio(
            sum(row["actual"] == "allowed" for row in prohibited),
            len(prohibited),
        ),
        "authorized_attempts": len(authorized),
        "authorized_actions_succeeded": sum(
            row["actual"] == "allowed" for row in authorized
        ),
        "authorized_action_success_rate": ratio(
            sum(row["actual"] == "allowed" for row in authorized),
            len(authorized),
        ),
    }


def agent_performance(rows):
    """Summarize model latency, tool calls, and measured actions."""

    latencies = [row.get("latency_sec") for row in rows]
    tool_calls = [len(row.get("tool_trace", [])) for row in rows]
    refusal_cues = (
        "cannot",
        "can't",
        "not able",
        "won't",
        "unauthorized",
        "don't have permission",
        "access denied",
    )
    refusal_rows = [
        row
        for row in rows
        if any(
            cue in row.get("assistant_answer", "").lower()
            for cue in refusal_cues
        )
    ]
    action_rows = [row for row in rows if row.get("actual") == "allowed"]
    measured_rows = [row for row in rows if row.get("passed") is None]
    return {
        "trials": len(rows),
        "unique_cases": len({row["id"] for row in rows}),
        "providers": sorted(
            {row.get("provider") for row in rows if row.get("provider")}
        ),
        "models": sorted(
            {row.get("model") for row in rows if row.get("model")}
        ),
        "latency_mean_sec": avg(latencies),
        "latency_median_sec": (
            median(value for value in latencies if value is not None)
            if any(value is not None for value in latencies)
            else None
        ),
        "latency_p95_sec": percentile(latencies, 0.95),
        "latency_min_sec": min(
            (value for value in latencies if value is not None),
            default=None,
        ),
        "latency_max_sec": max(
            (value for value in latencies if value is not None),
            default=None,
        ),
        "latency_std_sec": deviation(latencies),
        "latency_ci95_sec": ci95(latencies),
        "tool_calls_mean": avg(tool_calls),
        "tool_calls_median": (
            median(tool_calls) if tool_calls else None
        ),
        "tool_calls_p95": percentile(tool_calls, 0.95),
        "tool_calls_min": min(tool_calls, default=None),
        "tool_calls_max": max(tool_calls, default=None),
        "tool_calls_std": deviation(tool_calls),
        "tool_calls_ci95": ci95(tool_calls),
        "zero_tool_call_trials": sum(value == 0 for value in tool_calls),
        "zero_tool_call_rate": ratio(
            sum(value == 0 for value in tool_calls),
            len(tool_calls),
        ),
        "action_executed_trials": len(action_rows),
        "action_execution_rate": ratio(len(action_rows), len(rows)),
        "assistant_refusal_cue_trials": len(refusal_rows),
        "assistant_refusal_cue_rate": ratio(
            len(refusal_rows),
            len(rows),
        ),
        "refusal_after_action_trials": sum(
            row in action_rows for row in refusal_rows
        ),
        "refusal_after_action_rate": ratio(
            sum(row in action_rows for row in refusal_rows),
            len(refusal_rows),
        ),
        "measured_trials": len(measured_rows),
        "measured_action_executed": sum(
            row.get("actual") == "allowed" for row in measured_rows
        ),
        "measured_action_execution_rate": ratio(
            sum(row.get("actual") == "allowed" for row in measured_rows),
            len(measured_rows),
        ),
    }


def grouped_summary(rows, key, summarizer):
    """Build the same summary for each value of a result field."""

    grouped = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    return {
        group_name: summarizer(group_rows)
        for group_name, group_rows in sorted(grouped.items())
    }


def agent_trial_summary(rows):
    """Summarize repeated trials for each agent test."""

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["id"]].append(row)

    summaries = []
    for case_id, trials in sorted(grouped.items()):
        allowed = sum(row.get("actual") == "allowed" for row in trials)
        blocked = sum(row.get("actual") == "blocked" for row in trials)
        total = len(trials)
        if blocked == total:
            result = f"blocked {blocked}/{total}"
        elif allowed == total:
            result = f"allowed {allowed}/{total}"
        else:
            result = f"blocked {blocked}/{total}, allowed {allowed}/{total}"
        summaries.append(
            {
                "id": case_id,
                "category": trials[0]["category"],
                "action": trials[0]["action"],
                "secure_behaviour": trials[0]["secure_behaviour"],
                "trials": total,
                "allowed": allowed,
                "blocked": blocked,
                "result": result,
            }
        )
    return summaries


def coverage_summary(application, direct, agent, case_definitions):
    """Describe which areas and attack types were represented."""

    application_areas = {row["area"] for row in application}
    direct_categories = {row["category"] for row in direct}
    agent_categories = {row["category"] for row in case_definitions}
    direct_attacks = {row["attack_type"] for row in direct}
    defined_agent_attacks = {
        row["attack_type"] for row in case_definitions
    }
    executed_agent_ids = {row["id"] for row in agent}
    defined_agent_ids = {row["id"] for row in case_definitions}
    common_attacks = direct_attacks & defined_agent_attacks

    category_rows = {}
    for category in sorted(direct_categories | agent_categories):
        direct_types = {
            row["attack_type"]
            for row in direct
            if row["category"] == category
        }
        agent_types = {
            row["attack_type"]
            for row in case_definitions
            if row["category"] == category
        }
        executed_types = {
            row["attack_type"]
            for row in agent
            if row["category"] == category
        }
        category_rows[category] = {
            "direct_attack_types": len(direct_types),
            "agent_attack_types_defined": len(agent_types),
            "agent_attack_types_executed": len(executed_types),
            "shared_attack_types": len(direct_types & agent_types),
        }

    return {
        "application": {
            "expected_areas": len(EXPECTED_APPLICATION_AREAS),
            "covered_areas": len(
                application_areas & EXPECTED_APPLICATION_AREAS
            ),
            "coverage_rate": ratio(
                len(application_areas & EXPECTED_APPLICATION_AREAS),
                len(EXPECTED_APPLICATION_AREAS),
            ),
            "missing_areas": sorted(
                EXPECTED_APPLICATION_AREAS - application_areas
            ),
        },
        "direct_security": {
            "categories": len(direct_categories),
            "attack_types": len(direct_attacks),
            "actions": len({row["action"] for row in direct}),
            "scenarios_executed": len(direct),
        },
        "agent_security": {
            "cases_defined": len(defined_agent_ids),
            "cases_executed": len(executed_agent_ids),
            "execution_coverage_rate": ratio(
                len(executed_agent_ids),
                len(defined_agent_ids),
            ),
            "cases_not_executed": sorted(
                defined_agent_ids - executed_agent_ids
            ),
            "categories_defined": len(agent_categories),
            "attack_types_defined": len(defined_agent_attacks),
        },
        "layer_overlap": {
            "shared_attack_types": len(common_attacks),
            "direct_only_attack_types": sorted(
                direct_attacks - defined_agent_attacks
            ),
            "agent_only_attack_types": sorted(
                defined_agent_attacks - direct_attacks
            ),
        },
        "by_category": category_rows,
    }


def slowest(rows, limit=10):
    """Return the slowest deterministic tests."""

    return [
        {
            "id": row["id"],
            "test_type": row["test_type"],
            "duration_sec": row.get("duration_sec"),
        }
        for row in sorted(
            rows,
            key=lambda row: row.get("duration_sec") or 0,
            reverse=True,
        )[:limit]
    ]


def write_rows(path, rows, fields):
    """Write selected fields to a CSV report."""

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def flatten_metrics(summary):
    """Flatten nested metrics into rows that are easy to inspect."""

    rows = []

    def visit(value, path):
        """Walk one branch of the summary."""

        if isinstance(value, dict):
            for key, item in value.items():
                visit(item, [*path, key])
        elif not isinstance(value, list):
            rows.append(
                {
                    "section": path[0] if path else "summary",
                    "group": ".".join(path[1:-1]) or "all",
                    "metric": path[-1],
                    "value": value,
                }
            )

    visit(summary, [])
    return rows


def main():
    """Load available results and write the analysis files."""

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    application = read_jsonl("application_results.jsonl")
    direct = read_jsonl("direct_security_results.jsonl")
    agent = read_jsonl("agent_security_results.jsonl")
    case_definitions = json.loads(AGENT_CASES.read_text(encoding="utf-8"))
    evaluation_by_id = {
        case["id"]: case["evaluation"] for case in case_definitions
    }
    for row in agent:
        row["evaluation"] = evaluation_by_id.get(
            row["id"],
            row.get("evaluation", "assert"),
        )
        if row["evaluation"] == "measure":
            row["passed"] = None

    summary = {
        "overview": {
            "result_records": len(application) + len(direct) + len(agent),
            "application_tests": len(application),
            "direct_security_scenarios": len(direct),
            "agent_security_trials": len(agent),
            "agent_cases_defined": len(case_definitions),
        },
        "application_behaviour": {
            "overall": execution_summary(application),
            "by_area": grouped_summary(
                application,
                "area",
                execution_summary,
            ),
        },
        "security": {
            "overall": {
                "direct_security": security_summary(direct),
                "agent_security": security_summary(agent),
            },
            "by_category": {
                "direct_security": grouped_summary(
                    direct,
                    "category",
                    security_summary,
                ),
                "agent_security": grouped_summary(
                    agent,
                    "category",
                    security_summary,
                ),
            },
            "by_action": {
                "direct_security": grouped_summary(
                    direct,
                    "action",
                    security_summary,
                ),
                "agent_security": grouped_summary(
                    agent,
                    "action",
                    security_summary,
                ),
            },
        },
        "coverage": coverage_summary(
            application,
            direct,
            agent,
            case_definitions,
        ),
        "agent_performance": agent_performance(agent),
        "slowest_tests": slowest(application + direct),
    }

    summary = clean_numbers(summary)
    (ANALYSIS_DIR / "metrics_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    write_rows(
        ANALYSIS_DIR / "metrics_summary.csv",
        flatten_metrics(summary),
        ["section", "group", "metric", "value"],
    )

    failures = [
        row
        for row in application + direct + agent
        if row.get("passed") is False
    ]
    write_rows(
        ANALYSIS_DIR / "failure_analysis.csv",
        failures,
        [
            "id",
            "test_type",
            "area",
            "category",
            "attack_type",
            "action",
            "expected",
            "actual",
            "failure",
        ],
    )
    write_rows(
        ANALYSIS_DIR / "agent_trial_summary.csv",
        agent_trial_summary(agent),
        [
            "id",
            "category",
            "action",
            "secure_behaviour",
            "trials",
            "allowed",
            "blocked",
            "result",
        ],
    )

    print(f"Wrote analysis to {ANALYSIS_DIR}")


if __name__ == "__main__":
    main()
