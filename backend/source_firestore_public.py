#!/usr/bin/env python3
"""Read-only one-time Firestore bootstrap using public-read security rules.

Queries ONLY the six market categories via an indexed IN query. Does not scan
sagra/carnevale records or write to Firebase. Use only for initial migration;
the live website reads versioned Cloudflare Pages static assets afterwards.

Docs: https://firebase.google.com/docs/firestore/use-rest-api
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

CATEGORIES = [
    "alimentare", "antiquariato", "vintage_abbigliamento",
    "usato", "artigianato", "misto",
]
QUERY_URL = (
    "https://firestore.googleapis.com/v1/projects/{project}"
    "/databases/(default)/documents:runQuery"
)


def value_from_firestore(value: dict):
    if not isinstance(value, dict):
        return None
    if "stringValue" in value:
        return value["stringValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "booleanValue" in value:
        return bool(value["booleanValue"])
    if "timestampValue" in value:
        return value["timestampValue"]
    if "nullValue" in value:
        return None
    if "geoPointValue" in value:
        return value["geoPointValue"]
    if "arrayValue" in value:
        return [value_from_firestore(v) for v in value["arrayValue"].get("values", [])]
    if "mapValue" in value:
        return {key: value_from_firestore(v) for key, v in value["mapValue"].get("fields", {}).items()}
    return None


def convert_response(results: list) -> list[dict]:
    records = []
    for result in results:
        if not isinstance(result, dict) or "document" not in result:
            continue
        d = result["document"]
        row = {key: value_from_firestore(v) for key, v in d.get("fields", {}).items()}
        row.setdefault("slug", d["name"].rsplit("/", 1)[-1])
        records.append(row)
    return records


def _post_json(url: str, payload: dict, max_bytes=25_000_000):
    request = Request(
        url, method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "User-Agent": "MercatiItaliaStaticBootstrap/1.0"},
    )
    try:
        with urlopen(request, timeout=40) as response:
            body = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise ValueError("Firestore read failed (HTTP " + str(exc.code) + ")") from None
    if len(body) > max_bytes:
        raise ValueError("Firestore response exceeded memory safety limit")
    return json.loads(body)


def _market_query(limit=None, after=None):
    query = {
        "from": [{"collectionId": "mercati"}],
        "where": {
            "fieldFilter": {
                "field": {"fieldPath": "categoria"}, "op": "IN",
                "value": {"arrayValue": {
                    "values": [{"stringValue": category} for category in CATEGORIES]
                }},
            }
        },
        "orderBy": [{"field": {"fieldPath": "__name__"}, "direction": "ASCENDING"}],
    }
    if limit is not None:
        query["limit"] = limit
    if after:
        query["startAt"] = {
            "values": [{"referenceValue": after}], "before": False,
        }
    return query


def count_filtered_public_markets(project: str) -> int:
    url = QUERY_URL.format(project=project).replace(":runQuery", ":runAggregationQuery")
    result = _post_json(url, {
        "structuredAggregationQuery": {
            "structuredQuery": _market_query(),
            "aggregations": [{"count": {}, "alias": "total"}],
        }
    }, max_bytes=100_000)
    for item in result:
        value = item.get("result", {}).get("aggregateFields", {}).get("total", {})
        if "integerValue" in value:
            return int(value["integerValue"])
    raise ValueError("No valid aggregate count returned by Firestore")


def load_filtered_public_markets(project: str, max_records: int = 20000,
                                 page_size: int = 500) -> list[dict]:
    if not project or not project.replace("-", "").isalnum():
        raise ValueError("Invalid Firebase project ID")
    if not 1 <= max_records <= 100_000 or not 1 <= page_size <= 1000:
        raise ValueError("Invalid paging safety limits")

    # A count aggregation is cheaper than reading thousands of documents
    # before discovering the sample would be incomplete.
    expected = count_filtered_public_markets(project)
    print("Firestore market-category match count:", expected)
    if not expected:
        raise ValueError("No markets in the allowed categories")
    if expected > max_records:
        raise ValueError("Quality gate: market count exceeds safe read limit " + str(max_records))

    markets = []
    last_name = None
    while len(markets) < expected:
        payload = {"structuredQuery": _market_query(
            limit=min(page_size, expected - len(markets)), after=last_name)}
        result = _post_json(QUERY_URL.format(project=project), payload)
        page = convert_response(result)
        if not page:
            raise ValueError("Empty page before expected count completed")
        current_last = result[-1].get("document", {}).get("name")
        if not current_last or current_last == last_name:
            raise ValueError("Invalid or repeated Firestore cursor")
        last_name = current_last
        markets.extend(page)
        print("Read-only bootstrap progress: " + str(len(markets)) + "/" + str(expected), flush=True)
    if len(markets) != expected:
        raise ValueError("Incomplete Firestore market export")
    return markets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.environ.get("FIREBASE_PROJECT_ID", "market-ef407"))
    parser.add_argument("--max-records", type=int, default=20000)
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = load_filtered_public_markets(args.project, args.max_records, args.page_size)
    if not records:
        raise ValueError("No records in allowed market categories")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", "utf-8")
    from collections import Counter
    counts = Counter(row.get("categoria", "(missing)") for row in records)
    print("Read-only market bootstrap: ", len(records), dict(counts))
    print("No Firestore writes were performed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("Bootstrap blocked: " + str(exc), file=sys.stderr)
        sys.exit(1)
