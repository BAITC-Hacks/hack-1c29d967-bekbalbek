"""Canned agent conversations for the sample domain: used by evals, tests and the OPENAI_MODEL=scripted:<name> demo fallback."""

import json
from collections.abc import Callable
from typing import Any

from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call

FULL_PLAN: list[dict[str, Any]] = [
    {"action_id": "a1", "type": "assign_job", "job_id": "j-101", "worker_id": "w-chen", "scheduled_date": "2026-09-24"},
    {"action_id": "a2", "type": "assign_job", "job_id": "j-105", "worker_id": "w-ana", "scheduled_date": "2026-09-24"},
    {
        "action_id": "a3",
        "type": "assign_job",
        "job_id": "j-103",
        "worker_id": "w-boris",
        "scheduled_date": "2026-09-24",
    },
    {"action_id": "a4", "type": "assign_job", "job_id": "j-102", "worker_id": "w-ana", "scheduled_date": "2026-09-25"},
    {"action_id": "a5", "type": "assign_job", "job_id": "j-104", "worker_id": "w-chen", "scheduled_date": "2026-09-24"},
    {
        "action_id": "a6",
        "type": "assign_job",
        "job_id": "j-106",
        "worker_id": "w-boris",
        "scheduled_date": "2026-09-25",
    },
]
REDUCED_CAPACITY_PLAN: list[dict[str, Any]] = [
    {**FULL_PLAN[0]},
    {**FULL_PLAN[1]},
    {**FULL_PLAN[2]},
    {**FULL_PLAN[3]},
    {"action_id": "a5", "type": "assign_job", "job_id": "j-104", "worker_id": "w-ana", "scheduled_date": "2026-09-26"},
    {**FULL_PLAN[5]},
]
BAD_PLAN: list[dict[str, Any]] = [
    {
        "action_id": "a1",
        "type": "assign_job",
        "job_id": "j-101",
        "worker_id": "w-boris",
        "scheduled_date": "2026-09-24",
    },
]
SMALL_PLAN: list[dict[str, Any]] = [FULL_PLAN[0], FULL_PLAN[2]]


def proposal_output(actions: list[dict[str, Any]], summary: str = "Assign the open jobs this week") -> str:
    return json.dumps(
        {
            "outcome": "proposal_ready",
            "message": "Plan ready for review.",
            "proposal": {
                "summary": summary,
                "actions": actions,
                "evidence": [
                    {"kind": "record", "ref": "job:j-101", "note": "high priority, due 2026-09-24"},
                    {"kind": "rule", "ref": "rule:daily_capacity", "note": None},
                    {"kind": "tool_result", "ref": "tool_result:simulate_plan", "note": "feasible=true"},
                ],
                "assumptions": ["Existing assignments stay as they are"],
                "expected_effects": [f"{len(actions)} job(s) move from unassigned to assigned"],
            },
            "missing_fields": [],
            "blocking_constraints": [],
        }
    )


def needs_input_output() -> str:
    return json.dumps(
        {
            "outcome": "needs_input",
            "message": "Job j-107 has no required skill.",
            "proposal": None,
            "missing_fields": [{"field": "jobs.j-107.required_skill", "reason": "get_case lists j-107 as incomplete"}],
            "blocking_constraints": [],
        }
    )


def infeasible_output() -> str:
    return json.dumps(
        {
            "outcome": "infeasible",
            "message": "Nobody can weld and nobody has 6h left today.",
            "proposal": None,
            "missing_fields": [],
            "blocking_constraints": [
                {"rule_id": "skill_match", "detail": "No worker has welding", "refs": ["job:j-109"]},
                {"rule_id": "daily_capacity", "detail": "No HVAC worker has 6h on 2026-09-24", "refs": ["job:j-110"]},
            ],
        }
    )


def tool(name: str, arguments: dict[str, Any] | None = None, call_id: str = "call-1"):
    return function_call(name, arguments or {}, call_id=call_id)


def scripted(*steps) -> ScriptedModel:
    return ScriptedModel(list(steps))


def scripted_fallback_output() -> str:
    return json.dumps(
        {
            "outcome": "infeasible",
            "proposal": None,
            "missing_fields": [],
            "message": "Scripted mode: the canned plan no longer validates against the current data (the jobs are probably "
            "already assigned). Reset the sample data or use a real model.",
            "blocking_constraints": [
                {"rule_id": "scripted_mode", "detail": "Canned plan rejected by the validator", "refs": []}
            ],
        }
    )


def happy_script(actions: list[dict[str, Any]] = FULL_PLAN) -> ScriptedModel:
    return scripted(
        [tool("get_case", {}, "c1")],
        [tool("lookup_rules", {}, "c2")],
        [tool("find_resources", {"skill": "electrical", "on_date": None}, "c3")],
        [tool("simulate_plan", {"actions": actions}, "c4")],
        [assistant_message(proposal_output(actions))],
        [assistant_message(scripted_fallback_output())],
    )


def needs_input_script() -> ScriptedModel:
    return scripted([tool("get_case", {}, "c1")], [assistant_message(needs_input_output())])


def infeasible_script() -> ScriptedModel:
    return scripted(
        [tool("get_case", {}, "c1")],
        [tool("find_resources", {"skill": "welding", "on_date": None}, "c2")],
        [assistant_message(infeasible_output())],
    )


def revision_script() -> ScriptedModel:
    return scripted(
        [tool("get_case", {}, "c1")],
        [assistant_message(proposal_output(BAD_PLAN))],
        [tool("simulate_plan", {"actions": FULL_PLAN}, "c2")],
        [assistant_message(proposal_output(FULL_PLAN))],
    )


def tool_failure_script() -> ScriptedModel:
    return scripted(
        [tool("find_resources", {"skill": None, "on_date": "not-a-date"}, "c1")],
        [tool("find_resources", {"skill": None, "on_date": "2026-09-24"}, "c2")],
        [assistant_message(proposal_output(FULL_PLAN))],
    )


def model_error_script() -> ScriptedModel:
    return scripted([tool("get_case", {}, "c1")], ModelStep.raise_error(RuntimeError("simulated provider outage")))


SCRIPTS: dict[str, Callable[[], ScriptedModel]] = {
    "happy": happy_script,
    "reduced_capacity": lambda: happy_script(REDUCED_CAPACITY_PLAN),
    "needs_input": needs_input_script,
    "infeasible": infeasible_script,
    "revision": revision_script,
    "tool_failure": tool_failure_script,
    "model_error": model_error_script,
}


def auto_script(case_ref: str, case_input: dict[str, Any]) -> ScriptedModel:
    if case_ref == "case-dispatch-002":
        return needs_input_script()
    if case_ref == "case-dispatch-003":
        return infeasible_script()
    if case_input.get("capacity_overrides"):
        return happy_script(REDUCED_CAPACITY_PLAN)
    return happy_script()
