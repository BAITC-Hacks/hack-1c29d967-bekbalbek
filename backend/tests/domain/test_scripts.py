from app.config import Settings
from app.core.events import EventBus
from app.core.run_service import RunService
from app.domain import DOMAIN
from app.domain.models import Meeting
from app.domain.scripts import auto_script


async def test_auto_script_uses_real_transcript_tools(session_factory, meeting_with_transcript):
    service = RunService(
        session_factory,
        DOMAIN,
        Settings(openai_model="scripted:auto"),
        EventBus(session_factory),
        lambda run: auto_script(run.case_ref, run.input),
    )
    run = await service.create_run(
        case_ref=meeting_with_transcript, goal="Протокол", input={"meeting_date": "2026-09-23"}
    )
    await service.execute(run.id)
    detail = await service.get_run_detail(run.id)
    assert detail.run.status == "proposed"
    assert len(detail.proposal.content["actions"]) == 3
    assert detail.run.stats.tool_calls == 2
    assert detail.proposal.content["evidence"][0]["ref"] == "segment:1"


async def test_auto_script_reports_transcript_not_ready(session_factory, meeting_with_transcript):
    async with session_factory() as session, session.begin():
        meeting = await session.get(Meeting, meeting_with_transcript)
        meeting.status = "uploaded"
    service = RunService(
        session_factory,
        DOMAIN,
        Settings(openai_model="scripted:auto"),
        EventBus(session_factory),
        lambda run: auto_script(run.case_ref, run.input),
    )
    run = await service.create_run(
        case_ref=meeting_with_transcript, goal="Протокол", input={"meeting_date": "2026-09-23"}
    )
    await service.execute(run.id)
    detail = await service.get_run_detail(run.id)
    assert detail.run.status == "needs_input"


def test_numbered_tasks_keep_explicit_owners_deadlines_and_segment_evidence():
    from datetime import date

    from app.domain.scripts import _actions

    rows = [{"id": 27, "speaker": "S2", "text": (
        "Доля выросла до 8%. Первое. Подготовить план, ответственный Иван Петров, до пятницы. "
        "Второе. Проверить расчёт, ответственная Анна Иванова, к 15 октября. "
        "Третье. Направить письмо, ответственный Пётр Сидоров, через две недели. "
        "Четвертое. Согласовать акт, ответственный Иван Петров, до 25.09.2026."
    )}]
    actions = _actions(rows, date(2026, 9, 23))
    assert len(actions) == 3
    assert [a['owner_name'] for a in actions] == ['Иван Петров', 'Анна Иванова', 'Пётр Сидоров']
    assert [a['deadline_date'] for a in actions] == ['2026-09-25', '2026-10-15', '2026-10-07']
    assert all(a['source_segment_ids'] == [27] and a['owner_speaker_id'] == 'S2' for a in actions)
    assert all('Четвертое' not in a['text'] for a in actions)


def test_numeric_tasks_direct_address_and_statistic_rejection():
    from datetime import date

    from app.domain.scripts import _actions

    rows = [{"id": 9, "speaker": "S1", "text": (
        "Отчёт показывает рост до 8%. 1. Ольга Петрова, подготовьте письмо до 25.09.2026. "
        "2. Проверить расчёт к среде."
    )}]
    actions = _actions(rows, date(2026, 9, 23))
    assert len(actions) == 2
    assert actions[0]['owner_name'] == 'Ольга Петрова'
    assert actions[0]['deadline_date'] == '2026-09-25'
    assert actions[1]['owner_name'] == 'не назначен'
    assert actions[1]['deadline_text'] == 'к среде'
