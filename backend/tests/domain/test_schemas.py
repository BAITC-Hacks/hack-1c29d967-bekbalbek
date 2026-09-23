import pytest
from pydantic import ValidationError

from app.domain.api import WorkerPatch
from app.domain.schemas import CaseInput, JobOverride


def test_should_cap_the_number_of_job_ids_and_overrides() -> None:
    with pytest.raises(ValidationError):
        CaseInput(planning_start="2026-09-24", job_ids=[f"j-{i}" for i in range(101)])
    with pytest.raises(ValidationError):
        CaseInput(
            planning_start="2026-09-24", job_overrides={f"j-{i}": JobOverride(duration_hours=1) for i in range(101)}
        )
    with pytest.raises(ValidationError):
        CaseInput(planning_start="2026-09-24", capacity_overrides={f"w-{i}": 1 for i in range(101)})


def test_should_cap_string_lengths_in_overrides_and_ids() -> None:
    with pytest.raises(ValidationError):
        JobOverride(required_skill="x" * 61)
    with pytest.raises(ValidationError):
        CaseInput(planning_start="2026-09-24", job_ids=["j" * 61])
    with pytest.raises(ValidationError):
        CaseInput(planning_start="2026-09-24", capacity_overrides={"w-ana": 25})


def test_should_reject_invalid_dates_in_worker_patch() -> None:
    with pytest.raises(ValidationError):
        WorkerPatch(unavailable_dates=["not-a-date"])
    assert WorkerPatch(unavailable_dates=["2026-09-24"]).unavailable_dates[0].isoformat() == "2026-09-24"
