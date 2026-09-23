from typing import Literal

import pytest
from agents import AgentOutputSchema
from pydantic import ValidationError

from app.core.contracts import (
    ActionBase,
    AgentOutputBase,
    ProposalBase,
    ValidationCheck,
    ValidationReport,
    make_agent_output,
    structural_checks,
)


class DemoAction(ActionBase):
    type: Literal["demo"] = "demo"
    target: str


class DemoProposal(ProposalBase):
    actions: list[DemoAction]


def _check(rule_id: str, status: str, action_id: str | None = None) -> ValidationCheck:
    return ValidationCheck(rule_id=rule_id, label=rule_id, status=status, message="m", action_id=action_id)


def test_should_build_a_strict_schema_agent_output_for_a_domain_proposal() -> None:
    output_model = make_agent_output(DemoProposal)
    schema = AgentOutputSchema(output_model, strict_json_schema=True).json_schema()
    assert set(schema["required"]) == {"outcome", "message", "proposal", "missing_fields", "blocking_constraints"}


def test_should_parse_proposal_ready_into_the_domain_proposal_type() -> None:
    output_model = make_agent_output(DemoProposal)
    parsed = output_model.model_validate(
        {
            "outcome": "proposal_ready",
            "message": "ok",
            "proposal": {"summary": "s", "actions": [{"action_id": "a1", "target": "x"}]},
        }
    )
    assert isinstance(parsed, AgentOutputBase)
    assert isinstance(parsed.proposal, DemoProposal)
    assert parsed.proposal.actions[0].target == "x"


def test_should_reject_an_unknown_outcome() -> None:
    output_model = make_agent_output(DemoProposal)
    with pytest.raises(ValidationError):
        output_model.model_validate({"outcome": "done", "message": "x"})


def test_should_mark_report_not_ok_when_any_check_fails() -> None:
    report = ValidationReport.from_checks([_check("a", "pass"), _check("b", "fail"), _check("c", "warn")])
    assert report.ok is False
    assert [c.rule_id for c in report.errors] == ["b"]
    assert [c.rule_id for c in report.warnings] == ["c"]


def test_should_mark_report_ok_when_only_warnings() -> None:
    report = ValidationReport.from_checks([_check("a", "pass"), _check("c", "warn")])
    assert report.ok is True


def test_should_fail_structural_checks_on_duplicate_action_ids() -> None:
    proposal = DemoProposal(
        summary="s", actions=[DemoAction(action_id="a1", target="x"), DemoAction(action_id="a1", target="y")]
    )
    failures = [c for c in structural_checks(proposal) if c.status == "fail"]
    assert [c.rule_id for c in failures] == ["unique_action_id"]


def test_should_fail_structural_checks_on_empty_action_list() -> None:
    proposal = DemoProposal(summary="s", actions=[])
    failures = [c for c in structural_checks(proposal) if c.status == "fail"]
    assert [c.rule_id for c in failures] == ["non_empty_plan"]
