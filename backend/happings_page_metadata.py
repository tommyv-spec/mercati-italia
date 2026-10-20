"""Scoped editorial dates for Happings pages; never market freshness.

These facts describe the publisher's document. A publication/modification
timestamp is not an observation of an individual market, nor a calendar date.
Only head metadata and a WebPage whose URL is the observed final URL are read.
The small envelope is reconstructible from its retained dated statements.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

SCOPE = "editorial_page_only_not_market_verification"
MAX_STATEMENTS = 32
MAX_JSONLD_BYTES = 200_000
PROPERTIES = {
    "article:published_time": "published_at",
    "article:modified_time": "modified_at",
    "WebPage.datePublished": "published_at",
    "WebPage.dateModified": "modified_at",
}


def _page_url(value):
    if not isinstance(value, str) or len(value) > 1000:
        return False
    try:
        parsed = urlsplit(value)
        return bool(parsed.scheme == "https" and parsed.hostname == "www.happings.com"
                    and not parsed.username and not parsed.password
                    and parsed.port in (None, 443) and not parsed.query and not parsed.fragment
                    and re.fullmatch(r"/it/[a-z0-9/-]+(?:\.html)?", parsed.path))
    except ValueError:
        return False


def _stamp(value):
    """Normalize equivalent ISO timestamps while retaining original evidence."""
    if not isinstance(value, str) or not 1 <= len(value) <= 80:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            day = date.fromisoformat(value)
            return value, day
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value):
            return None
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        return stamp.isoformat(), stamp.date()
    except (ValueError, OverflowError):
        return None


def _from_statements(statements, *, final_url, read_on):
    if (not _page_url(final_url) or type(read_on) is not date
            or not isinstance(statements, list) or not 1 <= len(statements) <= MAX_STATEMENTS):
        return None
    unique = {}
    for item in statements:
        if (not isinstance(item, dict) or set(item) != {"property", "value", "url"}
                or item.get("property") not in PROPERTIES or item.get("url") != final_url
                or not isinstance(item.get("value"), str) or len(item["value"]) > 80):
            return None
        unique[(item["property"], item["value"])] = deepcopy(item)
    statements = [unique[key] for key in sorted(unique)]
    result = {"schema": 1, "scope": SCOPE, "url": final_url,
              "published_at": None, "modified_at": None,
              "evidence": statements, "conflicts": []}
    dates = {}
    for field in ("published_at", "modified_at"):
        values, issues = {}, []
        for item in statements:
            if PROPERTIES[item["property"]] != field:
                continue
            stamp = _stamp(item["value"])
            if stamp is None:
                issues.append({"field": field, "code": "invalid_editorial_date",
                               "value": item["value"]})
            elif stamp[1] > read_on:
                issues.append({"field": field, "code": "future_editorial_date",
                               "value": item["value"]})
            else:
                values[stamp[0]] = stamp[1]
        if len(values) > 1:
            issues.append({"field": field, "code": "conflicting_editorial_dates",
                           "values": sorted(values)})
        if not issues and len(values) == 1:
            result[field] = next(iter(values))
            dates[field] = next(iter(values.values()))
        # A bad value is not silently overruled by a second convenient value.
        result["conflicts"].extend(issues)
    if dates.get("published_at") and dates.get("modified_at"):
        published, modified = result["published_at"], result["modified_at"]
        # Both complete timestamps were normalized to UTC above. A date-only
        # statement has no time of day, so compare only days in that case.
        reversed_order = (datetime.fromisoformat(modified) < datetime.fromisoformat(published)
                          if "T" in published and "T" in modified else
                          dates["modified_at"] < dates["published_at"])
        if reversed_order:
            result["conflicts"].append({"field": "modified_at", "code": "modification_precedes_publication"})
            result["modified_at"] = None
    return result


def clean_page_metadata(value, *, final_url, read_on):
    """Require exact scoped reconstruction, including conflicts and nulls."""
    if not isinstance(value, dict):
        return None
    expected = _from_statements(value.get("evidence"), final_url=final_url, read_on=read_on)
    return expected if expected is not None and expected == value else None


class _HeadMetadata(HTMLParser):
    def __init__(self, final_url):
        super().__init__(convert_charrefs=True)
        self.final_url = final_url
        self.in_head = False
        self.head_seen = False
        self.body_seen = False
        self.in_script = False
        self.script = []
        self.script_bytes = 0
        self.statements = []
        self.overflow = False

    def _add(self, prop, value):
        if not isinstance(value, str):
            return
        if len(value) > 80 or len(self.statements) >= MAX_STATEMENTS:
            self.overflow = True
            return
        self.statements.append({"property": prop, "value": value, "url": self.final_url})

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head" and not self.head_seen and not self.body_seen:
            self.in_head = self.head_seen = True
        if tag in {"body", "footer"}:
            self.in_head = False
            self.body_seen = True
        if not self.in_head:
            return
        if tag == "meta" and attrs.get("property") in {"article:published_time", "article:modified_time"}:
            self._add(attrs["property"], attrs.get("content"))
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.in_script = True
            self.script = []
            self.script_bytes = 0

    def handle_data(self, data):
        if self.in_head and self.in_script:
            self.script_bytes += len(data.encode("utf-8"))
            if self.script_bytes <= MAX_JSONLD_BYTES:
                self.script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.in_script:
            self.in_script = False
            if self.script_bytes > MAX_JSONLD_BYTES:
                self.overflow = True
                return
            try:
                data = json.loads("".join(self.script))
            except (ValueError, RecursionError):
                return
            queue = data if isinstance(data, list) else [data]
            if len(queue) > 100:
                self.overflow = True
            # Only WebPage, not Article/Event/Organization dates, is scoped by
            # its own exact URL. A canonical tag is not an observed redirect.
            for item in queue[:100]:
                if not isinstance(item, dict):
                    continue
                nodes = [item] + (item["@graph"] if isinstance(item.get("@graph"), list) else [])
                if len(nodes) > 100:
                    self.overflow = True
                for node in nodes[:100]:
                    if not isinstance(node, dict):
                        continue
                    types = node.get("@type")
                    types = types if isinstance(types, list) else [types]
                    if "WebPage" not in types or node.get("url") != self.final_url:
                        continue
                    for key in ("datePublished", "dateModified"):
                        self._add("WebPage." + key, node.get(key))
        elif tag == "head":
            self.in_head = False
            self.in_script = False


def parse_page_metadata(html, *, final_url, read_on):
    if not isinstance(html, bytes) or not _page_url(final_url) or type(read_on) is not date:
        raise ValueError("Page metadata requires exact URL, HTML bytes and observation date")
    parser = _HeadMetadata(final_url)
    parser.feed(html.decode("utf-8-sig", errors="replace"))
    parser.close()
    if parser.overflow:
        return None
    return _from_statements(parser.statements, final_url=final_url, read_on=read_on)
