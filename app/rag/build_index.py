from __future__ import annotations

from collections import Counter

from app.config import settings
from app.rag.loader import EmbeddingModel, VectorStore, load_knowledge_items


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
    knowledge_items = load_knowledge_items(settings.knowledge_json_path)
    chunk_items = build_chunks(knowledge_items)

    if not chunk_items:
        raise ValueError("没有生成任何 chunk，请检查 travel_knowledge.json 内容")

    embedding_model = EmbeddingModel()
    embeddings = embedding_model.embed([item["content"] for item in chunk_items])

    store = VectorStore(index_path=settings.index_path, chunks_path=settings.chunks_path)
    store.build(embeddings, chunk_items)
    store.save()

    return {
        "knowledge_path": str(settings.knowledge_json_path),
        "knowledge_count": len(knowledge_items),
        "chunk_count": len(chunk_items),
        "index_path": str(settings.index_path),
        "chunks_path": str(settings.chunks_path),
    }


def main() -> None:
    result = build_index()
    print("索引构建完成")
    print("原始知识库：", result["knowledge_path"])
    print("知识条目数量：", result["knowledge_count"])
    print("生成 Chunk 数量：", result["chunk_count"])
    print("索引保存位置：", result["index_path"])
    print("Chunk 保存位置：", result["chunks_path"])


if __name__ == "__main__":
    main()
