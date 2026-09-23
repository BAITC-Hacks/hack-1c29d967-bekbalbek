from dataclasses import asdict
from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contracts import CaseNotFound
from app.domain.models import Meeting, MeetingSegment, MeetingSpeaker

if TYPE_CHECKING:
    from app.speech.align import SpokenSegment


async def get_meeting(session: AsyncSession, meeting_id: str) -> Meeting:
    row = await session.get(Meeting, meeting_id)
    if row is None:
        raise CaseNotFound(f"Unknown meeting '{meeting_id}'")
    return row


async def list_segments(session: AsyncSession, meeting_id: str) -> list[MeetingSegment]:
    rows = await session.scalars(
        select(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id).order_by(MeetingSegment.idx)
    )
    return list(rows)


async def list_speakers(session: AsyncSession, meeting_id: str) -> list[MeetingSpeaker]:
    rows = await session.scalars(
        select(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id).order_by(MeetingSpeaker.speaker_id)
    )
    return list(rows)


async def replace_transcript(
    session: AsyncSession, meeting_id: str, segments: list["SpokenSegment"], duration_s: float
) -> None:
    meeting = await get_meeting(session, meeting_id)
    await session.execute(delete(MeetingSegment).where(MeetingSegment.meeting_id == meeting_id))
    await session.execute(delete(MeetingSpeaker).where(MeetingSpeaker.meeting_id == meeting_id))
    for idx, segment in enumerate(segments):
        session.add(
            MeetingSegment(
                meeting_id=meeting_id,
                idx=idx,
                start_s=segment.start,
                end_s=segment.end,
                speaker_id=segment.speaker,
                language=segment.language,
                text=segment.text,
                words=[asdict(word) for word in segment.words],
            )
        )
    for speaker in sorted({segment.speaker for segment in segments}):
        session.add(MeetingSpeaker(meeting_id=meeting_id, speaker_id=speaker, display_name=speaker))
    meeting.duration_s = duration_s
    await session.flush()


async def set_status(session: AsyncSession, meeting_id: str, status: str, error: str | None = None) -> None:
    meeting = await get_meeting(session, meeting_id)
    meeting.status, meeting.error = status, error
    await session.flush()
