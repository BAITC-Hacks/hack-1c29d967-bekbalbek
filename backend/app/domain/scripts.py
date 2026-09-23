"""Deterministic demo mode derives candidates only from returned transcript evidence."""

import json
import re
from datetime import date
from typing import Any

from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call

from app.speech.deadlines import resolve

_TASK = re.compile(
    r"подготов|разработ|представ|предостав|обеспеч|поруч|провест|соглас|проработ|провер|состав|направ|организ|отч[её]т|жауапты|дайында|тапсыр",
    re.IGNORECASE,
)
_ENUMERATION = re.compile(
    r"(?:^|(?<=[.!?;])\s+|\s+)(?:первое|второе|третье|четв[её]ртое|пятое|шестое|седьмое|восьмое|девятое|десятое)(?:[.:)]|\s)|(?:^|(?<=[.!?;])\s+|\n\s*)\d{1,2}[.)]\s+",
    re.IGNORECASE,
)
_NAME = r"[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүһі]+(?:\s+[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүһі]+){0,2}"


def _deadline(text: str, anchor: date) -> tuple[str, date] | None:
    # Try bounded phrases, longest first; the resolver rejects quantities and percentages.
    for match in re.finditer(r"\b(?:до|к|через|за|by|until|завтра|ертең)\b", text, re.IGNORECASE):
        tail = text[match.start():]
        tail = re.split(r"[,;!?—]|\.(?!\d)", tail, maxsplit=1)[0]
        tokens = tail.split()
        for length in range(min(len(tokens), 7), 0, -1):
            phrase = " ".join(tokens[:length]).rstrip('.')
            resolved = resolve(phrase, anchor)
            if resolved is not None:
                return phrase, resolved
    return None


def _actions(rows: list[dict], anchor: date) -> list[dict]:
    actions = []
    for row in rows:
        for quote in _ENUMERATION.split(row["text"]):
            quote = quote.strip(' .:;')
            if not quote or not _TASK.search(quote):
                continue
            deadline = _deadline(quote, anchor)
            if deadline is None:
                continue
            phrase, resolved = deadline
            explicit = re.search(r"\b(?i:ответственн(?:ый|ая|ые)|жауапты)\s*[:—-]?\s*(" + _NAME + r")", quote)
            address = re.match(r"^(" + _NAME + r"),", quote)
            name = explicit or address
            actions.append({
                "action_id": f"a{len(actions) + 1}", "type": "action_item",
                "text": quote[:500], "owner_name": name.group(1) if name else "не назначен",
                "owner_speaker_id": row["speaker"], "deadline_text": phrase,
                "deadline_date": resolved.isoformat(), "urgency": "средний",
                "source_segment_ids": [row["id"]],
            })
            if len(actions) == 3:
                return actions
    return actions


def _output(call, meeting_date: date):
    rows = []
    not_ready = False
    for item in call.input:
        if not isinstance(item, dict) or item.get("type") != "function_call_output":
            continue
        try:
            envelope = json.loads(item["output"])
        except (ValueError, TypeError, KeyError):
            continue
        if not envelope.get("ok"):
            not_ready = True
        data = envelope.get("data", {})
        if isinstance(data, dict) and "segments" in data:
            rows = data["segments"]
    if not_ready:
        return [
            assistant_message(
                json.dumps(
                    {
                        "outcome": "needs_input",
                        "message": "Сначала распознайте запись",
                        "proposal": None,
                        "missing_fields": [{"field": "transcript", "reason": "Стенограмма ещё не готова"}],
                        "blocking_constraints": [],
                    },
                    ensure_ascii=False,
                )
            )
        ]
    actions = _actions(rows, meeting_date)
    evidence = [{"kind": "record", "ref": f"segment:{action['source_segment_ids'][0]}", "note": action["text"]} for action in actions]
    summary = "Демонстрационный режим: выбраны цитаты с указанием срока; проверьте поручения и ответственных."
    output = {
        "outcome": "proposal_ready",
        "message": summary if actions else "В стенограмме не найдены поручения с явным сроком.",
        "proposal": {
            "summary": summary,
            "actions": actions,
            "decisions": [],
            "evidence": evidence,
            "assumptions": ["Демонстрационный алгоритм выбирает не более трёх цитат с предлогом срока"],
            "expected_effects": ["Поручения доступны для проверки"],
        },
        "missing_fields": [],
        "blocking_constraints": [],
    }
    return [assistant_message(json.dumps(output, ensure_ascii=False))]


def auto_script(case_ref: str, case_input: dict[str, Any]) -> ScriptedModel:
    anchor = date.fromisoformat(case_input["meeting_date"])
    return ScriptedModel(
        [
            [function_call("get_meeting", {}, call_id="meeting")],
            [function_call("read_transcript", {"offset": 0, "limit": 0}, call_id="transcript")],
            ModelStep.respond(lambda call: _output(call, anchor)),
        ]
    )


SCRIPTS = {"auto": lambda: auto_script("m-sample-1", {"meeting_date": "2026-09-23"})}
