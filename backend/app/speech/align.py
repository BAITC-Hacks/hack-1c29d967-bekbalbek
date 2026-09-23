import re
from dataclasses import dataclass, field

from app.speech.asr import Segment, Word
from app.speech.diarize import Turn

MIN_RUN = 3


@dataclass
class SpokenSegment:
    start: float
    end: float
    speaker: str
    language: str
    text: str
    words: list[Word] = field(default_factory=list)


def _speaker_for(word: Word, turns: list[Turn], previous: str | None) -> str:
    best, best_overlap = None, 0.0
    for t in turns:
        overlap = min(word.end, t.end) - max(word.start, t.start)
        if overlap > best_overlap:
            best, best_overlap = t.speaker, overlap
    if best is not None:
        return best
    if previous is not None:
        return previous
    nearest = min(turns, key=lambda t: min(abs(t.start - word.start), abs(t.end - word.end)))
    return nearest.speaker


def assign_speakers(segments: list[Segment], turns: list[Turn]) -> list[SpokenSegment]:
    if not turns:
        return [SpokenSegment(s.start, s.end, "S1", s.language, s.text, s.words) for s in segments]
    labelled: list[tuple[Word, str, str]] = []  # word, speaker, language
    previous = None
    for s in segments:
        words = s.words or [Word(s.start, s.end, s.text, 1.0)]
        for w in words:
            previous = _speaker_for(w, turns, previous)
            labelled.append((w, previous, s.language))
    # smoothing: a run shorter than MIN_RUN flanked by the same speaker on both sides joins that speaker
    speakers = [sp for _, sp, _ in labelled]
    runs: list[list[int]] = []
    for i, sp in enumerate(speakers):
        if runs and speakers[runs[-1][0]] == sp:
            runs[-1].append(i)
        else:
            runs.append([i])
    for k in range(1, len(runs) - 1):
        left, mid, right = runs[k - 1], runs[k], runs[k + 1]
        if len(mid) < MIN_RUN and speakers[left[0]] == speakers[right[0]]:
            for i in mid:
                speakers[i] = speakers[left[0]]
    out: list[SpokenSegment] = []
    for (w, _, lang), sp in zip(labelled, speakers, strict=True):
        if out and out[-1].speaker == sp and out[-1].language == lang and w.start - out[-1].end < 2.0:
            out[-1].end = max(out[-1].end, w.end)
            out[-1].text = re.sub(r"\s+([,.;:!?…])", r"\1", f"{out[-1].text} {w.text.strip()}").strip()
            out[-1].words.append(w)
        else:
            out.append(SpokenSegment(w.start, w.end, sp, lang, w.text, [w]))
    return out
