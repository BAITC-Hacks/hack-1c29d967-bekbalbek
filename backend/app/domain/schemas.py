from datetime import date
from typing import ClassVar, Literal

from pydantic import BaseModel, Field

from app.core.contracts import ActionBase, ProposalBase


class CaseInput(BaseModel):
    meeting_date: date
    language: Literal["ru", "kk", "auto"] = "auto"
    notes: str | None = Field(default=None, max_length=2000)


class ActionItemAction(ActionBase):
    type: Literal["action_item"] = "action_item"
    text: str = Field(min_length=1, max_length=500)
    owner_name: str = Field(description="Имя из стенограммы или 'не назначен'", max_length=200)
    owner_speaker_id: str | None = Field(default=None, description="S1..Sn говорящего, который ДАЛ поручение")
    deadline_text: str = Field(default="", max_length=500)
    deadline_date: date | None = None
    urgency: Literal["высокий", "средний", "низкий"] = "средний"
    source_segment_ids: list[int] = Field(min_length=1, description="Идентификаторы сегментов с поручением")


class ProtocolProposal(ProposalBase):
    allow_empty_actions: ClassVar[bool] = True
    actions: list[ActionItemAction]
    decisions: list[str] = Field(default_factory=list)
