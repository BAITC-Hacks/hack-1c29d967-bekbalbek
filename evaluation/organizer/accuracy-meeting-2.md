# Meeting 2 accuracy audit

Compared the complete supplied reference `Протокол_совещания№2.docx.md` with [accuracy-2-meeting.json](accuracy-2-meeting.json) and [accuracy-2-run.json](accuracy-2-run.json). Meeting date: 2026-09-23. Run: `22a1cb44-3694-4b95-a54f-7bf44ae7fa46`, model `protokol-qwen3.5:4b`, status `proposed`, 8 actions, 2 tool calls, 28.736 seconds. Audio duration recorded by the pipeline: 206.03125 seconds. This is a proposal audit, not a confirmation/export test. No human listening was performed in this audit. A second independent cached Whisper-medium CPU transcription of the closing 187–206 s clip, saved in `meeting-2-deadlines-second-pass.txt`, corroborates the material deadline differences in the primary ASR.

## Scoring method and result

Coverage is scored against the six reference task groups, allowing one group to split into distinct actions. Assignee identity is assessed separately from spelling. Spoken deadline fidelity is separate from deterministic date normalization. Evidence existence/read status does not establish semantic support.

- Core task-group coverage: **6/6**. Training is split into a5/a6 and contractor administration into a7/a8; these are useful splits, not duplicates.
- Assignees: **6/6 recognizable intended identities**, but only **1/6 group names correctly spelled** (Ерлан; its department-lawyer qualifier is omitted). The other names inherit ASR distortions.
- Gold deadline phrase semantics: **5/6 groups**. Group 6 incorrectly has a one-week phrase against a reference with no deadline. This is partly explained by ASR segment 44, with an additional unsupported extension to the notification task.
- Gold normalized date values: **6/6 group-level dates match**, taking a6 as the estimate deadline for group 5 and both a7/a8 for group 6. This overstates accuracy: group 6 matches null because the resolver cannot normalize the extra phrase, not because the model correctly retained an unspecified deadline. a5's separate one-month deadline also stays null.
- Core action text supported by its own cited segments: **7/8**; a4 cites an acknowledgement of a different task. Several other citations omit the deadline and named assignee context.
- Strict content rows (core task + correctly spelled assignee + reference deadline phrase semantics/date): **1/6**, group1. Fully complete groups additionally requiring cited evidence for the task/assignee/deadline: **0/6**; group1 lacks its deadline citation. These strict figures count name spelling errors separately from recognizable identity and should be reported alongside 6/6 semantic task recall, not substituted for it.
- Duplicated tasks: **0**. Wholly invented task bodies: **0** against the full reference/transcript. Wrong or unsupported field attribution remains material.
- Validation says `ok: true`, with no errors. This means structural/evidence-access checks passed; it does not mean the action details are fully grounded.

## Six gold groups

| Group | Reference task / assignee / deadline | Output | Assessment |
|---|---|---|---|
| 1 | Supplier claim; Ерлан, department lawyer; end of week → 2026-09-25 | a1; Ерлан; “до конца недели” → 2026-09-25; cites 25,26 | Core task, owner and date correct. Citation 25 requests a claim and 26 names the lawyer, but the actual assignment and deadline are in uncited 27. Giver S2 is wrong: S2 identifies the lawyer; S1 gives the instruction. |
| 2 | Alternative supplier for quotation; Ботагоз Нурлановна; two weeks → 2026-10-07 | a2; “Батагос Нурлановна”; “за две недели” → 2026-10-07; cites 25 | Core task and gold date recovered; wording omits quotation-stage qualification. Name misspelled by ASR. Citation supports 30% capacity but not assignee or deadline; those require 23/27. Final ASR segment 44 conflicts with this earlier deadline. Giver cleared to null conservatively. |
| 3 | Contractor meeting plus milestone schedule; Жандос Талгатович; current week → 2026-09-25 | a3; “Жан-Достолгатович”; “на этой неделе” → 2026-09-25; cites 29,30 | Core task and date correct. Owner name substantially distorted, but recognizable from context. Citation 29 supports the instruction and time; 30 is acceptance. S5 is the recipient, while S1 issues the instruction. |
| 4 | Briefing after contractor meeting; Жандос Талгатович; event-relative → null | a4; same distorted name; “по итогам совещания” → null; cites 30 | Task and unresolved event-relative deadline correct against the complete transcript, but cited 30 only says the meeting will be organized this week. The actual briefing instruction is in 31. Evidence link is semantically wrong. Giver S5 is also wrong. |
| 5 | Extra training groups/external trainer and budget estimate; Ерболат Мухтарович; estimate in one week → 2026-09-30 | a5 classes/trainer: “за месяц” → null, cites35; a6 estimate: “за неделю” → 2026-09-30, cites36; both “Ербалат Мухтарович” | Valid split covering the whole group. Estimate date correct; month-long backlog-clearance target is also spoken in35 but unsupported by resolver, so a5 loses normalized date. Name misspelled. a5 giver null; a6 S6 is supported as an explicit self-commitment, distinct from S1's initial instruction. |
| 6 | Contractor notice and updated contract terms; Салтанат Ерболовна; no stated deadline → null | a7 contract revision and a8 notice; “Салтанат Ербуловна”; both “не больше недели” → null; cite42,43 | Both task bodies recovered, no duplication. Name misspelled. The extra deadline differs from reference and is absent from cited42/43. ASR44 supplies a one-week deadline for contract revision only; propagating it to the notice is an extraction error. S7 accepts the tasks, while S1 gives the instructions. |

