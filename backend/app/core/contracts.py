from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, create_model
from sqlalchemy.ext.asyncio import AsyncSession

Outcome = Literal["proposal_ready", "needs_input", "infeasible"]
CheckStatus = Literal["pass", "warn", "fail"]


class EvidenceRef(BaseModel):
    kind: Literal["record", "rule", "tool_result"]
    ref: str
    note: str | None = None


class ActionBase(BaseModel):
    action_id: str = Field(description="Short unique id for this action within the proposal, e.g. 'a1'")
    type: str


class ProposalBase(BaseModel):
    allow_empty_actions: ClassVar[bool] = False

    summary: str = Field(description="One or two sentences a manager can read in five seconds")
    actions: list[ActionBase]
    evidence: list[EvidenceRef] = Field(
        default_factory=list, description="Record ids, rule ids and tool results that support the plan"
    )
    assumptions: list[str] = Field(default_factory=list)
    expected_effects: list[str] = Field(default_factory=list)


class MissingField(BaseModel):
    field: str = Field(description="Dotted path of the missing input, e.g. jobs.j-107.required_skill")
    reason: str


class BlockingConstraint(BaseModel):
    rule_id: str
    detail: str
    refs: list[str] = Field(default_factory=list)


class AgentOutputBase(BaseModel):
    outcome: Outcome
    message: str = Field(description="Plain-language explanation for the user")
    proposal: ProposalBase | None = None
    missing_fields: list[MissingField] = Field(default_factory=list)
    blocking_constraints: list[BlockingConstraint] = Field(default_factory=list)


def make_agent_output(proposal_model: type[ProposalBase]) -> type[AgentOutputBase]:
    return create_model("AgentOutput", __base__=AgentOutputBase, proposal=(proposal_model | None, None))


class ValidationCheck(BaseModel):
    rule_id: str
    label: str
    status: CheckStatus
    message: str
    action_id: str | None = None
    refs: list[str] = Field(default_factory=list)
    source: str | None = None


class ValidationReport(BaseModel):
    ok: bool
    checks: list[ValidationCheck]
    errors: list[ValidationCheck]

    @classmethod
    def from_checks(cls, checks: list[ValidationCheck]) -> "ValidationReport":
        errors = [c for c in checks if c.status == "fail"]
        return cls(ok=not errors, checks=list(checks), errors=errors)

    @property
    def warnings(self) -> list[ValidationCheck]:
        return [c for c in self.checks if c.status == "warn"]


def structural_checks(proposal: ProposalBase) -> list[ValidationCheck]:
    ids = [a.action_id for a in proposal.actions]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    return [
        ValidationCheck(
            rule_id="non_empty_plan",
            label="Plan has actions",
            status="pass" if ids or proposal.allow_empty_actions else "fail",
            message=f"{len(ids)} action(s)" if ids else "The proposal contains no actions",
        ),
        ValidationCheck(
            rule_id="unique_action_id",
            label="Action ids are unique",
            status="fail" if duplicates else "pass",
            message=f"Duplicate action ids: {', '.join(duplicates)}" if duplicates else "All action ids are unique",
        ),
    ]


class VerificationCheck(BaseModel):
    id: str
    label: str
    ok: bool
    detail: str


class VerificationReport(BaseModel):
    ok: bool
    summary: str
    checks: list[VerificationCheck]

    @classmethod
    def from_checks(cls, checks: list[VerificationCheck], summary: str) -> "VerificationReport":
        return cls(ok=all(c.ok for c in checks), summary=summary, checks=list(checks))


class ActionResult(BaseModel):
    action_id: str
    type: str
    summary: str
    result: dict[str, Any] = Field(default_factory=dict)


class ExampleRequest(BaseModel):
    case_ref: str
    goal: str
    input: dict[str, Any]


class ExampleCase(BaseModel):
    id: str
    title: str
    description: str
    expected_outcome: Outcome
    request: ExampleRequest


class ToolError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class TransientToolError(ToolError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, retryable=True)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    label: str
    fn: Callable[..., Awaitable[Any]]
    description: str | None = None


class CaseNotFound(Exception):
    pass


SessionFn = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class DomainModule:
    key: str
    title: str
    agent_name: str
    case_input_model: type[BaseModel]
    proposal_model: type[ProposalBase]
    tools: list[ToolSpec]
    instructions: Callable[[BaseModel], str]
    task_prompt: Callable[[str, str, BaseModel], str]
    load_case_view: Callable[[AsyncSession, str], Awaitable[dict[str, Any]]]
    validate_proposal: Callable[[AsyncSession, str, BaseModel, ProposalBase], Awaitable[ValidationReport]]
    fingerprint: Callable[[AsyncSession, str, BaseModel, ProposalBase], Awaitable[str]]
    snapshot: Callable[[AsyncSession, str, BaseModel], Awaitable[dict[str, Any]]]
    execute_actions: Callable[
        [AsyncSession, str, BaseModel, ProposalBase, dict[str, str]], Awaitable[list[ActionResult]]
    ]
    verify_outcome: Callable[
        [AsyncSession, str, BaseModel, ProposalBase, list[ActionResult]], Awaitable[VerificationReport]
    ]
    seed: Callable[[AsyncSession], Awaitable[dict[str, int]]]
    required_tools: tuple[str, ...] = ()
    examples: list[ExampleCase] = field(default_factory=list)
    api_router: APIRouter | None = None
    scripts: dict[str, Callable[[], Any]] = field(default_factory=dict)
    auto_script: Callable[[str, dict[str, Any]], Any] | None = None

    @property
    def agent_output_model(self) -> type[AgentOutputBase]:
        return make_agent_output(self.proposal_model)

    @property
    def tool_labels(self) -> dict[str, str]:
        return {t.name: t.label for t in self.tools}


class ExecutionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
