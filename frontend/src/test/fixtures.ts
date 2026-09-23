import type { CaseView, ExampleCase, ProposalRecord, RunDetail, RunEvent, Run, Snapshot } from "../api/types";

// Synthetic API fixtures for UI tests; not recognition results or organizer golden references.
export const caseView: CaseView = {
  "case_ref": "m-sample-1",
  "title": "Развитие химической промышленности и ТБ",
  "description": "Стенограмма и поручения совещания",
  "status": "ready",
  "meeting_date": "2026-09-23",
  "duration_s": 274.3,
  "error": null,
  "meeting": {
    "id": "m-sample-1",
    "title": "Развитие химической промышленности и ТБ",
    "meeting_date": "2026-09-23",
    "audio_path": "/app/samples/sovechanie_1.mp3",
    "status": "ready",
    "error": null,
    "duration_s": 274.3,
    "language_hint": "auto",
    "created_at": "2026-09-23T10:02:11+05:00"
  },
  "speakers": [
    {
      "meeting_id": "m-sample-1",
      "speaker_id": "S1",
      "display_name": "Председатель"
    },
    {
      "meeting_id": "m-sample-1",
      "speaker_id": "S2",
      "display_name": "Айдос Б."
    },
    {
      "meeting_id": "m-sample-1",
      "speaker_id": "S3",
      "display_name": "Гульнара С."
    }
  ],
  "segments": [
    {
      "id": 101,
      "meeting_id": "m-sample-1",
      "idx": 0,
      "start_s": 0.4,
      "end_s": 6.8,
      "speaker_id": "S1",
      "language": "ru",
      "text": "Коллеги, начинаем. Первый вопрос — развитие химической промышленности.",
      "words": []
    },
    {
      "id": 102,
      "meeting_id": "m-sample-1",
      "idx": 1,
      "start_s": 7.1,
      "end_s": 15.9,
      "speaker_id": "S2",
      "language": "ru",
      "text": "Подготовить обновлённый план по химическому кластеру до пятницы.",
      "words": []
    },
    {
      "id": 103,
      "meeting_id": "m-sample-1",
      "idx": 2,
      "start_s": 16.2,
      "end_s": 21.0,
      "speaker_id": "S1",
      "language": "ru",
      "text": "Хорошо. Ответственный — департамент стратегии.",
      "words": []
    },
    {
      "id": 104,
      "meeting_id": "m-sample-1",
      "idx": 3,
      "start_s": 21.4,
      "end_s": 29.7,
      "speaker_id": "S3",
      "language": "kk",
      "text": "Қауіпсіздік техникасы бойынша есепті келесі аптаға дейін дайындаймыз.",
      "words": []
    },
    {
      "id": 105,
      "meeting_id": "m-sample-1",
      "idx": 4,
      "start_s": 30.0,
      "end_s": 36.5,
      "speaker_id": "S1",
      "language": "ru",
      "text": "Договорились. Следующий вопрос.",
      "words": []
    },
    {
      "id": 106,
      "meeting_id": "m-sample-1",
      "idx": 5,
      "start_s": 37.0,
      "end_s": 44.2,
      "speaker_id": "S2",
      "language": "ru",
      "text": "Ещё нужно согласовать бюджет на обучение персонала, срок не назову.",
      "words": []
    }
  ],
  "protocol": null,
  "action_items": []
};
export const confirmedCaseView: CaseView = {
  "case_ref": "m-sample-1",
  "title": "Развитие химической промышленности и ТБ",
  "description": "Стенограмма и поручения совещания",
  "status": "ready",
  "meeting_date": "2026-09-23",
  "duration_s": 274.3,
  "error": null,
  "meeting": {
    "id": "m-sample-1",
    "title": "Развитие химической промышленности и ТБ",
    "meeting_date": "2026-09-23",
    "audio_path": "/app/samples/sovechanie_1.mp3",
    "status": "ready",
    "error": null,
    "duration_s": 274.3,
    "language_hint": "auto",
    "created_at": "2026-09-23T10:02:11+05:00"
  },
  "speakers": [
    {
      "meeting_id": "m-sample-1",
      "speaker_id": "S1",
      "display_name": "Председатель"
    },
    {
      "meeting_id": "m-sample-1",
      "speaker_id": "S2",
      "display_name": "Айдос Б."
    },
    {
      "meeting_id": "m-sample-1",
      "speaker_id": "S3",
      "display_name": "Гульнара С."
    }
  ],
  "segments": [
    {
      "id": 101,
      "meeting_id": "m-sample-1",
      "idx": 0,
      "start_s": 0.4,
      "end_s": 6.8,
      "speaker_id": "S1",
      "language": "ru",
      "text": "Коллеги, начинаем. Первый вопрос — развитие химической промышленности.",
      "words": []
    },
    {
      "id": 102,
      "meeting_id": "m-sample-1",
      "idx": 1,
      "start_s": 7.1,
      "end_s": 15.9,
      "speaker_id": "S2",
      "language": "ru",
      "text": "Подготовить обновлённый план по химическому кластеру до пятницы.",
      "words": []
    },
    {
      "id": 103,
      "meeting_id": "m-sample-1",
      "idx": 2,
      "start_s": 16.2,
      "end_s": 21.0,
      "speaker_id": "S1",
      "language": "ru",
      "text": "Хорошо. Ответственный — департамент стратегии.",
      "words": []
    },
    {
      "id": 104,
      "meeting_id": "m-sample-1",
      "idx": 3,
      "start_s": 21.4,
      "end_s": 29.7,
      "speaker_id": "S3",
      "language": "kk",
      "text": "Қауіпсіздік техникасы бойынша есепті келесі аптаға дейін дайындаймыз.",
      "words": []
    },
    {
      "id": 105,
      "meeting_id": "m-sample-1",
      "idx": 4,
      "start_s": 30.0,
      "end_s": 36.5,
      "speaker_id": "S1",
      "language": "ru",
      "text": "Договорились. Следующий вопрос.",
      "words": []
    },
    {
      "id": 106,
      "meeting_id": "m-sample-1",
      "idx": 5,
      "start_s": 37.0,
      "end_s": 44.2,
      "speaker_id": "S2",
      "language": "ru",
      "text": "Ещё нужно согласовать бюджет на обучение персонала, срок не назову.",
      "words": []
    }
  ],
  "protocol": {
    "id": "p-7f3a",
    "meeting_id": "m-sample-1",
    "run_id": null,
    "summary": "Обсуждены развитие химического кластера и отчёт по технике безопасности.",
    "decisions": [
      "Утвердить обновление плана по химическому кластеру",
      "Подготовить отчёт по ТБ"
    ],
    "confirmed_at": "2026-09-23T10:31:40+05:00"
  },
  "action_items": [
    {
      "id": "ai-1",
      "protocol_id": "p-7f3a",
      "meeting_id": "m-sample-1",
      "action_key": "prop-1:a1",
      "text": "Подготовить обновлённый план по химическому кластеру",
      "owner_name": "Айдос Б.",
      "owner_speaker_id": "S2",
      "deadline_text": "до пятницы",
      "deadline_date": "2026-09-25",
      "urgency": "высокий",
      "status": "new",
      "source_segment_ids": [
        102,
        103
      ]
    },
    {
      "id": "ai-2",
      "protocol_id": "p-7f3a",
      "meeting_id": "m-sample-1",
      "action_key": "prop-1:a2",
      "text": "Подготовить отчёт по технике безопасности",
      "owner_name": "Гульнара С.",
      "owner_speaker_id": "S3",
      "deadline_text": "келесі аптаға дейін",
      "deadline_date": "2026-09-30",
      "urgency": "средний",
      "status": "new",
      "source_segment_ids": [
        104
      ]
    },
    {
      "id": "ai-3",
      "protocol_id": "p-7f3a",
      "meeting_id": "m-sample-1",
      "action_key": "prop-1:a3",
      "text": "Согласовать бюджет на обучение персонала",
      "owner_name": "не назначен",
      "owner_speaker_id": null,
      "deadline_text": "",
      "deadline_date": null,
      "urgency": "низкий",
      "status": "new",
      "source_segment_ids": [
        106
      ]
    }
  ]
};
const proposalFixture = {
  "id": "p-1",
  "run_id": "run-1",
  "version": 1,
  "status": "validated",
  "basis_fingerprint": "e3b0c442",
  "created_at": "2026-09-23T10:30:02+05:00",
  "content": {
    "summary": "Обсуждены развитие химического кластера и отчёт по технике безопасности.",
    "decisions": [
      "Утвердить обновление плана по химическому кластеру"
    ],
    "actions": [
      {
        "action_id": "a1",
        "type": "action_item",
        "text": "Подготовить обновлённый план по химическому кластеру",
        "owner_name": "Айдос Б.",
        "owner_speaker_id": "S2",
        "deadline_text": "до пятницы",
        "deadline_date": "2026-09-25",
        "urgency": "высокий",
        "source_segment_ids": [
          102,
          103
        ]
      },
      {
        "action_id": "a2",
        "type": "action_item",
        "text": "Подготовить отчёт по технике безопасности",
        "owner_name": "Гульнара С.",
        "owner_speaker_id": "S3",
        "deadline_text": "келесі аптаға дейін",
        "deadline_date": "2026-09-30",
        "urgency": "средний",
        "source_segment_ids": [
          104
        ]
      },
      {
        "action_id": "a3",
        "type": "action_item",
        "text": "Согласовать бюджет на обучение персонала",
        "owner_name": "не назначен",
        "owner_speaker_id": null,
        "deadline_text": "",
        "deadline_date": null,
        "urgency": "низкий",
        "source_segment_ids": [
          106
        ]
      }
    ],
    "evidence": [
      {
        "kind": "record",
        "ref": "segment:102",
        "note": "Подготовить обновлённый план по химическому кластеру до пятницы."
      },
      {
        "kind": "record",
        "ref": "segment:104",
        "note": "Қауіпсіздік техникасы бойынша есепті келесі аптаға дейін дайындаймыз."
      }
    ],
    "assumptions": [
      "Пятница = 2026-09-25 относительно даты совещания"
    ],
    "expected_effects": [
      "В протокол добавлено 3 поручения"
    ]
  },
  "validation": {
    "ok": true,
    "checks": [
      {
        "rule_id": "transcript_ready",
        "label": "Стенограмма готова",
        "status": "pass",
        "message": "",
        "action_id": null,
        "refs": [],
        "source": null
      },
      {
        "rule_id": "evidence_exists",
        "label": "Есть цитата",
        "status": "pass",
        "message": "",
        "action_id": "a1",
        "refs": [
          "segment:102"
        ],
        "source": null
      },
      {
        "rule_id": "owner_known",
        "label": "Ответственный найден",
        "status": "pass",
        "message": "",
        "action_id": "a1",
        "refs": [],
        "source": null
      },
      {
        "rule_id": "deadline_consistent",
        "label": "Срок согласован",
        "status": "warn",
        "message": "Дата уточнена по фразе «до пятницы»",
        "action_id": "a1",
        "refs": [],
        "source": null
      },
      {
        "rule_id": "evidence_exists",
        "label": "Есть цитата",
        "status": "pass",
        "message": "",
        "action_id": "a2",
        "refs": [
          "segment:104"
        ],
        "source": null
      },
      {
        "rule_id": "owner_named",
        "label": "Ответственный назначен",
        "status": "warn",
        "message": "Ответственный не назван в речи",
        "action_id": "a3",
        "refs": [],
        "source": null
      }
    ],
    "errors": []
  }
};
export const proposalRecord = proposalFixture as ProposalRecord;

