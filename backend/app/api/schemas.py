from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RunOptions(BaseModel):
    max_turns: int | None = Field(default=None, ge=1, le=100)


class CreateRunRequest(BaseModel):
    case_ref: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=2000)
    input: dict[str, Any] = Field(default_factory=dict)
    options: RunOptions | None = None


class ApplyRequest(BaseModel):
    proposal_id: UUID
    version: int = Field(ge=1)
