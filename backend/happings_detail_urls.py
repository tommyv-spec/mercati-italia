"""Validate observed Happings event URLs, including safe UTF-8 WordPress slugs.

Never create a slug from event names or infer URLs. This strictly validates
a link already seen in HTML, a sitemap, or a trusted catalog.
"""
from __future__ import annotations
import re
import unicodedata
from urllib.parse import unquote_to_bytes, urlsplit

PLAIN_SLUG = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*")
ESCAPE = re.compile(r"%(?:[0-9a-f]{2})")
MAX_URL = 1000


def detail_url(value):
    if not isinstance(value, str) or not 30 <= len(value) <= MAX_URL:
        return False
    if any(ord(char) < 33 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or parsed.netloc != "www.happings.com"
                or parsed.query or parsed.fragment
                or not parsed.path.startswith("/it/happing/")
                or not parsed.path.endswith("/")):
            return False
        slug = parsed.path[len("/it/happing/"):-1]
        if not 1 <= len(slug) <= 650 or "/" in slug or "\\" in slug:
            return False
        if "%" not in slug:
            return bool(PLAIN_SLUG.fullmatch(slug))
        # Only canonical lowercase percent escapes already observed in a link.
        parts = re.split(r"(%[0-9a-f]{2})", slug)
        if any("%" in item and not ESCAPE.fullmatch(item) for item in parts):
            return False
        raw = unquote_to_bytes(slug)
        decoded = raw.decode("utf-8", "strict")
        if not 1 <= len(decoded) <= 240 or decoded.startswith((".", "-")):
            return False
        if any(char in "/\\%?#" or not char.isprintable()
               or unicodedata.category(char) in {"Cc", "Cf", "Cs"}
               for char in decoded):
            return False
        # Native WordPress slugs may contain accented letters, typographic
        # symbols and mathematical Unicode. They are never used as paths.
        return True
    except (ValueError, UnicodeError):
        return False