export const examples: ExampleCase[] = [
  { id: "m-sample-1", title: caseView.title, description: "Запись совещания", expected_outcome: "proposal_ready",
    request: { case_ref: "m-sample-1", goal: "Составь протокол совещания.", input: { meeting_date: "2026-09-23" } } },
  { id: "m-sample-2", title: "Оперативное совещание по отчётам департаментов", description: "Запись совещания", expected_outcome: "proposal_ready",
    request: { case_ref: "m-sample-2", goal: "Подготовь протокол оперативного совещания.", input: { meeting_date: "2026-09-23" } } },
];
export function makeRun(overrides: Partial<Run> = {}): Run {
  return {
    id: "run-1", case_ref: "m-sample-1", goal: examples[0].request.goal, input: { meeting_date: "2026-09-23" },
    status: "proposed", outcome: "proposal_ready", model: "scripted:auto", max_turns: 12, error: null,
    stats: { duration_ms: 812, tool_calls: 4, usage: { requests: 5, input_tokens: 0, output_tokens: 0, total_tokens: 0 } },
    created_at: "2026-09-23T10:00:00Z", started_at: "2026-09-23T10:00:00Z", finished_at: "2026-09-23T10:00:05Z", updated_at: "2026-09-23T10:00:05Z",
    ...overrides,
  };
}
export const snapshotBefore: Snapshot = { action_items: 0, protocol_exists: false };
export const snapshotAfter: Snapshot = { action_items: 3, protocol_exists: true };
export const proposedDetail: RunDetail = {
  run: makeRun(), proposals: [proposalRecord], proposal: proposalRecord, needs_input: null, infeasible: null,
  application: null, snapshot_before: snapshotBefore, snapshot_after: null, messages: [],
};
export const needsInputDetail: RunDetail = {
  run: makeRun({ id: "run-2", case_ref: "m-sample-2", goal: examples[1].request.goal, input: {}, status: "needs_input", outcome: "needs_input" }),
  proposals: [], proposal: null,
  needs_input: { message: "Укажите дату совещания.", missing_fields: [{ field: "meeting_date", reason: "Дата нужна для определения сроков" }] },
  infeasible: null, application: null, snapshot_before: null, snapshot_after: null, messages: [],
};
export const infeasibleDetail: RunDetail = {
  run: makeRun({ id: "run-3", case_ref: "m-sample-3", status: "infeasible", outcome: "infeasible" }),
  proposals: [], proposal: null, needs_input: null,
  infeasible: { message: "Стенограмма отсутствует.", blocking_constraints: [{ rule_id: "transcript_ready", detail: "Сначала распознайте запись", refs: [] }] },
  application: null, snapshot_before: null, snapshot_after: null, messages: [],
};
function ev(id: number, type: string, run_status: RunEvent["run_status"], payload: Record<string, unknown>): RunEvent {
  return { id, run_id: "run-1", type, ts: `2026-09-23T10:00:${String(id).padStart(2, "0")}Z`, run_status, payload };
}

