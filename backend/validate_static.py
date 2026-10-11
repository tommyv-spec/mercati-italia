#!/usr/bin/env python3
"""Validate every file referenced by a static release manifest before deployment."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def validate(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text("utf-8"))
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported catalog schema")
    out = manifest_path.parent
    public = out.parent.parent
    layout = manifest.get("layout")
    if layout == "single":
        parts = [{"path": manifest["catalog"], "count": manifest["total"]}]
    elif layout == "regional":
        parts = manifest["regions"]
    else:
        raise ValueError("Invalid catalog layout")

    ids = set()
    all_markets = []
    for entry in parts:
        rel = entry.get("path", "")
        if not re.fullmatch(r"data/v1/[a-z0-9/.-]+\.json", rel) or ".." in rel:
            raise ValueError("Unsafe asset path")
        asset = (public / rel).resolve()
        if not asset.is_relative_to(public.resolve()) or not asset.is_file():
            raise ValueError("Missing asset: " + rel)
        blob = asset.read_bytes()
        match = re.search(r"-([a-f0-9]{14})\.json$", rel)
        if not match or not hashlib.sha256(blob).hexdigest().startswith(match.group(1)):
            raise ValueError("Asset hash mismatch: " + rel)
        payload = json.loads(blob)
        if payload.get("schema") != 1 or not isinstance(payload.get("markets"), list):
            raise ValueError("Invalid asset schema: " + rel)
        records = payload["markets"]
        if len(records) != entry.get("count", len(records)):
            raise ValueError("Region count mismatch")
        for item in records:
            if item.get("slug") in ids or not item.get("slug"):
                raise ValueError("Duplicate or missing market identifier")
            ids.add(item["slug"])
            if not item.get("nome") or not item.get("citta"):
                raise ValueError("Missing market name or city")
            if item.get("status") in {"annullato", "archiviato"}:
                raise ValueError("Cancelled/archived market in public catalog")
            if item.get("date_quality") not in {"confermata", "riportata", "prevista", "sconosciuta"}:
                raise ValueError("Date certainty not set")
        all_markets.extend(records)

    if len(all_markets) != manifest.get("total"):
        raise ValueError("Manifest total mismatch")
    if not all_markets:
        raise ValueError("Empty market catalog")

    # Index entries must be the exact, non-fabricated lightweight projections.
    index_rel = manifest.get("index")
    if not index_rel:
        raise ValueError("Missing lightweight catalog index")
    if not re.fullmatch(r"data/v1/index-[a-f0-9]{14}\.json", index_rel):
        raise ValueError("Unsafe index path")
    index_asset = public / index_rel
    if not index_asset.is_file():
        raise ValueError("Missing global index")
    index_blob = index_asset.read_bytes()
    index_sha = index_rel.rsplit("-", 1)[-1].removesuffix(".json")
    if not hashlib.sha256(index_blob).hexdigest().startswith(index_sha):
        raise ValueError("Global index content hash mismatch")
    index_obj = json.loads(index_blob)
    if (index_obj.get("schema") != 1 or
        manifest.get("index_schema") != 4 or
        len(index_obj.get("markets", [])) != len(all_markets)):
        raise ValueError("Index count/schema mismatch")
    from export_static import small_index
    expected_index = small_index(all_markets)
    if index_obj["markets"] != expected_index:
        raise ValueError("Search index differs from source market records")

    from export_static import compact_json, CANONICAL_REGIONS
    invalid_regions = {m["regione"] for m in all_markets if m["regione"] not in CANONICAL_REGIONS}
    if invalid_regions:
        raise ValueError("Non-Italian or inconsistent regions: " + repr(invalid_regions))
    signature = hashlib.sha256(compact_json(
        sorted(all_markets, key=lambda m: (m["regione"], m["citta"], m["nome"], m["slug"]))
    )).hexdigest()
    if signature != manifest.get("content_signature"):
        raise ValueError("Content signature mismatch")
    return {"records": len(all_markets), "assets": len(parts), "index_bytes": len(index_blob), "regions": len({m["regione"] for m in all_markets})}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.manifest), indent=2))


if __name__ == "__main__":
    main()
