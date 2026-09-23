from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.schemas import ActionItemAction, CaseInput, ProtocolProposal


def test_action_requires_source_evidence():
    with pytest.raises(ValidationError):
        ActionItemAction(action_id="a1", text="Отчёт", owner_name="не назначен", source_segment_ids=[])


def test_meeting_input_and_empty_protocol():
    assert CaseInput(meeting_date="2026-09-23").meeting_date == date(2026, 9, 23)
    assert ProtocolProposal(summary="Нет поручений", actions=[]).actions == []