export const happyEvents: RunEvent[] = [
  ev(1, "run_started", "analyzing", { goal: "Составь протокол совещания.", case_ref: "m-sample-1", model: "scripted:auto", max_turns: 12 }),
  ev(2, "tool_started", "analyzing", { call_id: "c1", tool: "get_meeting", label: "Чтение совещания", arguments: {} }),
  ev(3, "tool_finished", "analyzing", { call_id: "c1", tool: "get_meeting", label: "Чтение совещания", duration_ms: 12, attempt: 1, summary: "6 field(s)", result: { segments: [] }, truncated: false }),
  ev(4, "tool_started", "analyzing", { call_id: "c2", tool: "read_transcript", label: "Чтение стенограммы", arguments: { skill: null, on_date: "bad" } }),
  ev(5, "tool_failed", "analyzing", { call_id: "c2", tool: "read_transcript", label: "Чтение стенограммы", duration_ms: 3, attempt: 1, will_retry: true, error: { code: "timeout", message: "slow" } }),
  ev(6, "tool_finished", "analyzing", { call_id: "c2", tool: "read_transcript", label: "Чтение стенограммы", duration_ms: 20, attempt: 2, summary: "2 field(s)", result: { speakers: [] }, truncated: true }),
  ev(7, "agent_output", "analyzing", { outcome: "proposal_ready", message: "Протокол готов.", missing_fields: [], blocking_constraints: [], action_count: 3 }),
  ev(8, "proposal_ready", "proposed", { proposal_id: "p-1", version: 1, summary: "Подготовлено 3 поручения.", action_count: 3, validation: proposalRecord.validation }),
  ev(9, "run_finished", "proposed", { outcome: "proposal_ready", status: "proposed", duration_ms: 812, tool_calls: 2, usage: { requests: 3, input_tokens: 0, output_tokens: 0, total_tokens: 0 } }),
];

