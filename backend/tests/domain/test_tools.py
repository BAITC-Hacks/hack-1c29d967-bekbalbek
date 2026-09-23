from datetime import date

from app.domain.schemas import AssignJobAction, CaseInput, JobOverride
from app.domain.tools import TOOLS, find_resources, get_case, lookup_rules, simulate_plan
from tests.domain.conftest import START, make_run_ctx


async def test_should_expose_four_labelled_tools() -> None:
    assert [t.name for t in TOOLS] == ["get_case", "find_resources", "lookup_rules", "simulate_plan"]
    assert all(t.label for t in TOOLS)


async def test_get_case_should_return_requested_jobs_with_overrides_applied(session_factory, seeded) -> None:
    ci = CaseInput(planning_start=START, job_ids=["j-107"], job_overrides={"j-107": JobOverride(required_skill="hvac")})
    result = await get_case(make_run_ctx(session_factory, "case-dispatch-002", ci))
    assert result["case_ref"] == "case-dispatch-002"
    assert [j["id"] for j in result["jobs"]] == ["j-107"]
    assert result["jobs"][0]["required_skill"] == "hvac" and result["jobs"][0]["duration_hours"] == 2
    assert result["existing_assignments"] and result["planning_start"] == "2026-09-24"


async def test_get_case_should_report_incomplete_jobs(session_factory, seeded) -> None:
    result = await get_case(make_run_ctx(session_factory, "case-dispatch-002"))
    assert "j-107" in result["incomplete_jobs"]


async def test_find_resources_should_filter_by_skill_and_report_remaining_capacity(session_factory, seeded) -> None:
    result = await find_resources(make_run_ctx(session_factory), skill="electrical", on_date=None)
    ids = [w["id"] for w in result["workers"]]
    assert ids == ["w-ana", "w-chen"]
    ana = result["workers"][0]
    assert ana["remaining_by_date"]["2026-09-24"] == 4 and ana["remaining_by_date"]["2026-09-25"] == 8
    chen = result["workers"][1]
    assert chen["remaining_by_date"]["2026-09-25"] == 0 and "2026-09-25" in chen["unavailable_dates"]


async def test_find_resources_should_narrow_to_one_date(session_factory, seeded) -> None:
    result = await find_resources(make_run_ctx(session_factory), skill=None, on_date="2026-09-24")
    assert all(list(w["remaining_by_date"]) == ["2026-09-24"] for w in result["workers"])


async def test_lookup_rules_should_list_rules_with_sources(session_factory, seeded) -> None:
    result = await lookup_rules(make_run_ctx(session_factory))
    assert {r["id"] for r in result["rules"]} >= {"skill_match", "daily_capacity", "deadline"}
    assert all(r["source"] and r["severity"] in ("fail", "warn") for r in result["rules"])


async def test_simulate_plan_should_report_feasibility_and_failed_rules(session_factory, seeded) -> None:
    bad = AssignJobAction(action_id="a1", job_id="j-101", worker_id="w-boris", scheduled_date=date(2026, 9, 24))
    result = await simulate_plan(make_run_ctx(session_factory), actions=[bad])
    assert result["feasible"] is False and "skill_match" in result["failed_rule_ids"]
    assert all(c["status"] != "pass" for c in result["issues"])
    assert result["passed_checks"] > 0


async def test_simulate_plan_should_accept_a_feasible_plan(session_factory, seeded) -> None:
    good = AssignJobAction(action_id="a1", job_id="j-101", worker_id="w-chen", scheduled_date=date(2026, 9, 24))
    result = await simulate_plan(make_run_ctx(session_factory), actions=[good])
    assert result["feasible"] is True and result["load"]["w-chen"]["2026-09-24"] == {"hours": 3, "capacity": 8}
