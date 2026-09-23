from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services import Services


def get_services(request: Request) -> Services:
    return request.app.state.services


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.services.session_factory() as session:
        yield session


ServicesDep = Annotated[Services, Depends(get_services)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