export const applyEvents: RunEvent[] = [
  ev(10, "apply_started", "applying", { application_id: "app-1", proposal_id: "p-1", version: 1 }),
  ev(11, "action_applied", "applied", { action_id: "a1", type: "action_item", summary: "План по химическому кластеру сохранён", result: {} }),
  ev(12, "action_applied", "applied", { action_id: "a2", type: "action_item", summary: "Отчёт по безопасности сохранён", result: {} }),
  ev(13, "verification_finished", "verified", { ok: true, summary: "Поручения сохранены в протоколе", checks: [{ id: "action_stored:a1", label: "Поручение сохранено", ok: true, detail: "found" }] }),
  ev(14, "run_finished", "verified", { outcome: "proposal_ready", status: "verified", duration_ms: 300, tool_calls: 2, usage: null }),
];

export const failedEvents: RunEvent[] = [
  ev(1, "run_started", "analyzing", { goal: "g", case_ref: "m-sample-1", model: "scripted:auto", max_turns: 12 }),
  ev(2, "tool_started", "analyzing", { call_id: "c1", tool: "get_meeting", label: "Чтение совещания", arguments: {} }),
  ev(3, "tool_failed", "analyzing", { call_id: "c1", tool: "get_meeting", label: "Чтение совещания", duration_ms: 3, attempt: 1, will_retry: false, error: { code: "not_found", message: "No case" } }),
  ev(4, "run_failed", "failed", { code: "agent_error", message: "RuntimeError: provider down", stage: "analysis", details: {} }),
];
