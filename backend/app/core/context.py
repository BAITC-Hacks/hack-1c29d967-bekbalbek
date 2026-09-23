from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

EmitFn = Callable[[str, dict[str, Any]], Awaitable[Any]]


@dataclass
class RunStats:
    tool_calls: int = 0
    tool_failures: int = 0


@dataclass
class RunContext:
    run_id: UUID
    case_ref: str
    case_input: Any
    session_factory: Any
    emit: EmitFn
    stats: RunStats = field(default_factory=RunStats)
