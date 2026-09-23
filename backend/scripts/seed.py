import asyncio

from app.config import get_settings
from app.db.engine import configure_database, dispose_engine
from app.domain import DOMAIN


async def main() -> None:
    session_factory = configure_database(get_settings().database_url)
    async with session_factory() as session, session.begin():
        counts = await DOMAIN.seed(session)
    await dispose_engine()
    print("Sample data loaded:", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    asyncio.run(main())
