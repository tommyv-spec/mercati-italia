"""Bound complete publisher hours text without interpreting an opening calendar.

Seasonal clauses, closure lists and floor-specific hours are evidence too.
Never keep a prefix that might omit those qualifications. The same limit is
used by source readers, field receipts and the public export.
"""

MAX_HOURS_TEXT_LENGTH = 2000


class HoursTextTooLong(ValueError):
    """Hold the source/export before writing an incomplete hours statement."""


def preserve_hours_text(value, *, qualification=""):
    """Keep the entire text and its qualification, or reject it explicitly.

    Only outer whitespace is removed. This does not parse dates, collapse
    separate schedules, mark precision, or update the source's age.
    """
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    if qualification:
        text += " " + qualification.strip()
    if len(text) > MAX_HOURS_TEXT_LENGTH:
        raise HoursTextTooLong(
            "hours_text_too_long: " + str(len(text)) + " characters exceed "
            + str(MAX_HOURS_TEXT_LENGTH) + "; source/export held without truncation"
        )
    return text
