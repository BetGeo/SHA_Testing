"""Small helpers for turning spoken/typed text into structured values."""
import re
from datetime import date, datetime, timedelta

from dateutil import parser as dateutil_parser

_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
    "half": 0.5, "quarter": 0.25,
}


def parse_date(text: str, today: date | None = None) -> date | None:
    today = today or date.today()
    text = text.strip().lower()
    if text in ("today", ""):
        return today
    if text == "yesterday":
        return today - timedelta(days=1)
    if text == "tomorrow":
        return today + timedelta(days=1)
    try:
        default_dt = datetime(today.year, today.month, today.day)
        return dateutil_parser.parse(text, default=default_dt, fuzzy=True).date()
    except (ValueError, OverflowError):
        return None


def parse_hours(text: str) -> float | None:
    text = text.strip().lower()
    if not text:
        return None

    # "an hour and a half", "half an hour"
    if "half an hour" in text and "and" not in text:
        return 0.5

    # numeric form: "2.5", "2.5 hours", "7"
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1))

    # "two and a half hours"
    m = re.match(r"(\w+)\s+and\s+a\s+half", text)
    if m and m.group(1) in _NUMBER_WORDS:
        return _NUMBER_WORDS[m.group(1)] + 0.5

    # bare number word: "seven hours"
    for word, value in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", text):
            return float(value)

    return None


_ORDINAL_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}

_YES_WORDS = ("yes", "yeah", "yep", "yup", "correct", "confirm", "sounds good", "right", "affirmative", "save it", "that's right")
_NO_WORDS = ("no", "nope", "nah", "cancel", "incorrect", "wrong", "negative", "don't save", "start over")


def parse_choice(text: str, count: int) -> int | None:
    """Map a spoken answer to a 0-based index among `count` options, or
    None if it's unclear or the speaker declined all of them."""
    text = text.strip().lower()
    if "none" in text:
        return None
    for word, value in _ORDINAL_WORDS.items():
        if word in text and 1 <= value <= count:
            return value - 1
    for word, value in _NUMBER_WORDS.items():
        if isinstance(value, int) and 1 <= value <= count and re.search(rf"\b{word}\b", text):
            return value - 1
    m = re.search(r"\b([1-9])\b", text)
    if m:
        idx = int(m.group(1))
        if 1 <= idx <= count:
            return idx - 1
    return None


def parse_yes_no(text: str) -> bool | None:
    text = text.strip().lower()
    if any(w in text for w in _NO_WORDS):
        return False
    if any(w in text for w in _YES_WORDS):
        return True
    return None


def parse_field_to_change(text: str) -> str | None:
    text = text.strip().lower()
    if "date" in text:
        return "date"
    if "project" in text or "code" in text:
        return "project"
    if "task" in text or "description" in text or "did" in text:
        return "task"
    if "hour" in text:
        return "hours"
    return None
