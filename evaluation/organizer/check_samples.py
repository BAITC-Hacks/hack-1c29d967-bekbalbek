#!/usr/bin/env python3
"""Verify organizer files and task-table references locally (Python 3.10+)."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
HEADERS = ["Поручение", "Ответственный", "Срок"]


def read_tables(path: Path) -> list[list[list[str]]]:
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    tables = []
    for table in root.findall("./w:body/w:tbl", NS):
        rows = []
        for row in table.findall("w:tr", NS):
            cells = []
            for cell in row.findall("w:tc", NS):
                paragraphs = [
                    "".join(t.text or "" for t in p.findall(".//w:t", NS))
                    for p in cell.findall("w:p", NS)
                ]
                cells.append("\n".join(paragraphs).strip())
            rows.append(cells)
        tables.append(rows)
    return tables


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def check(source_dir: Path, reference_path: Path) -> list[str]:
    references = json.loads(reference_path.read_text(encoding="utf-8"))
    if references["schema_version"] != 1:
        return ["Unsupported reference schema version"]
    errors = []
    for sample in references["samples"]:
        sample_id = sample["id"]
        verified = {}
        for kind in ("protocol", "audio"):
            expected = sample["sources"][kind]
            path = source_dir / expected["filename"]
            if not path.is_file():
                errors.append(f"{sample_id}: missing {path.name}")
                continue
            if path.stat().st_size != expected["size_bytes"] or digest(path) != expected["sha256"]:
                errors.append(f"{sample_id}: size/hash mismatch for {path.name}")
                continue
            verified[kind] = path
        if "protocol" not in verified:
            continue
        tables = read_tables(verified["protocol"])
        actual = []
        for table_number, rows in enumerate(tables, start=1):
            if rows and rows[0] == HEADERS:
                for row_number, cells in enumerate(rows[1:], start=2):
                    actual.append((table_number, row_number, cells))
        expected_rows = [
            (action["source_table"], action["source_row"],
             [action["task"], action["owner"], action["due_text"]])
            for action in sample["actions"]
        ]
        if actual != expected_rows:
            errors.append(f"{sample_id}: task references differ from DOCX tables")
        elif "audio" in verified:
            print(f"PASS {sample_id}: both source hashes; {len(actual)} reference groups match DOCX")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="Directory containing the four organizer files")
    parser.add_argument("--references", type=Path, default=Path(__file__).with_name("references.json"))
    args = parser.parse_args()
    try:
        errors = check(args.source_dir, args.references)
    except (OSError, ValueError, KeyError, TypeError, BadZipFile, ET.ParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("Source/reference checks passed. ASR, diarization and model accuracy were NOT evaluated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
