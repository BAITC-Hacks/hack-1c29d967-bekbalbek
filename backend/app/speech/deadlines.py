"""Resolve explicit Russian and Kazakh deadlines; leave unknown phrases unresolved."""

import re
from datetime import date, timedelta

_MONTHS = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
    'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
    'қаңтар': 1, 'ақпан': 2, 'наурыз': 3, 'сәуір': 4, 'мамыр': 5, 'маусым': 6,
    'шілде': 7, 'тамыз': 8, 'қыркүйек': 9, 'қазан': 10, 'қараша': 11, 'желтоқсан': 12,
}
_WEEKDAYS = (
    r'monday|понедельник(?:а|у)?|дүйсенбі(?:ге)?',
    r'tuesday|вторник(?:а|у)?|сейсенбі(?:ге)?',
    r'wednesday|сред(?:а|у|ы|е)|сәрсенбі(?:ге)?',
    r'thursday|четверг(?:а|у)?|бейсенбі(?:ге)?',
    r'friday|пятниц(?:а|у|ы|е)|жұма(?:ға)?',
    r'saturday|суббот(?:а|у|ы|е)|сенбі(?:ге)?',
    r'sunday|воскресень(?:е|я|ю)|жексенбі(?:ге)?',
)


def _end_of_week(anchor: date, weeks_ahead: int = 0) -> date:
    return anchor + timedelta(days=4 - anchor.weekday() + 7 * weeks_ahead)


def _date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def resolve(phrase: str, meeting_date: date) -> date | None:
    """Weekdays mean the next occurrence; week deadlines mean Friday."""
    p = ' '.join((phrase or '').casefold().split()).strip(' .')
    # Only a trailing annotation is accepted; arbitrary text must never become a date.
    p = re.sub(r'\s*\([^()]*\)$', '', p).strip()
    if not p:
        return None
    p = re.sub(r'^(?:до|к|в|на|через|за|by|until)\s+', '', p)
    p = re.sub(r'\s+(?:дейін|қарай)$', '', p)
    cardinal = {'один': '1', 'одна': '1', 'одну': '1', 'два': '2', 'две': '2', 'три': '3', 'четыре': '4', 'пять': '5', 'шесть': '6', 'семь': '7'}
    first, _, rest = p.partition(' ')
    if first in cardinal:
        p = cardinal[first] + ' ' + rest
    if p in {'неделю', 'неделя', 'день'}:
        p = '1 ' + p
    # Russian ordinal stems plus their calendar-date endings.
    stems = ('перв', 'втор', 'треть', 'четверт', 'пят', 'шест', 'седьм', 'восьм', 'девят', 'десят', 'одиннадцат', 'двенадцат', 'тринадцат', 'четырнадцат', 'пятнадцат', 'шестнадцат', 'семнадцат', 'восемнадцат', 'девятнадцат', 'двадцат')
    ordinal = {stem + ending: number for number, stem in enumerate(stems, 1) for ending in ('ое', 'ого', 'ому')}
    ordinal.update({'третье': 3, 'третьего': 3, 'третьему': 3, 'тридцатое': 30, 'тридцатого': 30, 'тридцатому': 30})
    parts = p.split()
    if parts and parts[0] in ordinal:
        p = str(ordinal[parts[0]]) + ' ' + ' '.join(parts[1:])
    elif len(parts) >= 3 and parts[0] in {'двадцать', 'тридцать'} and parts[1] in ordinal:
        day = (20 if parts[0] == 'двадцать' else 30) + ordinal[parts[1]]
        if ordinal[parts[1]] < 10 and day <= 31:
            p = str(day) + ' ' + ' '.join(parts[2:])
    m = re.fullmatch(r'(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?', p)
    if m:
        return _date(int(m[3] or meeting_date.year), int(m[2]), int(m[1]))
    m = re.fullmatch(r'(\d{1,2})(?:-?го)?\s+([^\W\d_]+)(?:\s+(\d{4})(?:\s*(?:г\.?|года|жыл))?)?', p)
    if m and m[2] in _MONTHS:
        month = _MONTHS[m[2]]
        year = int(m[3]) if m[3] else meeting_date.year + (month < meeting_date.month)
        return _date(year, month, int(m[1]))
    if p in {'завтра', 'ертең'}:
        return meeting_date + timedelta(days=1)
    if p in {'сегодня', 'бүгін'}:
        return meeting_date
    if p in {'следующая неделя', 'следующей недели', 'следующей неделе', 'келесі апта', 'келесі аптаның соңына'}:
        return _end_of_week(meeting_date, 1)
    if p in {'текущая неделя', 'текущей недели', 'текущей неделе', 'этой недели', 'этой неделе', 'конца недели', 'конец недели', 'осы апта', 'апта соңы'}:
        return _end_of_week(meeting_date)
    m = re.fullmatch(r'(\d+)\s*(недел(?:я|и|ь|ю)|апта|день|дня|дней|күн)', p)
    if m:
        days = int(m[1]) * (7 if m[2].startswith(('недел', 'апта')) else 1)
        try:
            return meeting_date + timedelta(days=days)
        except OverflowError:
            return None
    for weekday, pattern in enumerate(_WEEKDAYS):
        if re.fullmatch(pattern, p):
            return meeting_date + timedelta(days=(weekday - meeting_date.weekday()) % 7 or 7)
    return None
