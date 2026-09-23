import uuid
from datetime import date

import pytest
from agents import RunContextWrapper

from app.core.context import RunContext
from app.domain.schemas import CaseInput
from tests.core.scripted import seed_ready_meetings

CASE = "m-sample-1"
START = date(2026, 9, 23)


@pytest.fixture
async def seeded(session_factory):
    async with session_factory() as session, session.begin():
        return await seed_ready_meetings(session)


@pytest.fixture
async def meeting_with_transcript(seeded):
    return CASE


@pytest.fixture
async def session(session_factory):
    async with session_factory() as session:
        yield session


async def noop_emit(event_type: str, payload: dict) -> None:
    pass


def make_run_ctx(session_factory, case_ref: str = CASE, case_input: CaseInput | None = None):
    return RunContextWrapper(
        context=RunContext(
            run_id=uuid.uuid4(),
            case_ref=case_ref,
            case_input=case_input or CaseInput(meeting_date=START),
            session_factory=session_factory,
            emit=noop_emit,
        )
    )
