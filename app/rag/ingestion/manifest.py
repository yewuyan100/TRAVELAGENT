from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "documents": {}}
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if "documents" not in data:
        data["documents"] = {}
    return data


def save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)


def diff_documents(documents: list[dict], manifest: dict, mode: str) -> tuple[list[dict], list[str]]:
    previous = manifest.get("documents", {})
    current_ids = {document["doc_id"] for document in documents}
    changed = []

    for document in documents:
        previous_entry = previous.get(document["doc_id"])
        if mode == "full" or previous_entry is None:
            changed.append(document)
            continue
        if previous_entry.get("content_hash") != document.get("content_hash"):
            changed.append(document)

    removed = sorted(set(previous) - current_ids)
    return changed, removed


def update_manifest(
    manifest: dict,
    documents: list[dict],
    chunk_counts: dict[str, int],
    removed_doc_ids: list[str],
) -> dict:
    document_entries = manifest.setdefault("documents", {})
    timestamp = now_iso()

    for document in documents:
        document_entries[document["doc_id"]] = {
            "content_hash": document.get("content_hash", ""),
            "last_processed_at": timestamp,
            "chunk_count": int(chunk_counts.get(document["doc_id"], 0)),
            "status": "active",
            "title": document.get("title", ""),
            "city": document.get("city", ""),
            "category": document.get("category", ""),
            "source": document.get("source", ""),
            "updated_at": document.get("updated_at", ""),
        }

    for doc_id in removed_doc_ids:
        entry = document_entries.setdefault(doc_id, {})
        entry["status"] = "inactive"
        entry["last_processed_at"] = timestamp

    manifest["version"] = 1
    manifest["updated_at"] = timestamp
    return manifest
