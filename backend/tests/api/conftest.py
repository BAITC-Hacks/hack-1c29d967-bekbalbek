from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.domain import DOMAIN
from app.domain.seed import seed
from app.main import create_app


@pytest.fixture
async def seeded(session_factory) -> dict[str, int]:
    async with session_factory() as session, session.begin():
        return await seed(session)


@pytest.fixture
async def client(session_factory, seeded) -> AsyncIterator[AsyncClient]:
    settings = Settings(agent_max_turns=8, agent_run_timeout_seconds=10, openai_model="scripted", openai_api_key=None)
    app = create_app(
        settings, session_factory=session_factory, model_factory=lambda run: DOMAIN.auto_script(run.case_ref, run.input)
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            http.app = app  # type: ignore[attr-defined]
            yield http


async def wait_for_run(client: AsyncClient) -> None:
    await client.app.state.services.registry.wait_all()  # type: ignore[attr-defined]
