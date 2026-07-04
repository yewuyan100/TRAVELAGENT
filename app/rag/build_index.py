from __future__ import annotations

from collections import Counter


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
}

METADATA_FIELDS = [
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
    "source_url",
    "freshness",
]


def validate_knowledge_items(items: list[dict]) -> None:
    if not isinstance(items, list):
        raise ValueError("知识库最外层必须是 JSON 数组")

    ids = []
    errors = []

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 条不是 JSON object")
            continue

        missing_fields = sorted(REQUIRED_FIELDS - set(item.keys()))
        if missing_fields:
            errors.append(f"第 {index} 条缺少字段：{', '.join(missing_fields)}")

        item_id = item.get("id")
        if item_id:
            ids.append(str(item_id))
        else:
            errors.append(f"第 {index} 条 id 为空")

        category = item.get("category")
        if category not in ALLOWED_CATEGORIES:
            errors.append(
                f"第 {index} 条 category 非法：{category}；"
                f"只能是 {', '.join(sorted(ALLOWED_CATEGORIES))}"
            )

        if not str(item.get("content", "")).strip():
            errors.append(f"第 {index} 条 content 为空")

        if not isinstance(item.get("tags", []), list):
            errors.append(f"第 {index} 条 tags 必须是数组")

        if not isinstance(item.get("suitable_for", []), list):
            errors.append(f"第 {index} 条 suitable_for 必须是数组")

    duplicate_ids = sorted([item_id for item_id, count in Counter(ids).items() if count > 1])
    if duplicate_ids:
        errors.append(f"id 不唯一，重复 id：{', '.join(duplicate_ids)}")

    if errors:
        preview = "\n".join(errors[:20])
        if len(errors) > 20:
            preview += f"\n... 还有 {len(errors) - 20} 个错误"
        raise ValueError(preview)


def make_chunk(item: dict) -> dict:
    chunk = {field: item.get(field) for field in METADATA_FIELDS}
    chunk["content"] = str(item.get("content", "")).strip()
    return chunk


def build_chunks(items: list[dict]) -> list[dict]:
    validate_knowledge_items(items)
    return [make_chunk(item) for item in items]


def build_index() -> dict:
    from app.rag.ingestion.pipeline import run_ingestion_pipeline

    return run_ingestion_pipeline(mode="full")


def main() -> None:
    result = build_index()
    print("索引构建完成")
    print("模式：", result["mode"])
    print("文档数量：", result["document_count"])
    print("生成 Chunk 数量：", result["chunk_count"])
    print("Embedding Provider：", result["embedding_provider"])
    print("Embedding Model：", result["embedding_model"])
    print("Embedding Dimension：", result["embedding_dimension"])
    print("索引保存位置：", result["index_path"])
    print("Chunk 保存位置：", result["chunks_path"])
    print("索引元数据：", result["index_metadata_path"])


if __name__ == "__main__":
    main()
