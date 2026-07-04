from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.rag.ingestion.cleaner import clean_text


DOCUMENT_ARRAY_KEYS = ("documents", "items", "data")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_slug(value: str, fallback: str = "document") -> str:
    text = clean_text(value).lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if ascii_text:
        return ascii_text[:80]
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{fallback}_{digest}"


def stable_content_hash(document: dict[str, Any]) -> str:
    payload = {
        "title": document.get("title", ""),
        "content": document.get("content", ""),
        "city": document.get("city", ""),
        "province": document.get("province", ""),
        "country": document.get("country", ""),
        "category": document.get("category", ""),
        "tags": document.get("tags", []),
        "source": document.get("source", ""),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def extract_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in DOCUMENT_ARRAY_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]
    return []


def normalize_json_payload(payload: Any, source: str, source_type: str = "static_json") -> list[dict[str, Any]]:
    documents = []
    for index, item in enumerate(extract_items(payload), start=1):
        if not isinstance(item, dict):
            continue
        document = normalize_record(item, source=source, source_type=source_type, ordinal=index)
        if document:
            documents.append(document)
    return documents


def normalize_text_document(path: Path, source_type: str = "static_text") -> list[dict[str, Any]]:
    content = clean_text(path.read_text(encoding="utf-8-sig"))
    if not content:
        return []

    title = clean_text(path.stem)
    document = {
        "doc_id": stable_slug(str(path), "text"),
        "title": title,
        "content": content,
        "city": "",
        "province": "",
        "country": "中国",
        "category": "overview",
        "tags": [],
        "source_type": source_type,
        "source": str(path),
        "updated_at": utc_now_iso(),
    }
    document["content_hash"] = stable_content_hash(document)
    return [document]


def normalize_record(
    item: dict[str, Any],
    source: str,
    source_type: str = "static_json",
    ordinal: int = 1,
) -> dict[str, Any] | None:
    review_status = clean_text(item.get("review_status"))
    if review_status and review_status != "approved":
        return None

    raw_id = clean_text(item.get("doc_id") or item.get("id"))
    title = clean_text(item.get("title") or item.get("name") or raw_id or f"资料 {ordinal}")
    content = clean_text(item.get("content") or item.get("text") or item.get("body") or item.get("description"))
    if not content:
        return None

    city = clean_text(item.get("city") or item.get("destination") or item.get("目的地"))
    province = clean_text(item.get("province") or item.get("region") or item.get("省份"))
    country = clean_text(item.get("country") or "中国")
    category = clean_text(item.get("category") or "overview")
    tags = item.get("tags") or []
    if not isinstance(tags, list):
        tags = [clean_text(tags)] if clean_text(tags) else []
    tags = [clean_text(tag) for tag in tags if clean_text(tag)]

    doc_id = raw_id or stable_slug(f"{city}_{category}_{title}_{ordinal}", "doc")
    document = {
        "doc_id": doc_id,
        "title": title,
        "content": content,
        "city": city,
        "province": province,
        "country": country,
        "category": category,
        "tags": tags,
        "source_type": clean_text(item.get("source_type") or source_type),
        "source": clean_text(item.get("source") or item.get("source_url") or source),
        "updated_at": clean_text(item.get("updated_at") or utc_now_iso()),
    }
    document["content_hash"] = stable_content_hash(document)
    return document
