import io
import zipfile
from dataclasses import replace
from datetime import date

from app.domain.exports import ProtocolDocument, to_docx, to_pdf

DOC = ProtocolDocument(
    title="Совещание",
    meeting_date=date(2026, 9, 23),
    speakers=[("S1", "Асхат Ерланович")],
    summary="Обсудили химическую отрасль. Қазақша: Ә Ғ Қ Ң Ө Ұ Ү Һ І.",
    decisions=["Утвердить план"],
    action_items=[
        {
            "text": "Подготовить отчёт",
            "owner_name": "Гульмира Сериковна",
            "deadline_text": "15 октября",
            "deadline_date": "2026-10-15",
            "urgency": "высокий",
            "status": "new",
        }
    ],
    transcript=[{"t": "00:00", "speaker": "Асхат Ерланович", "text": "Коллеги, начинаем."}],
)


def test_pdf_is_valid_and_contains_cyrillic_font():
    data = to_pdf(DOC)
    assert data[:4] == b"%PDF" and b"DejaVu" in data
    assert data.rstrip().endswith(b"%%EOF")


def test_docx_contains_owner_and_deadline():
    data = to_docx(DOC)
    xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode()
    assert "Гульмира Сериковна" in xml and "15 октября" in xml
    assert "Ә Ғ Қ Ң Ө Ұ Ү Һ І" in xml


def test_pdf_handles_untrusted_markup_and_long_rows():
    long_doc = replace(
        DOC,
        title='<protocol> & "test"',
        summary="a < b & c > d",
        action_items=[{**DOC.action_items[0], "text": "Очень длинное поручение & <важно>. " * 400}],
    )
    assert to_pdf(long_doc).startswith(b"%PDF")
    xml = zipfile.ZipFile(io.BytesIO(to_docx(long_doc))).read("word/document.xml").decode()
    assert "&lt;protocol&gt;" in xml


def test_empty_protocol_exports():
    empty = replace(DOC, speakers=[], decisions=[], action_items=[], transcript=[])
    assert to_pdf(empty).startswith(b"%PDF")
    assert zipfile.is_zipfile(io.BytesIO(to_docx(empty)))


async def test_missing_meeting_or_unconfirmed_protocol_returns_404():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import pytest
    from fastapi import HTTPException

    from app.domain.exports import build_document

    session = AsyncMock()
    session.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        await build_document(session, "missing")
    assert missing.value.status_code == 404
    session.get.return_value = SimpleNamespace(id="m1")
    session.scalar.return_value = None
    with pytest.raises(HTTPException) as unconfirmed:
        await build_document(session, "m1")
    assert unconfirmed.value.status_code == 404
