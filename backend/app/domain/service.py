import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contracts import (
    ActionResult,
    EvidenceRef,
    ExecutionError,
    ValidationCheck,
    ValidationReport,
    VerificationCheck,
    VerificationReport,
)
from app.core.serialization import jsonable
from app.domain import repo
from app.domain.models import ActionItem, Meeting, Protocol
from app.domain.schemas import CaseInput, ProtocolProposal
from app.speech.deadlines import resolve


def row_dict(row) -> dict:
    return {column.key: getattr(row, column.key) for column in row.__table__.columns}


async def load_case_view(session: AsyncSession, case_ref: str) -> dict[str, Any]:
    meeting = await repo.get_meeting(session, case_ref)
    protocol = await session.scalar(
        select(Protocol).where(Protocol.meeting_id == case_ref).order_by(Protocol.confirmed_at.desc()).limit(1)
    )
    items = (
        list(
            await session.scalars(
                select(ActionItem).where(ActionItem.protocol_id == protocol.id).order_by(ActionItem.id)
            )
        )
        if protocol
        else []
    )
    return jsonable(
        {
            "case_ref": meeting.id,
            "title": meeting.title,
            "description": "Стенограмма и поручения совещания",
            "status": meeting.status,
            "meeting_date": meeting.meeting_date,
            "duration_s": meeting.duration_s,
            "error": meeting.error,
            "meeting": row_dict(meeting),
            "speakers": [row_dict(s) for s in await repo.list_speakers(session, case_ref)],
            "segments": [row_dict(s) for s in await repo.list_segments(session, case_ref)],
            "protocol": row_dict(protocol) if protocol else None,
            "action_items": [row_dict(a) for a in items],
        }
    )


async def validate_proposal(
    session: AsyncSession, case_ref: str, case_input: CaseInput, proposal: ProtocolProposal
) -> ValidationReport:
    meeting = await repo.get_meeting(session, case_ref)
    segments = {s.id: s for s in await repo.list_segments(session, case_ref)}
    speakers = {s.speaker_id for s in await repo.list_speakers(session, case_ref)}
    checks = []
    if meeting.status != "ready":
        checks.append(
            ValidationCheck(
                rule_id="transcript_ready",
                label="Стенограмма готова",
                status="fail",
                message="Сначала распознайте запись",
            )
        )
    evidence = []
    for action in proposal.actions:
        refs = [f"segment:{sid}" for sid in action.source_segment_ids]
        valid = all(sid in segments for sid in action.source_segment_ids)
        checks.append(
            ValidationCheck(
                rule_id="evidence_exists",
                label="Цитата принадлежит совещанию",
                status="pass" if valid else "fail",
                message="Цитаты найдены" if valid else "Указан неизвестный сегмент стенограммы",
                action_id=action.action_id,
                refs=refs,
            )
        )
        known = action.owner_speaker_id is None or action.owner_speaker_id in speakers
        checks.append(
            ValidationCheck(
                rule_id="owner_known",
                label="Говорящий известен",
                status="pass" if known else "fail",
                message="Говорящий проверен" if known else "Неизвестный говорящий",
                action_id=action.action_id,
            )
        )
        cited_speakers = {segments[sid].speaker_id for sid in action.source_segment_ids if sid in segments}
        if known and action.owner_speaker_id is not None and action.owner_speaker_id not in cited_speakers:
            action.owner_speaker_id = None
            checks.append(
                ValidationCheck(
                    rule_id="giver_matches_evidence",
                    label="Поручивший подтверждён цитатой",
                    status="warn",
                    message="Указанный говорящий отсутствует в цитатах: поручивший оставлен неуказанным",
                    action_id=action.action_id,
                    refs=refs,
                )
            )
        normalized = resolve(action.deadline_text, meeting.meeting_date)
        changed = normalized != action.deadline_date
        action.deadline_date = normalized
        checks.append(
            ValidationCheck(
                rule_id="deadline_consistent",
                label="Срок проверен",
                status="warn" if changed else "pass",
                message="Дата приведена к произнесённому сроку; неизвестный срок оставлен пустым"
                if changed
                else "Срок согласован",
                action_id=action.action_id,
            )
        )
        named = bool(action.owner_name.strip())
        if not named:
            action.owner_name = "не назначен"
        checks.append(
            ValidationCheck(
                rule_id="owner_named",
                label="Ответственный указан",
                status="pass" if named else "warn",
                message="Имя указано" if named else "Ответственный не назначен",
                action_id=action.action_id,
            )
        )
        for sid in action.source_segment_ids:
            if sid in segments:
                evidence.append(EvidenceRef(kind="record", ref=f"segment:{sid}", note=segments[sid].text))
    proposal.evidence = list({e.ref: e for e in evidence}.values())
    return ValidationReport.from_checks(checks)


