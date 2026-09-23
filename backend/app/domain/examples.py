from app.core.contracts import ExampleCase, ExampleRequest

GOAL = "Assign every open job for this week to a qualified technician without breaking capacity, deadline or availability rules."

EXAMPLES: list[ExampleCase] = [
    ExampleCase(
        id="week-plan",
        title="Schedule the week's open jobs",
        expected_outcome="proposal_ready",
        description="Six unassigned jobs, four technicians, two existing assignments. Expect a full plan with one cross-zone warning.",
        request=ExampleRequest(case_ref="case-dispatch-001", goal=GOAL, input={"planning_start": "2026-09-24"}),
    ),
    ExampleCase(
        id="missing-skill",
        title="Job with an unknown skill",
        expected_outcome="needs_input",
        description="Job j-107 has no required skill. The agent must ask for jobs.j-107.required_skill instead of guessing.",
        request=ExampleRequest(
            case_ref="case-dispatch-002", goal="Schedule the two clinic jobs.", input={"planning_start": "2026-09-24"}
        ),
    ),
    ExampleCase(
        id="impossible",
        title="Jobs nobody can take",
        expected_outcome="infeasible",
        description="A welding job with no qualified worker and a 6h HVAC job nobody has capacity for before its deadline.",
        request=ExampleRequest(
            case_ref="case-dispatch-003",
            goal="Schedule both emergency jobs today.",
            input={"planning_start": "2026-09-24"},
        ),
    ),
    ExampleCase(
        id="reduced-capacity",
        title="Same week, Chen at half capacity",
        expected_outcome="proposal_ready",
        description="Identical jobs, but Chen can only work 4h/day. The plan must move work to other days or people.",
        request=ExampleRequest(
            case_ref="case-dispatch-001",
            goal=GOAL,
            input={"planning_start": "2026-09-24", "capacity_overrides": {"w-chen": 4}},
        ),
    ),
]
