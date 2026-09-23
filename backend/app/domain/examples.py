from app.core.contracts import ExampleCase, ExampleRequest
from app.domain.seed import SAMPLES

GOAL = "Составь протокол совещания: саммари, решения и поручения с ответственными и сроками."
EXAMPLES = [
    ExampleCase(
        id=meeting_id,
        title=title,
        description="Загрузите или распознайте запись, затем составьте протокол.",
        expected_outcome="proposal_ready",
        request=ExampleRequest(case_ref=meeting_id, goal=GOAL, input={"meeting_date": "2026-09-23"}),
    )
    for meeting_id, title, _ in SAMPLES
]
