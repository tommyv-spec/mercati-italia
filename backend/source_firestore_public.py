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


def load_filtered_public_markets(project: str, limit: int = 3000) -> list[dict]:
    if not project or not project.replace("-", "").isalnum():
        raise ValueError("Invalid Firebase project ID")
    if not 1 <= limit <= 10_000:
        raise ValueError("Limit must be between 1 and 10,000")
    request_body = {
        "structuredQuery": {
            "from": [{"collectionId": "mercati"}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": "categoria"},
                    "op": "IN",
                    "value": {
                        "arrayValue": {
                            "values": [{"stringValue": category} for category in CATEGORIES]
                        }
                    },
                }
            },
            "limit": limit,
        },
    }
    request = Request(
        QUERY_URL.format(project=project),
        method="POST",
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "MercatiItaliaStaticBootstrap/1.0"},
    )
    try:
        with urlopen(request, timeout=40) as response:
            data = response.read(25_000_001)
    except HTTPError as exc:
        # Never reveal authentication tokens or dump complete upstream records.
        raise ValueError("Firestore read failed (HTTP " + str(exc.code) + ")") from None
    if len(data) > 25_000_000:
        raise ValueError("Too many records in response; reduce the limit")
    results = json.loads(data)
    if not isinstance(results, list):
        raise ValueError("Unexpected Firestore response")
    markets = convert_response(results)
    if len(markets) >= limit:
        raise ValueError("Query hit safety limit; raise it after reviewing dataset size")
    return markets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.environ.get("FIREBASE_PROJECT_ID", "market-ef407"))
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = load_filtered_public_markets(args.project, args.limit)
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
