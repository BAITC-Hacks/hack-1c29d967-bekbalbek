"""Evaluation runner. Default: scripted model (deterministic, no API key). EVAL_MODEL=live uses the configured OpenAI model."""

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.core.apply_service import ApplyError, ApplyService
from app.core.events import EventBus
from app.core.llm import configure_model_provider
from app.core.run_service import RunService
from app.db.base import Base
from app.domain import DOMAIN
from evals.scenarios import SCENARIOS, Scenario

RESULTS_DIR = Path(__file__).parent / "results"


async def ensure_database(url: str) -> None:
    raw = url.replace("postgresql+asyncpg://", "postgresql://")
    admin, _, name = raw.rpartition("/")
    conn = await asyncpg.connect(f"{admin}/postgres")
    try:
        if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name):
            await conn.execute(f'CREATE DATABASE "{name}"')
    finally:
        await conn.close()


async def run_scenario(scenario: Scenario, session_factory, settings: Settings, live: bool) -> dict[str, Any]:
    bus = EventBus(session_factory)
    async with session_factory() as session, session.begin():
        await DOMAIN.seed(session)
    factory = (lambda run: settings.openai_model) if live else (lambda run: DOMAIN.scripts[scenario.script]())
    runs = RunService(session_factory, DOMAIN, settings, bus, factory)
    applies = ApplyService(session_factory, DOMAIN, bus)

    started = time.perf_counter()
    run = await runs.create_run(
        case_ref=scenario.case_ref, goal=scenario.goal, input=scenario.input, **scenario.options
    )
    await runs.execute(run.id)
    detail = await runs.get_run_detail(run.id)
    apply_error: str | None = None
    second_apply_error: str | None = None
    if scenario.apply and detail.run.status == "proposed":
        if scenario.before_apply is not None:
            async with session_factory() as session, session.begin():
                await scenario.before_apply(session)
        try:
            await applies.apply(run.id, detail.proposal.id, detail.proposal.version)
        except ApplyError as exc:
            apply_error = exc.code
        if scenario.apply_twice:
            try:
                await applies.apply(run.id, detail.proposal.id, detail.proposal.version)
            except ApplyError as exc:
                second_apply_error = exc.code
        detail = await runs.get_run_detail(run.id)
    duration_ms = int((time.perf_counter() - started) * 1000)

    events = await bus.replay(run.id)
    async with session_factory() as session:
        state_ok = await scenario.final_state_ok(session, scenario.case_ref)
    violated = [
        c["rule_id"]
        for c in (
            detail.proposal.validation["errors"]
            if detail.proposal and detail.proposal.status in {"validated", "applied"}
            else []
        )
    ]
    verification = detail.application.verification if detail.application else None
    expected_error = scenario.expected_apply_error
    observed_error = second_apply_error if scenario.apply_twice else apply_error
    checks = {
        "status": detail.run.status == scenario.expected_status,
        "outcome": detail.run.outcome == scenario.expected_outcome,
        "apply_error": (observed_error == expected_error) if expected_error else observed_error is None,
        "run_error": (detail.run.error or {}).get("code") == scenario.expected_run_error
        if scenario.expected_run_error
        else detail.run.error is None,
        "event": any(e.type == scenario.expect_event for e in events) if scenario.expect_event else True,
        "verification": verification["ok"] if (scenario.apply and not expected_error) else True,
        "final_state": state_ok,
    }
    return {
        "scenario": scenario.name,
        "description": scenario.description,
        "success": all(checks.values()),
        "checks": checks,
        "status": detail.run.status,
        "outcome": detail.run.outcome,
        "constraints_violated": violated,
        "final_state_correct": state_ok,
        "duration_ms": duration_ms,
        "agent_duration_ms": detail.run.stats.duration_ms,
        "tool_calls": detail.run.stats.tool_calls,
        "tokens": (detail.run.stats.usage or {}).get("total_tokens"),
        "usage": detail.run.stats.usage,
        "events": len(events),
        "apply_error": apply_error,
        "second_apply_error": second_apply_error,
        "run_error": detail.run.error,
        "run_id": str(run.id),
    }


def print_report(results: list[dict[str, Any]], mode: str) -> None:
    header = f"{'scenario':30} {'ok':4} {'status':18} {'outcome':15} {'violations':12} {'state':6} {'ms':>7} {'tools':>5} {'tokens':>7}"
    print(f"\nEvaluation ({mode} model) — {len(results)} scenario(s)\n{header}\n{'-' * len(header)}")
    for r in results:
        print(
            f"{r['scenario']:30} {'PASS' if r['success'] else 'FAIL':4} {r['status']:18} {str(r['outcome']):15} "
            f"{','.join(r['constraints_violated']) or '-':12} {'ok' if r['final_state_correct'] else 'BAD':6} "
            f"{r['duration_ms']:7d} {r['tool_calls']:5d} {str(r['tokens'] if r['tokens'] is not None else '-'):>7}"
        )
        if not r["success"]:
            failed = [k for k, v in r["checks"].items() if not v]
            print(
                f"{'':30} failed checks: {', '.join(failed)}; run_error={r['run_error']}; apply_error={r['apply_error']}"
            )
    passed = sum(1 for r in results if r["success"])
    print(f"\n{passed}/{len(results)} scenarios passed (sample size n={len(results)}, one run each)")


async def main() -> int:
    live = os.environ.get("EVAL_MODEL", "scripted").lower() == "live"
    settings = Settings()
    if live and not settings.api_key_configured:
        print("EVAL_MODEL=live requires OPENAI_API_KEY", file=sys.stderr)
        return 2
    only = {name for name in os.environ.get("EVAL_ONLY", "").split(",") if name}
    url = os.environ.get("EVAL_DATABASE_URL", settings.database_url.rsplit("/", 1)[0] + "/agent_workspace_eval")
    await ensure_database(url)
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    configure_model_provider(settings)

    results = []
    for scenario in SCENARIOS:
        if only and scenario.name not in only:
            continue
        print(f"▶ {scenario.name}: {scenario.description}")
        results.append(await run_scenario(scenario, session_factory, settings, live))
    await engine.dispose()

    mode = "live:" + settings.openai_model if live else "scripted"
    print_report(results, mode)
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{'live' if live else 'scripted'}.json"
    out.write_text(
        json.dumps({"mode": mode, "generated_at": datetime.now(UTC).isoformat(), "results": results}, indent=2)
    )
    print(f"Saved {out}")
    return 0 if all(r["success"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
