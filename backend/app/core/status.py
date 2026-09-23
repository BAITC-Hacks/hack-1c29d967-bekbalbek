from typing import Literal

RunStatus = Literal[
    "queued",
    "analyzing",
    "needs_input",
    "infeasible",
    "proposed",
    "validation_failed",
    "applying",
    "applied",
    "verified",
    "failed",
    "interrupted",
]

TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"verified", "failed", "interrupted", "infeasible", "needs_input", "validation_failed"}
)
IN_FLIGHT_STATUSES: frozenset[str] = frozenset({"queued", "analyzing", "applying"})


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES
