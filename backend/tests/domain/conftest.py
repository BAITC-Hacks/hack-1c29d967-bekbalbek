import uuid
from datetime import date

import pytest
from agents import RunContextWrapper

from app.core.context import RunContext
from app.domain.schemas import CaseInput
from app.domain.seed import seed

CASE = "case-dispatch-001"
START = date(2026, 9, 24)


@pytest.fixture
async def seeded(session_factory) -> dict[str, int]:
    async with session_factory() as session, session.begin():
        return await seed(session)


async def noop_emit(event_type: str, payload: dict) -> None:
    return None


def make_run_ctx(
    session_factory, case_ref: str = CASE, case_input: CaseInput | None = None
) -> RunContextWrapper[RunContext]:
    ctx = RunContext(
        run_id=uuid.uuid4(),
        case_ref=case_ref,
        case_input=case_input or CaseInput(planning_start=START),
        session_factory=session_factory,
        emit=noop_emit,
    )
    return RunContextWrapper(context=ctx)
