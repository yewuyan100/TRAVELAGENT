from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.rag.embeddings import create_embedding_provider


def main() -> int:
    provider = create_embedding_provider()
    sample_text = "成都适合慢节奏旅行，也适合美食和城市漫游。"
    vectors = provider.embed([sample_text])
    if not vectors or not vectors[0]:
        print("Embedding 自检失败：接口没有返回向量")
        return 1

    dimension = len(vectors[0])
    print("Embedding 自检通过")
    print("Provider：", provider.name)
    print("Model：", provider.model)
    print("Configured Dimension：", settings.embedding_dimension)
    print("Returned Dimension：", dimension)
    if dimension != settings.embedding_dimension:
        print("维度不一致，请检查 EMBEDDING_DIMENSION 与模型配置")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
