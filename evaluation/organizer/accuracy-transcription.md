# Transcription and reference coverage audit

Audit date: 2026-09-23. Inputs: the supplied `Протокол_совещания№1.docx.md` and `Протокол_совещания№2.docx.md`, compared with live REST transcripts saved beside this report as `accuracy-transcript-1.json` and `accuracy-transcript-2.json`. Both meetings had status `ready`. Audio hashes were checked separately by the lead and match the supplied recordings. This review does not run recognition again or change product data.

The reference documents are narrative transcripts plus summaries, not timestamped, independently checked acoustic annotations. Differences below are **observed reference/transcript divergences**, not proven recognition mistakes: the recording itself may differ from the reference. No WER, DER, speaker identification accuracy, or exhaustive action recall is claimed. The older `asr-2.json` was inspected preliminarily but is not the basis of the findings below; all segment IDs and quotations below come from the live REST snapshots.

## Meeting 1: chemistry and safety

22 aligned segments, 5 speaker labels (`S1`, `S2`, `S4`, `S5`, `S6`), all labelled Russian. The supplied reference identifies five named participants. Matching label count does not establish correct attribution; labels remain unnamed in the API.

| Field | Reference | Live transcript evidence | Assessment |
|---|---|---|---|
| Investment owner | Тимур Болатович | Segment 3: `Тимур Булатович`; segment 8: `Тимур Балатович` | Inconsistent patronymic already present before LLM extraction. |
| Chairman | Асхат Ерланович | Segment 17: `Асхат Ярланович` | Spelling divergence already present upstream. |
| Other names | Гульмира Сериковна, Айнур Каировна, Нурлан Сагатович | Preserved repeatedly, e.g. segments 1, 6, 8, 14–21 | These names are available to the extractor. |
| Modernization location | Павлодарская область | Segment 4: `Атраусской области`; segment 8: `Атараусской области` | Important location divergence already in ASR text. Павлодар remains in the incident and later investment discussion, so the transcript is internally inconsistent. |
| Operational numbers | 71% loading, 8% logistics losses, 60% project readiness, 11 sites | Segments 2, 4, 13 preserve these values | Numeric content present; spacing and numeral formatting differ harmlessly. |
| First five assignment dates | 15 Oct; 26 Sep; 30 Sep; 30 Sep; 20 Oct | All present in segment 8, with the corresponding assignments and named owners/department | No upstream date omission for this group. |
| Contractor investigation | Гульмира, Friday, personal report, possible termination | Segment 12 has Friday, investigation and termination; personal reporting and the full explanation are absent | A shortened action downstream may reflect upstream omission/reference mismatch. |
| Audit negotiation | Two weeks proposed, rejected, three weeks accepted; final report 15 Oct | Segments 14–16 retain the negotiation and explicit date | Correct final deadline is available. Choosing the initial two weeks would be an extraction error. |
| Audit scope | All gas-leak detectors and PPE at all 11 sites | Segment 13 has `11 площадок`; segment 14 only `Мне нужен полный аудит`; segment 16 says report for each site | The full specific detector/PPE scope is absent from this portion of ASR; do not invent it solely from the reference. |
| Budget coordination | Тимур with Нурлан, this week | Segment 17 proposes synchronization; segment 18 says `с Нурланом Сагатовичем на этой неделе, не задваивайте бюджет` | The direct address to Тимур and part of the instruction are missing in ASR. Correct owner requires discourse reasoning from surrounding turns. |
| Training | Нурлан, next week | Segment 20 preserves the name, next week and real knowledge checks | Available to extraction; all-sites scope is less explicit than in the reference. |
| Legal conclusion | Айнур, Wednesday | Segment 20 mentions Айнур/material responsibility; segment 21 says `Запрошу у юристов заключение. К среде будет ответ` | Deadline and legal follow-up are present, spanning two segments. |
| Final recap | Reference repeats owners and dates | Segment 22 only has a short closing | An extractor cannot recover the reference's detailed recap from this final segment. |

### Attribution and segmentation risks

- Segment 5 (56.05–58.03, S5) combines the end of the investment speaker's sentence and `Это`, the chairman's next response. Boundary is inside a sentence/turn.
- Segment 9 (148.90–157.09, S5) combines incident explanation with the chairman's question `Как это возможно?`; segment 10 (S1) also includes a response about non-execution of the schedule.
- Segment 12 (170.03–186.88, S1) includes instruction, `Хорошо, сделаю`, a new question, and the start of the answer. A single label covers multiple conversational roles.
- Segment 15 (194.12–198.98, S5) includes the two-week objection and `Хорошо, три`; segment 16 (S1) continues `недели...`. The accepted three-week deadline crosses the speaker boundary.
- Segment 19 (219.93–228.48, S6) starts with the investment participant's acknowledgment and continues with the training question attributed to Айнур in the reference.
- Segment 20 (229.02–262.53, S1) includes chairman questions/instructions plus `По плану, в марте`, `Сделаем. Отчитаюсь...`, replies attributed to Нурлан in the reference. Evidence cites a real segment, but that does not establish that every word in it was spoken by S1.

