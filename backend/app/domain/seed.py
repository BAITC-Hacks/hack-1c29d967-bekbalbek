from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.models import Meeting

SAMPLES = [
    ("m-sample-1", "Развитие химической промышленности и ТБ", "sovechanie_1.mp3"),
    ("m-sample-2", "Оперативное совещание по отчётам департаментов", "sovechanie_2.mp3"),
]


async def seed(session: AsyncSession) -> dict[str, int]:
    for meeting_id, title, filename in SAMPLES:
        if await session.get(Meeting, meeting_id) is not None:
            continue
        session.add(
            Meeting(
                id=meeting_id,
                title=title,
                meeting_date=date(2026, 9, 23),
                audio_path=str(get_settings().samples_dir / filename),
                status="uploaded",
            )
        )
    await session.flush()
    return {"meetings": len(SAMPLES)}
