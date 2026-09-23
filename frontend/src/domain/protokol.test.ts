import { caseView, proposalRecord, snapshotAfter, snapshotBefore } from "../test/fixtures";
import { protokolDomain } from "./protokol";

describe("meeting domain mapping", () => {
  it("should preserve global segment ids and resolve speaker display names", () => {
    const table = protokolDomain.tableFor(caseView);
    expect(table.columns).toEqual(["Время", "Говорящий", "Язык", "Реплика"]);
    expect(table.rows).toHaveLength(6);
    expect(table.rows[1]).toEqual({ id: "102", cells: ["00:07", "Айдос Б.", "RU", caseView.segments[1].text] });
  });
  it("should attach only each action's checks and source references", () => {
    const changes = protokolDomain.changesFor(proposalRecord.content, proposalRecord.validation, caseView);
    expect(changes).toHaveLength(3);
    expect(changes[0].label).toBe("Айдос Б. · 2026-09-25");
    expect(changes[0].rowId).toBe("102");
    expect(changes[0].checks.map((check) => check.status)).toEqual(["pass", "pass", "warn"]);
    expect(changes[1].checks.map((check) => check.status)).toEqual(["pass"]);
    expect(changes[1].evidence[0].ref).toBe("segment:104");
    expect(changes[2].label).toBe("не назначен · срок не указан");
  });
  it("should keep the assignee distinct from the speaker who gave the instruction", () => {
    const content = { ...proposalRecord.content, actions: [{ ...proposalRecord.content.actions[0], owner_name: "Ерлан", owner_speaker_id: "S1" }] };
    const change = protokolDomain.changesFor(content, proposalRecord.validation, caseView)[0];
    expect(change.label).toBe("Ерлан · 2026-09-25");
    expect(change.why).toContain("Поручил: Председатель");
  });
  it("should return the cited transcript quote with its timestamp", () => {
    expect(protokolDomain.describeEvidence({ kind: "record", ref: "segment:102", note: null }, caseView)).toEqual({
      title: "Айдос Б. · 00:07", source: "реплика №2", snippet: caseView.segments[1].text,
    });
  });
  it("should compare stored protocol and assignment counts", () => {
    expect(protokolDomain.beforeAfter(snapshotBefore, snapshotAfter)).toEqual([
      { label: "Поручений в протоколе", before: "0", after: "3" },
      { label: "Протокол подтверждён", before: "нет", after: "да" },
    ]);
    expect(protokolDomain.beforeAfter(null, snapshotAfter)).toEqual([]);
  });
  it("should merge a missing field while retaining the rest of the request", () => {
    expect(protokolDomain.applyMissingField({ notes: "keep" }, "meeting_date", "2026-09-23"))
      .toEqual({ notes: "keep", meeting_date: "2026-09-23" });
  });
  it("should bound long transcripts and disclose omitted rows", () => {
    const segments = Array.from({ length: 305 }, (_, index) => ({ ...caseView.segments[0], id: index + 1, idx: index }));
    const rows = protokolDomain.tableFor({ ...caseView, segments }).rows;
    expect(rows).toHaveLength(301);
    expect(rows.at(-1)?.cells[3]).toBe("ещё 5 реплик");
  });
});