These are concrete collapsed/split-turn examples, not a measured diarization error rate. No acoustic gold was supplied.

### Upstream versus extraction examples from the saved protocol snapshot

The sample-1 REST snapshot also contained confirmed protocol `82f44232-8623-4288-8d33-597012bf849d`; these examples describe that snapshot only, not every later model run.

- `Атараусской области` and `Тимур Булатович` in its finance action reflect variants already in transcript segments 3/8; the extractor did not originate those spellings.
- Its synchronization action names `Асхат Ярланович` as responsible and cites segment 17. That segment starts by addressing Асхат, while the reference assigns the task to Тимур. The direct address was mistaken for ownership; upstream omitted wording complicates recovery, but the ASR did not explicitly assign responsibility to Асхат.
- Its audit action selects 15 October but cites only segments 13, 14, 15. The explicit `К 15 октября` is in segment 16. The text exists upstream, but this action's selected evidence does not contain the claimed explicit date.
- Separate material-responsibility and legal-conclusion actions both concern the final legal follow-up. Potential duplication arises during extraction, rather than from two independently stated reference assignments.

## Meeting 2: departmental reports

22 aligned segments, 6 speaker labels (`S1`, `S2`, `S3`, `S5`, `S6`, `S7`) versus five named speaking participants in the reference. Ерлан is mentioned as a lawyer, not shown speaking in the reference. All transcript segments are labelled Russian.

| Field | Reference | Live transcript evidence | Assessment |
|---|---|---|---|
| Industry owner | Ботагоз Нурлановна | Segments 23/44: `Батагос Нурлановны/Нурлановна` | Name divergence already in ASR. |
| Investments owner | Жандос Талгатович | Segment 27: `Дорога Сталгатович`; segment 44: `Жан -Достолгатович` | Severe name corruption/inconsistency before extraction. |
| Safety owner | Ерболат Мухтарович | Segments 31/44: `Ербалат Мухтарович` | Spelling divergence before extraction. |
| Contractor owner | Салтанат Ерболовна | Segment 37: `Салтанат Ербуловна`; segment 44 correct `Салтанат Ерболовна` | Correct form is present later; consolidation is possible. |
| Lawyer | Ерлан | Segments 26/27 preserve name and responsibility for claim | Explicit owner available. |
| Chairman | Данияр Серикович | Name is not spoken in the saved transcript | Do not infer the chairman's name solely from the external reference. |
| Numbers and location | 94%; 5–7 days; second supplier 30%; investment 68%; 3 projects; Павлодар; overdue certificates 12%; 3–4 contractors; 5 working days invoicing | Segments 24, 25, 28, 32/33, 41, 42 preserve these values | These facts are available; the 5-working-day invoicing condition is not the same as the action completion deadline. |
| Legal claim | Ерлан, end of week | Segment 27 states this directly | Preserved. |
| Alternative supplier | Ботагоз, two weeks | Segment 27: `за две недели`; closing segment 44: `неделя максимум 10 дней на поиск альтернативы` | Live transcript contains a later, conflicting deadline not in the reference. Selecting two weeks versus final 7–10 days needs explicit handling, not blind reference matching. |
| Contractor meeting | Жандос, current week | Segments 29/30: this week | Preserved despite corrupted owner name in preceding address. |
| Follow-up note | Жандос, after contractor meeting | Segment 31: `по итогам этого совещания короткую справку` | Relative event condition present; cannot normalize to a specific calendar date without guessing. |
| Additional training | Ерболат, estimate in one week; clear queue in a month | Segments 35/36 preserve month and estimate `За неделю дам смету подоб. Группам` | Time distinction available; `по доп. группам` is garbled but estimate intent survives. |
| Contractor notice and agreement revision | Салтанат; reference table says no deadline | Segments 42/43 carry task; segment 44 says `не больше недели` for agreement revision | Deadline is present in live transcript, absent from reference. It is not automatically a hallucination if the LLM reports one week for revision. Do not automatically apply that deadline to every notice-related subtask. |

### Attribution examples

- Segment 27 (44.79–55.80, S1) includes chairman instructions, Ботагоз's acknowledgment, and the next name-address. Segment 28 (S5) includes the chairman's question plus investment report and another question/answer.
- Segment 31 (92.95–98.37, S1) includes the chairman's request, `Сделаю`, and the next direct address.
- Segment 39 (164.25–164.87, S3) is only `Это системная`; segment 40 (S1) continues the same chairman question. This isolated extra label is an observable fragmentation example, not proof of a sixth real speaker.

## Interpretation

Recognition retains most operational numbers and the explicit dated assignments, but proper names, a key region name, and some instruction scope need human review. Speaker labels alone are insufficient for trustworthy giver attribution because multiple conversational turns are merged, and some sentences are split across labels. Several reference mismatches are already in the text supplied to the LLM. Conversely, choosing an addressee as an assignee, citing segments that omit the claimed deadline, or duplicating one legal follow-up are extraction/evidence issues when the relevant text is available elsewhere.

A numeric quality score requires a manually checked transcript of these exact recordings and timestamped speaker turns. The supplied narrative references should not be treated as perfect acoustic gold, especially where the live transcript's closing deadlines differ materially.