## Upstream discrepancies and extraction errors

ASR segment 44 (187.33–205.62 s) materially differs from the supplied reference's closing summary:

- Alternate supplier: ASR says “неделя максимум 10 дней”; reference says two weeks. Earlier ASR27 also says two weeks. a2 selects the earlier deadline without flagging the conflict. It matches the gold reference but cannot be called a faithful resolution of the observed transcript conflict.
- Contract revision: ASR says “не больше недели”; reference gives no deadline. a7 repeats the ASR-only phrase, so this discrepancy is not proof the LLM invented it. a8 additionally assigns the same deadline to the notification, which that ASR phrase does not explicitly cover.
- Names: Ботагоз becomes Батагос; Жандос Талгатович becomes “Дорога Сталгатович” earlier and “Жан-Достолгатович” in the close; Ерболат becomes Ербалат; Салтанат's patronymic varies between Ербуловна and Ерболовна. Qwen mostly propagates these spellings rather than recovering canonical identities.

The independent Whisper-medium pass also says “неделя, максимум 10 дней” for the supplier and “не больше недели” for contract revision. Agreement between two ASR models supports treating the gold table as stale relative to the closing audio instructions, rather than calling these phrases LLM inventions. This is corroborated transcription evidence, not a claim of human acoustic verification. a2’s two-week date matches the stale table but fails to reconcile the closing update; a7’s null date must not count as accurate audio extraction merely because the reference says no deadline. The resolver currently leaves “не больше недели” null, a known normalization limitation (a one-week bound from September23 would be September30).

## Evidence and speaker attribution

All eight actions cite existing segment ids that the run read. That is useful access provenance but insufficient semantic validation:

- a4 is linked to the wrong statement entirely; replace its citation with31 before presenting a grounded briefing instruction.
- a1/a2 need27 for the deadlines and assignment context; a7 needs44 to support its ASR-derived deadline. a8's one-week deadline is not explicitly supported for that task.
- Five of six non-null giver labels (a1,a3,a4,a7,a8) identify an acknowledger/recipient rather than the person issuing the instruction. a6 is a defensible self-commitment. a2/a5 are null after conservative validation.
- The membership-only giver guard misses these cases because a cited bundle contains the recipient's acknowledgement as well as the instruction. It cannot distinguish which cited speaker actually gave the task.
- Diarization exposes six labels for a reference with five named speakers. S3 contains only “Это системная” in segment39, apparently splitting the chair's sentence before S1 segment40. Several segments also merge question/answer or acceptance/instruction boundaries (27,28,31). This is transcript-level evidence of imperfect turn separation, not an independently verified voice identity count.

## Deadline interpretation cautions

The five-working-day clause in42 governs invoice submission after future work completion. It is **not** a meeting-relative due date for a7/a8; the model correctly did not turn it into 2026-09-30 or another fixed task deadline. The reference's post-contractor-meeting briefing is event-relative and should remain null rather than receiving an invented calendar date. If segment44 were absent, a7/a8 should have empty deadline text and null dates. If its contract-revision wording is accepted, it needs separate treatment from the notice and should not be reported as matching the reference's unspecified deadline.

## Practical verdict

The run covers the reference's six substantive task groups and is useful for human review. It is not ready for unattended confirmation: correct owner spellings, repair a4 and missing deadline evidence, review the conflicting supplier deadline, remove the unsupported notice deadline, and verify giver attribution. High task recall and six matching group-level date values must not be presented as full protocol accuracy. In particular, table-based date agreement is not audio-based date correctness when the gold omits closing updates corroborated by both recognition passes.
