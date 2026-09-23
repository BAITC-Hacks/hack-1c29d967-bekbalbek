from app.domain.schemas import CaseInput


def build_instructions(case_input: CaseInput) -> str:
    return f"""You are a dispatch planner for a field-service team. Your job is to assign the requested unassigned jobs to technicians for the planning horizon that starts on {case_input.planning_start.isoformat()}.

Scope and rules of engagement:
- You can only read data and simulate plans. You never apply changes; a human approves and the system applies them.
- Work in this order: get_case → lookup_rules → find_resources (per skill) → simulate_plan on your candidate → fix every failing check → simulate again → final answer.
- Never claim an assignment was made. Your output is a proposal.
- Dates are ISO strings (YYYY-MM-DD). Action ids are short: a1, a2, ...
- Prefer the same zone and the earliest feasible date; high-priority jobs first. Cross-zone assignments are allowed (warning only).

Outcomes:
- proposal_ready: every requested job that can be placed has an action, the last simulate_plan showed feasible=true, and you cite evidence (record ids like job:j-101 and worker:w-ana, rule ids like rule:daily_capacity, and tool results like tool_result:simulate_plan). List assumptions and expected effects. If a subset of jobs cannot be placed but others can, still return a proposal for the feasible ones and explain the rest in the message and assumptions.
- needs_input: a requested job is missing required_skill or duration_hours (get_case lists them under incomplete_jobs). Return the exact fields as jobs.<job_id>.<field>. Do not guess values.
- infeasible: no requested job can be placed without violating a fail-severity rule (for example no worker has the skill, or no worker has enough remaining capacity before the deadline). Name the blocking rule ids and the records involved.
"""


def build_task_prompt(case_ref: str, goal: str, case_input: CaseInput) -> str:
    extras = []
    if case_input.job_ids:
        extras.append(f"Only schedule these jobs: {', '.join(case_input.job_ids)}.")
    if case_input.job_overrides:
        extras.append(
            "The user supplied job details (already applied in get_case): "
            + ", ".join(
                f"{job_id} {override.model_dump(exclude_none=True)}"
                for job_id, override in case_input.job_overrides.items()
            )
        )
    if case_input.capacity_overrides:
        extras.append(
            "Capacity overrides in effect (already applied): "
            + ", ".join(f"{worker_id}={hours}h/day" for worker_id, hours in case_input.capacity_overrides.items())
        )
    if case_input.notes:
        extras.append(f"Notes from the user: {case_input.notes}")
    return f"Case {case_ref}. Goal: {goal}\n" + "\n".join(extras)
