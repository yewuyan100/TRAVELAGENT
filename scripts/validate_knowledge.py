from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "id",
    "city",
    "province",
    "country",
    "category",
    "title",
    "tags",
    "suitable_for",
    "updated_at",
    "source_type",
    "content",
}

ALLOWED_CATEGORIES = {
    "overview",
    "attractions",
    "food",
    "itinerary",
    "transport",
    "tips",
    "season",
    "weather_note",
}

MIN_CONTENT_LENGTH = 80


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: JSON 格式错误：{exc}") from exc


def validate_item(item: dict[str, Any], index: int, seen_ids: set[str]) -> list[str]:
    errors: list[str] = []
    item_id = str(item.get("id") or f"#{index}")

    missing = sorted(field for field in REQUIRED_FIELDS if field not in item)
    if missing:
        errors.append(f"{item_id}: 缺少字段 {', '.join(missing)}")

    if item_id in seen_ids:
        errors.append(f"{item_id}: id 重复")
    seen_ids.add(item_id)

    category = item.get("category")
    if category not in ALLOWED_CATEGORIES:
        errors.append(f"{item_id}: category 不合法：{category}")

    for array_field in ["tags", "suitable_for"]:
        value = item.get(array_field)
        if not isinstance(value, list) or not all(isinstance(entry, str) and entry.strip() for entry in value):
            errors.append(f"{item_id}: {array_field} 必须是非空字符串数组")

    content = item.get("content")
    if not isinstance(content, str) or len(content.strip()) < MIN_CONTENT_LENGTH:
        errors.append(f"{item_id}: content 过短，至少需要 {MIN_CONTENT_LENGTH} 个字符")

    updated_at = item.get("updated_at")
    if not isinstance(updated_at, str) or len(updated_at.split("-")) != 3:
        errors.append(f"{item_id}: updated_at 应使用 YYYY-MM-DD 格式")

    source_type = item.get("source_type")
    if not isinstance(source_type, str) or not source_type.strip():
        errors.append(f"{item_id}: source_type 不能为空")

    return errors


def validate_file(path: Path) -> tuple[int, list[str]]:
    data = load_json(path)
    if not isinstance(data, list):
        return 0, [f"{path}: 顶层必须是知识条目数组"]

    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"{path}: 第 {index + 1} 条不是对象")
            continue
        errors.extend(validate_item(item, index, seen_ids))
    return len(data), errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate travel knowledge JSON files.")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["data/knowledge/travel_knowledge.json", "data/knowledge_drafts/static_knowledge_trial_3_cities.json"],
        help="需要校验的 JSON 文件路径",
    )
    args = parser.parse_args()

    total_items = 0
    all_errors: list[str] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.exists():
            all_errors.append(f"{path}: 文件不存在")
            continue
        count, errors = validate_file(path)
        total_items += count
        all_errors.extend(errors)

    if all_errors:
        print("知识库校验失败：")
        for error in all_errors:
            print(f"- {error}")
        return 1

    print(f"知识库校验通过，共检查 {total_items} 条知识。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
