from datetime import date

import pytest

from app.speech.deadlines import resolve

MEETING = date(2026, 9, 23)  # Wednesday


@pytest.mark.parametrize(
    "phrase, expected",
    [
        ("15 октября", date(2026, 10, 15)),
        ("до 26 сентября", date(2026, 9, 26)),
        ("30 сентября", date(2026, 9, 30)),
        ("Пятница", date(2026, 9, 25)),
        ("до пятницы", date(2026, 9, 25)),
        ("Среда", date(2026, 9, 30)),
        ("Следующая неделя", date(2026, 10, 2)),
        ("Текущая неделя", date(2026, 9, 25)),
        ("До конца недели", date(2026, 9, 25)),
        ("2 недели", date(2026, 10, 7)),
        ("1 неделя (смета)", date(2026, 9, 30)),
        ("завтра", date(2026, 9, 24)),
        ("ертең", date(2026, 9, 24)),
        ("25.09", date(2026, 9, 25)),
        ("25.09.2026", date(2026, 9, 25)),
        ("Не указан", None),
        ("", None),
        ("После совещания с подрядчиками", None),
    ],
)
def test_resolve(phrase, expected):
    assert resolve(phrase, MEETING) == expected


@pytest.mark.parametrize(
    'phrase, expected',
    [
        ('дүйсенбі', date(2026, 9, 28)),
        ('сейсенбіге дейін', date(2026, 9, 29)),
        ('сәрсенбі', date(2026, 9, 30)),
        ('бейсенбі', date(2026, 9, 24)),
        ('жұмаға дейін', date(2026, 9, 25)),
        ('сенбі', date(2026, 9, 26)),
        ('жексенбі', date(2026, 9, 27)),
        ('послезавтра', None),
        ('31 сентября', None),
        ('31.09.2026', None),
        ('15 мая 2028 года', date(2028, 5, 15)),
        ('15 материалов', None),
        ('2 дневника', None),
        ('после совещания в пятницу', None),
        ('через 3 дня', date(2026, 9, 26)),
        ('2 апта', date(2026, 10, 7)),
        ('две недели', date(2026, 10, 7)),
        ('три недели', date(2026, 10, 14)),
        ('за неделю', date(2026, 9, 30)),
        ('через один день', date(2026, 9, 24)),
        ('к пятнадцатому октября', date(2026, 10, 15)),
        ('by Wednesday', date(2026, 9, 30)),
        ('until Friday', date(2026, 9, 25)),
        ('двадцать пятое сентября', date(2026, 9, 25)),
        ('тридцать первое сентября', None),
    ],
)
def test_conservative_resolution(phrase, expected):
    assert resolve(phrase, MEETING) == expected
