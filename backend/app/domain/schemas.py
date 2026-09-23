from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.core.contracts import ActionBase, ProposalBase

Priority = Literal["low", "normal", "high"]
JobStatus = Literal["unassigned", "assigned", "done"]


RecordId = Annotated[str, StringConstraints(min_length=1, max_length=60)]
MAX_LIST_ITEMS = 100


class JobOverride(BaseModel):
    required_skill: str | None = Field(default=None, max_length=60)
    duration_hours: int | None = Field(default=None, ge=1, le=24)


class CaseInput(BaseModel):
    planning_start: date
    job_ids: list[RecordId] = Field(
        default_factory=list,
        max_length=MAX_LIST_ITEMS,
        description="Jobs to schedule; empty means every unassigned job in the case",
    )
    job_overrides: dict[RecordId, JobOverride] = Field(default_factory=dict, max_length=MAX_LIST_ITEMS)
    capacity_overrides: dict[RecordId, Annotated[int, Field(ge=0, le=24)]] = Field(
        default_factory=dict, max_length=MAX_LIST_ITEMS
    )
    notes: str | None = Field(default=None, max_length=2000)


class AssignJobAction(ActionBase):
    type: Literal["assign_job"] = "assign_job"
    job_id: str
    worker_id: str
    scheduled_date: date


class DispatchProposal(ProposalBase):
    actions: list[AssignJobAction]
