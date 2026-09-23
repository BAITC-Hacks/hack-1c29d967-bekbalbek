from datetime import date

from app.domain.models import MeetingSegment, MeetingSpeaker
from app.domain.schemas import ActionItemAction, CaseInput, ProtocolProposal
from app.domain.service import execute_actions, fingerprint, validate_proposal, verify_outcome

INPUT = CaseInput(meeting_date=date(2026, 9, 23))


def proposal(**changes):
    action = dict(
        action_id="a1",
        text="Подготовить отчёт",
        owner_name="Гульмира Сериковна",
        owner_speaker_id="S1",
        deadline_text="15 октября",
        deadline_date=None,
        source_segment_ids=[1],
    )
    action.update(changes)
    return ProtocolProposal(summary="Итог", decisions=["Утвердить план"], actions=[ActionItemAction(**action)])


async def test_validate_fails_on_unknown_segment(session, meeting_with_transcript):
    report = await validate_proposal(session, meeting_with_transcript, INPUT, proposal(source_segment_ids=[9999]))
    assert not report.ok and report.errors[0].rule_id == "evidence_exists"


async def test_validate_rejects_segment_from_another_meeting(session, meeting_with_transcript):
    report = await validate_proposal(session, meeting_with_transcript, INPUT, proposal(source_segment_ids=[4]))
    assert not report.ok and report.errors[0].rule_id == "evidence_exists"


async def test_validate_warns_and_fixes_deadline_from_text(session, meeting_with_transcript):
    p = proposal()
    report = await validate_proposal(session, meeting_with_transcript, INPUT, p)
    assert report.ok and any(c.rule_id == "deadline_consistent" and c.status == "warn" for c in report.checks)
    assert p.actions[0].deadline_date == date(2026, 10, 15)
    assert p.evidence[0].ref == "segment:1"


async def test_unknown_deadline_removes_invented_date(session, meeting_with_transcript):
    p = proposal(deadline_text="после совещания с подрядчиками", deadline_date=date(2026, 10, 15))
    report = await validate_proposal(session, meeting_with_transcript, INPUT, p)
    assert report.ok and p.actions[0].deadline_date is None


async def test_execute_and_verify_persist_action_items(session, meeting_with_transcript):
    p = proposal()
    results = await execute_actions(session, meeting_with_transcript, INPUT, p, {"a1": "run-1:a1"})
    report = await verify_outcome(session, meeting_with_transcript, INPUT, p, results)
    assert report.ok and results[0].result["deadline_date"] == "2026-10-15"


async def test_fingerprint_changes_on_text_and_speaker_rename(session, meeting_with_transcript):
    p = proposal()
    before = await fingerprint(session, meeting_with_transcript, INPUT, p)
    segment = await session.get(MeetingSegment, 1)
    segment.text += " changed"
    await session.flush()
    changed = await fingerprint(session, meeting_with_transcript, INPUT, p)
    assert changed != before
    speaker = await session.get(MeetingSpeaker, (meeting_with_transcript, "S1"))
    speaker.display_name = "New name"
    await session.flush()
    assert await fingerprint(session, meeting_with_transcript, INPUT, p) != changed


async def test_unknown_speaker_rejected(session, meeting_with_transcript):
    p = proposal(owner_speaker_id="S999")
    report = await validate_proposal(session, meeting_with_transcript, INPUT, p)
    assert not report.ok and any(c.rule_id == "owner_known" for c in report.errors)
    assert p.actions[0].owner_speaker_id == "S999"


async def test_known_giver_absent_from_evidence_is_cleared_without_changing_assignee(session, meeting_with_transcript):
    session.add(MeetingSpeaker(meeting_id=meeting_with_transcript, speaker_id="S2", display_name="Гульмира"))
    await session.flush()
    p = proposal(owner_speaker_id="S2")
    report = await validate_proposal(session, meeting_with_transcript, INPUT, p)
    assert report.ok
    assert p.actions[0].owner_speaker_id is None
    assert p.actions[0].owner_name == "Гульмира Сериковна"
    assert any(c.rule_id == "giver_matches_evidence" and c.status == "warn" for c in report.checks)


async def test_giver_present_in_cited_evidence_is_preserved(session, meeting_with_transcript):
    p = proposal(owner_speaker_id="S1")
    report = await validate_proposal(session, meeting_with_transcript, INPUT, p)
    assert report.ok and p.actions[0].owner_speaker_id == "S1"
    assert not any(c.rule_id == "giver_matches_evidence" and c.status == "warn" for c in report.checks)
