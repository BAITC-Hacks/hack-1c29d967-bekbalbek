from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import ServicesDep
from app.speech import guard

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(services: ServicesDep) -> dict:
    database = "ok"
    try:
        async with services.session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - health must never raise
        database = "error"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "model": services.settings.openai_model,
        "api_key_configured": services.settings.api_key_configured,
        "domain": {"key": services.domain.key, "title": services.domain.title},
        "active_runs": services.registry.active_count,
        "version": services.settings.app_version,
        "provenance": guard.status(),
        "llm_endpoint": services.settings.openai_base_url or "http://localhost:11434/v1",
        "stt_device": services.settings.stt_device,
        "models_present": (services.settings.models_dir / "kk-turbo-ct2" / "model.bin").exists(),
    }
