from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.apply_service import ApplyService
from app.core.contracts import DomainModule
from app.core.events import EventBus
from app.core.run_registry import RunRegistry
from app.core.run_service import RunService


@dataclass(frozen=True)
class Services:
    settings: Settings
    session_factory: async_sessionmaker[AsyncSession]
    bus: EventBus
    registry: RunRegistry
    run_service: RunService
    apply_service: ApplyService
    domain: DomainModule