async def fingerprint(session: AsyncSession, case_ref: str, case_input: CaseInput, proposal: ProtocolProposal) -> str:
    meeting = await repo.get_meeting(session, case_ref)
    basis = {
        "meeting": row_dict(meeting),
        "segments": [row_dict(s) for s in await repo.list_segments(session, case_ref)],
        "speakers": [row_dict(s) for s in await repo.list_speakers(session, case_ref)],
    }
    return hashlib.sha256(json.dumps(jsonable(basis), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


async def snapshot(session: AsyncSession, case_ref: str, case_input: CaseInput) -> dict:
    view = await load_case_view(session, case_ref)
    return {"action_items": len(view["action_items"]), "protocol_exists": view["protocol"] is not None}


async def execute_actions(
    session: AsyncSession, case_ref: str, case_input: CaseInput, proposal: ProtocolProposal, action_keys: dict[str, str]
) -> list[ActionResult]:
    await session.get(Meeting, case_ref, with_for_update=True)
    report = await validate_proposal(session, case_ref, case_input, proposal)
    if not report.ok:
        raise ExecutionError("invalid_proposal", "Поручения не подтверждены стенограммой")
    protocol = Protocol(
        id=str(uuid.uuid4()), meeting_id=case_ref, run_id=None, summary=proposal.summary, decisions=proposal.decisions
    )
    session.add(protocol)
    await session.flush()
    results = []
    for action in proposal.actions:
        item = ActionItem(
            id=str(uuid.uuid4()),
            protocol_id=protocol.id,
            meeting_id=case_ref,
            action_key=action_keys[action.action_id],
            text=action.text,
            owner_name=action.owner_name,
            owner_speaker_id=action.owner_speaker_id,
            deadline_text=action.deadline_text,
            deadline_date=action.deadline_date,
            urgency=action.urgency,
            status="new",
            source_segment_ids=action.source_segment_ids,
        )
        session.add(item)
        await session.flush()
        results.append(
            ActionResult(
                action_id=action.action_id,
                type=action.type,
                summary=f"{action.text} — {action.owner_name}",
                result=jsonable(row_dict(item)),
            )
        )
    return results


async def verify_outcome(
    session: AsyncSession, case_ref: str, case_input: CaseInput, proposal: ProtocolProposal, results: list[ActionResult]
) -> VerificationReport:
    protocol_id = (
        results[0].result["protocol_id"]
        if results
        else await session.scalar(
            select(Protocol.id).where(Protocol.meeting_id == case_ref).order_by(Protocol.confirmed_at.desc()).limit(1)
        )
    )
    protocol = await session.get(Protocol, protocol_id) if protocol_id else None
    items = (
        list(await session.scalars(select(ActionItem).where(ActionItem.protocol_id == protocol_id))) if protocol else []
    )
    checks = [
        VerificationCheck(
            id="protocol_stored",
            label="Протокол сохранён",
            ok=protocol is not None
            and protocol.summary == proposal.summary
            and protocol.decisions == proposal.decisions,
            detail=str(protocol_id),
        ),
        VerificationCheck(
            id="action_count",
            label="Все поручения сохранены",
            ok=len(items) == len(proposal.actions) == len(results),
            detail=f"{len(items)} / {len(proposal.actions)}",
        ),
    ]
    for action, result in zip(proposal.actions, results, strict=False):
        item = next((a for a in items if a.id == result.result["id"]), None)
        checks.append(
            VerificationCheck(
                id=f"action_stored:{action.action_id}",
                label="Поручение проверено",
                ok=item is not None
                and bool(item.text.strip())
                and item.text == action.text
                and item.owner_name == action.owner_name
                and item.deadline_date == action.deadline_date
                and item.source_segment_ids == action.source_segment_ids,
                detail=action.text,
            )
        )
    return VerificationReport.from_checks(checks, f"Сохранено поручений: {len(items)}")
