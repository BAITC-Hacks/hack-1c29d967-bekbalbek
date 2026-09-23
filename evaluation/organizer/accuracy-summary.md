# Accuracy audit — 23 September 2026

Compared the two supplied MP3 files and reference Markdown protocols. SHA-256 confirms both audio files are byte-identical to the repository samples. Meeting 1 uses the last verified live-Qwen run `bae6867f-96c2-4a49-b7fc-64afd5915c39`; meeting 2 uses a new transcription and live-Qwen run `22a1cb44-3694-4b95-a54f-7bf44ae7fa46`. Model: `protokol-qwen3.5:4b` (16K context). The references were used for evaluation, not supplied to the extraction model. No product code was changed for this audit.

The application uses 2026-09-23 as meeting date. The reference documents do not establish that date. Week-only deadlines are converted to Friday by the current resolver; this is an application convention, not a uniquely spoken calendar day.

## Results

| Measure | Meeting 1 | Meeting 2 |
|---|---|---|
| Reference task groups | 10 | 6 |
| Generated actions | 11 | 8 |
| Groups with a corresponding output | 10/10 | 6/6 |
| Important task-level defects | Budget coordination assigned to the chair instead of Тимур; several scopes shortened | All six core groups covered; training and contract work reasonably split |
| Duplication | Legal follow-up split into two overlapping actions | No task duplicates found |
| Assignee names | 8/10 group names exact; Тимур patronymic variant; 1 wrong identity | All intended identities recognizable, but only Ерлан spelled correctly; four participant names distorted |
| Citation quality | Audit date and synchronization deadline missing from cited segments | Briefing linked to wrong statement; several deadlines absent from cited segments |
| Diarization labels | 5, matching the 5 reference speakers in count only | 6 vs 5 reference speakers; extra short fragment |

These are manually reviewed task-group counts, not a benchmark accuracy percentage. Group correspondence does not imply complete wording, correct owner, correct deadline, or supported citations. Matching dates to the reference is also insufficient where the recording/transcript contradicts the document.

## Most consequential findings

1. Meeting 1 budget coordination is assigned to **Асхат Ярланович**, although the reference assigns it to **Тимур Болатович**. The model mistakes a name being addressed for the assignee; incomplete upstream wording contributes.
2. The meeting 1 finance action names **Атараусская область**, while the reference says **Павлодарская область**. The differing location is already present in ASR, before Qwen. This audit has not independently listened to resolve that divergence.
3. Meeting 2 closing instructions differ from its reference table: supplier search becomes **a week, maximum ten days**, and contract revision has **no more than a week**. An independent local Whisper-medium pass over 187–206 seconds reproduces both phrases. This strongly suggests a reference/recording mismatch; it is not human acoustic verification.
4. Qwen keeps the earlier **two-week supplier deadline** and does not flag the later change. It also extends the contract-revision deadline to the notification task without clear support. The resolver leaves “не больше недели” and “за месяц” without calendar dates.
5. Existing validation proves that a citation was read and belongs to the meeting, but does not prove it supports every action field. The wrong briefing citation in meeting 2 passes those checks.
6. Giver/assignee confusion remains when both speakers appear in cited segments. Several segments merge multiple speaker turns, so label membership cannot establish who issued the instruction.

## Detailed evidence

- [Meeting 1 action-by-action review](accuracy-meeting-1.md)
- [Meeting 2 action-by-action review](accuracy-meeting-2.md)
- [Transcription and speaker review](accuracy-transcription.md)
- [Disputed meeting 2 closing audio, 187–206 seconds](meeting-2-disputed-deadlines.wav)
- [Independent local second transcription](meeting-2-deadlines-second-pass.txt)

No WER or diarization error rate was computed: there is no manually verified, time-aligned acoustic ground truth, and the supplied documents have material discrepancies. The product currently produces a useful draft, but assignees, scope, changing deadlines and evidence links require human review.
