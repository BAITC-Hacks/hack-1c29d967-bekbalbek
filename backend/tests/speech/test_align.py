from app.speech.align import assign_speakers
from app.speech.asr import Segment, Word
from app.speech.diarize import Turn


def seg(start, end, text):
    words = []
    t = start
    step = (end - start) / max(len(text.split()), 1)
    for w in text.split():
        words.append(Word(t, t + step, w, 0.9))
        t += step
    return Segment(start, end, text, "ru", words)


def test_words_take_the_turn_with_most_overlap_and_split_segments():
    segments = [seg(0.0, 4.0, "коллеги начинаем на повестке один вопрос гульмира сериковна вам слово")]
    turns = [Turn(0.0, 2.0, "S1"), Turn(2.0, 4.0, "S2")]
    out = assign_speakers(segments, turns)
    assert [o.speaker for o in out] == ["S1", "S2"]
    assert out[0].text.startswith("коллеги") and out[1].text.endswith("слово")


def test_short_run_between_same_speaker_is_smoothed():
    segments = [seg(0.0, 6.0, "a b c d e f g h i j k l")]
    turns = [Turn(0.0, 2.5, "S1"), Turn(2.5, 3.0, "S2"), Turn(3.0, 6.0, "S1")]
    out = assign_speakers(segments, turns)
    assert {o.speaker for o in out} == {"S1"}


def test_no_turns_means_single_speaker():
    out = assign_speakers([seg(0.0, 2.0, "тест тест")], [])
    assert len(out) == 1 and out[0].speaker == "S1"


def test_separate_punctuation_is_not_detached_from_words():
    segments = [seg(0, 4, 'Здравствуйте , коллеги !')]
    out = assign_speakers(segments, [Turn(0, 4, 'S1')])
    assert out[0].text == 'Здравствуйте, коллеги!'


def test_segment_without_words_still_gets_speaker():
    out = assign_speakers([Segment(2, 4, 'Сәлем, әріптестер!', 'kk')], [Turn(0, 5, 'S2')])
    assert out[0].speaker == 'S2'
    assert out[0].text == 'Сәлем, әріптестер!'
    assert out[0].language == 'kk'


def test_nearest_turn_covers_initial_gap_then_previous_speaker_covers_gap():
    segments = [seg(0, 1, 'first'), seg(3, 4, 'last')]
    out = assign_speakers(segments, [Turn(1, 2, 'S2')])
    assert all(s.speaker == 'S2' for s in out)


def test_language_boundary_is_preserved():
    out = assign_speakers(
        [Segment(0, 1, 'Сәлем!', 'kk'), Segment(1, 2, 'Привет!', 'ru')],
        [Turn(0, 2, 'S1')],
    )
    assert [s.language for s in out] == ['kk', 'ru']
