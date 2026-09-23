import pytest

from app.config import Settings
from app.core.events import EventBus
from app.domain import DOMAIN
from app.domain.seed import seed


@pytest.fixture
async def seeded(session_factory) -> dict[str, int]:
    async with session_factory() as session, session.begin():
        return await seed(session)


@pytest.fixture
def bus(session_factory) -> EventBus:
    return EventBus(session_factory)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        agent_max_turns=8,
        agent_run_timeout_seconds=10,
        tool_timeout_seconds=5,
        tool_max_retries=1,
        agent_max_revisions=1,
        openai_model="scripted",
    )


@pytest.fixture
def domain():
    return DOMAIN
