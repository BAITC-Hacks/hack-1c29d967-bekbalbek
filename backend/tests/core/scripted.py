"""Deterministic meeting conversations for generic workflow regression tests."""
import json
import uuid

from agents.testing import ScriptedModel, assistant_message, function_call

from app.domain import repo
from app.domain.seed import seed
from app.speech.align import SpokenSegment

FULL_PLAN = [
    {"action_id": f"a{i}", "type": "action_item", "text": text, "owner_name": "Асхат",
     "owner_speaker_id": "S1", "deadline_text": "до пятницы", "deadline_date": "2026-09-25",
     "source_segment_ids": [i], "urgency": "средний"}
    for i, text in enumerate(["Подготовить отчёт", "Проверить смету", "Согласовать договор"], 1)
]
SMALL_PLAN = [FULL_PLAN[0], FULL_PLAN[2]]
BAD_PLAN = [{**FULL_PLAN[0], "source_segment_ids": [99999]}]


async def seed_ready_meetings(session):
    result = await seed(session)
    for meeting_id in ["m-sample-1", "m-sample-2"]:
        segments = [SpokenSegment(i * 5.0, (i + 1) * 5.0, "S1", "ru",
                    f"Асхат, {a['text']} до пятницы.") for i, a in enumerate(FULL_PLAN)]
        await repo.replace_transcript(session, meeting_id, segments, 15.0)
        await repo.set_status(session, meeting_id, "ready")
    return result


def tool(name, arguments=None, call_id=None):
    return function_call(name, arguments or {}, call_id=call_id or str(uuid.uuid4()))


def scripted(*steps):
    return ScriptedModel(list(steps))


def proposal_output(actions, summary="Обсудили отчёт, смету и договор"):
    return json.dumps({"outcome": "proposal_ready", "message": "Протокол готов", "proposal": {
        "summary": summary, "actions": actions, "decisions": [], "evidence": [],
        "assumptions": [], "expected_effects": []}, "missing_fields": [], "blocking_constraints": []})


def needs_input_output():
    return json.dumps({"outcome": "needs_input", "message": "Уточните имя участника", "proposal": None,
        "missing_fields": [{"field": "notes", "reason": "Уточните имя говорящего"}], "blocking_constraints": []})


def infeasible_output():
    return json.dumps({"outcome": "infeasible", "message": "Нет подтверждённой стенограммы", "proposal": None,
        "missing_fields": [], "blocking_constraints": [
            {"rule_id": "transcript_ready", "detail": "Нужна стенограмма", "refs": []}]})


def happy_script(actions=FULL_PLAN):
    return scripted(
        [tool("get_meeting", {}, "c1")],
        [tool("read_transcript", {"offset": 0, "limit": 60}, "c2")],
        [tool("search_transcript", {"query": "до пятницы"}, "c3")],
        [tool("resolve_deadline", {"phrase": "до пятницы"}, "c4")],
        [assistant_message(proposal_output(actions))],
    )
