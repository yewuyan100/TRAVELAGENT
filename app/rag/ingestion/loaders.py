from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.rag.ingestion.normalizer import normalize_json_payload, normalize_text_document


SUPPORTED_JSON = {".json"}
SUPPORTED_TEXT = {".md", ".txt"}


def iter_raw_paths() -> list[Path]:
    paths: list[Path] = []

    if settings.raw_static_dir.exists():
        paths.extend(sorted(path for path in settings.raw_static_dir.iterdir() if path.is_file()))

    if not paths and settings.knowledge_json_path.exists():
        paths.append(settings.knowledge_json_path)

    if settings.raw_dynamic_dir.exists():
        paths.extend(sorted(path for path in settings.raw_dynamic_dir.iterdir() if path.is_file()))

    return paths


def load_raw_documents() -> list[dict]:
    documents: list[dict] = []
    for path in iter_raw_paths():
        suffix = path.suffix.lower()
        if suffix in SUPPORTED_JSON:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            documents.extend(normalize_json_payload(payload, source=str(path), source_type="static_json"))
        elif suffix in SUPPORTED_TEXT:
            documents.extend(normalize_text_document(path))
    return documents


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
