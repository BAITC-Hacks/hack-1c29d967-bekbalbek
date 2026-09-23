import uuid

from httpx import AsyncClient

from tests.api.conftest import wait_for_run

CASE = "m-sample-1"
BODY = {"case_ref": CASE, "goal": "Составь протокол.", "input": {"meeting_date": "2026-09-23"}}


async def start_run(client: AsyncClient, body: dict | None = None) -> dict:
    response = await client.post("/api/runs", json=body or BODY)
    assert response.status_code == 202, response.text
    await wait_for_run(client)
    return (await client.get(f"/api/runs/{response.json()['run']['id']}")).json()


async def test_health_should_report_status_without_secrets(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok" and body["database"] == "ok" and body["model"] == "scripted"
    assert body["api_key_configured"] is False and body["domain"]["key"] == "protokol"
    assert "sk-" not in response.text


async def test_domain_endpoints_should_expose_examples_and_case_views(client: AsyncClient) -> None:
    examples = (await client.get("/api/domain/examples")).json()["examples"]
    assert [e["expected_outcome"] for e in examples] == [
        "proposal_ready",
        "proposal_ready",
    ]
    view = await client.get(f"/api/domain/cases/{CASE}")
    assert view.status_code == 200 and len(view.json()["segments"]) == 3 and len(view.json()["speakers"]) == 1
    missing = await client.get("/api/domain/cases/nope")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "case_not_found"


async def test_should_validate_run_requests(client: AsyncClient) -> None:
    bad_input = await client.post("/api/runs", json={**BODY, "input": {"meeting_date": "soon"}})
    assert bad_input.status_code == 422
    unknown_case = await client.post("/api/runs", json={**BODY, "case_ref": "nope"})
    assert unknown_case.status_code == 404 and unknown_case.json()["error"]["code"] == "case_not_found"
    missing_goal = await client.post("/api/runs", json={"case_ref": CASE, "input": {}})
    assert missing_goal.status_code == 422


async def test_should_run_the_agent_in_the_background_and_expose_the_result(client: AsyncClient) -> None:
    created = await client.post("/api/runs", json=BODY)
    assert created.status_code == 202 and created.json()["run"]["status"] in {"queued", "analyzing"}
    await wait_for_run(client)

    detail = (await client.get(f"/api/runs/{created.json()['run']['id']}")).json()
    assert detail["run"]["status"] == "proposed" and detail["proposal"]["validation"]["ok"] is True
    assert detail["run"]["stats"]["tool_calls"] >= 2 and detail["snapshot_before"] is not None
    assert len(detail["messages"]) >= 5

    listed = (await client.get("/api/runs")).json()["runs"]
    assert listed[0]["id"] == detail["run"]["id"]
    assert (await client.get(f"/api/runs/{uuid.uuid4()}")).status_code == 404


async def test_should_list_and_stream_persisted_events_with_reconnect(client: AsyncClient) -> None:
    detail = await start_run(client)
    run_id = detail["run"]["id"]
    apply = await client.post(f"/api/runs/{run_id}/apply", json={"proposal_id": detail["proposal"]["id"], "version": 1})
    assert apply.status_code == 200, apply.text

    listed = (await client.get(f"/api/runs/{run_id}/events/list")).json()["events"]
    assert [e["id"] for e in listed] == list(range(1, len(listed) + 1))
    assert listed[-1]["type"] == "run_finished" and listed[-1]["run_status"] == "verified"

    async with client.stream("GET", f"/api/runs/{run_id}/events") as stream:
        assert stream.headers["content-type"].startswith("text/event-stream")
        text = "".join([chunk async for chunk in stream.aiter_text()]).replace("\r\n", "\n")
    assert "event: run_started" in text and "event: verification_finished" in text and f"id: {len(listed)}" in text

    async with client.stream("GET", f"/api/runs/{run_id}/events", params={"after": len(listed) - 2}) as stream:
        tail = "".join([chunk async for chunk in stream.aiter_text()]).replace("\r\n", "\n")
    assert f"id: {len(listed) - 2}\n" not in tail and f"id: {len(listed) - 1}\n" in tail

    async with client.stream(
        "GET", f"/api/runs/{run_id}/events", headers={"Last-Event-ID": str(len(listed) - 1)}
    ) as stream:
        last = "".join([chunk async for chunk in stream.aiter_text()]).replace("\r\n", "\n")
    assert last.count("id: ") == 1 and f"id: {len(listed)}" in last


async def test_should_apply_once_and_reject_duplicates_and_bad_versions(client: AsyncClient) -> None:
    detail = await start_run(client)
    run_id, proposal_id = detail["run"]["id"], detail["proposal"]["id"]

    wrong = await client.post(f"/api/runs/{run_id}/apply", json={"proposal_id": proposal_id, "version": 2})
    assert wrong.status_code == 409 and wrong.json()["error"]["code"] == "invalid_state"

    applied = await client.post(f"/api/runs/{run_id}/apply", json={"proposal_id": proposal_id, "version": 1})
    assert applied.status_code == 200
    assert applied.json()["application"]["status"] == "verified" and applied.json()["run"]["status"] == "verified"
    assert len(applied.json()["application"]["actions"]) == 3

    again = await client.post(f"/api/runs/{run_id}/apply", json={"proposal_id": proposal_id, "version": 1})
    assert again.status_code == 409 and again.json()["error"]["code"] == "duplicate_apply"

    view = (await client.get(f"/api/domain/cases/{CASE}")).json()
    assert len(view["action_items"]) == 3 and view["protocol"] is not None
    missing = await client.post(f"/api/runs/{uuid.uuid4()}/apply", json={"proposal_id": proposal_id, "version": 1})
    assert missing.status_code == 404


async def test_should_reject_stale_proposals_after_transcript_change(client: AsyncClient, session_factory) -> None:
    detail = await start_run(client)
    from sqlalchemy import delete

    from app.domain.models import MeetingSegment

    async with session_factory() as session, session.begin():
        await session.execute(delete(MeetingSegment).where(MeetingSegment.id == 1))

    rejected = await client.post(
        f"/api/runs/{detail['run']['id']}/apply", json={"proposal_id": detail["proposal"]["id"], "version": 1}
    )
    assert rejected.status_code == 409
    body = rejected.json()["error"]
    assert body["code"] == "stale_proposal" and body["details"]["fingerprint_changed"] is True
    after = (await client.get(f"/api/runs/{detail['run']['id']}")).json()
    assert after["proposal"]["status"] == "stale" and after["application"]["status"] == "rejected"


async def test_reset_should_restore_the_sample_dataset(client: AsyncClient) -> None:
    detail = await start_run(client)
    await client.post(
        f"/api/runs/{detail['run']['id']}/apply", json={"proposal_id": detail["proposal"]["id"], "version": 1}
    )
    reset = await client.post("/api/domain/reset")
    assert reset.status_code == 200 and reset.json()["seeded"]["meetings"] == 2
    view = (await client.get(f"/api/domain/cases/{CASE}")).json()
    assert view["action_items"] == [] and view["protocol"] is None


async def test_should_preserve_meeting_notes_as_a_different_input(client: AsyncClient) -> None:
    detail = await start_run(client, {**BODY, "input": {"meeting_date": "2026-09-23", "notes": "Уточнить сроки"}})
    baseline = await start_run(client)
    assert detail["run"]["input"]["notes"] == "Уточнить сроки"
    assert baseline["run"]["input"]["notes"] is None
    assert detail["run"]["status"] == "proposed" and baseline["run"]["status"] == "proposed"
    assert all(c["status"] != "fail" for c in detail["proposal"]["validation"]["checks"])


async def test_should_reject_oversized_request_bodies(client: AsyncClient) -> None:
    huge = {**BODY, "input": {"meeting_date": "2026-09-23", "notes": "x" * 1500}, "goal": "g" * 1500}
    padded = {**huge, "padding": "p" * (2 * 1024 * 1024)}
    response = await client.post("/api/runs", json=padded)
    assert response.status_code == 413 and response.json()["error"]["code"] == "payload_too_large"


async def test_should_reject_empty_speaker_names(client: AsyncClient) -> None:
    response = await client.patch(f"/api/domain/meetings/{CASE}/speakers/S1", json={"display_name": ""})
    assert response.status_code == 422
    assert (await client.get(f"/api/domain/cases/{CASE}")).status_code == 200


async def test_should_cap_sse_subscribers_per_run(client: AsyncClient) -> None:
    from app.core.events import MAX_SUBSCRIBERS_PER_RUN, TooManySubscribers

    detail = await start_run(client)
    bus = client.app.state.services.bus  # type: ignore[attr-defined]
    run_id = uuid.UUID(detail["run"]["id"])
    queues = []
    for _ in range(MAX_SUBSCRIBERS_PER_RUN):
        cm = bus.subscribe(run_id)
        queues.append((cm, await cm.__aenter__()))
    try:
        with __import__("pytest").raises(TooManySubscribers):
            async with bus.subscribe(run_id):
                pass
        response = await client.get(f"/api/runs/{run_id}/events/list")
        assert response.status_code == 200
    finally:
        for cm, _ in queues:
            await cm.__aexit__(None, None, None)
