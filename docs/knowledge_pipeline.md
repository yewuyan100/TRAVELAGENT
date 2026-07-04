# Knowledge Pipeline

本项目的知识库已从单个 `knowledge.json` + 手动全量索引，升级为标准 RAG Pipeline：

```text
data/raw -> data/processed/documents.jsonl -> data/chunks/chunks.jsonl -> data/index/travel.index
```

## 目录结构

```text
data/
  raw/
    static/
      travel_knowledge.json
    dynamic/
  processed/
    documents.jsonl
    manifest.json
  chunks/
    chunks.jsonl
  index/
    travel.index
    index_metadata.json
```

旧路径仍保留 fallback：

- `data/knowledge/travel_knowledge.json`
- `data/chunks.json`
- `data/travel.index`
- `data/index_meta.json`

服务启动时会优先读取新索引三件套；如果新索引不存在，会回退到旧索引。

## 添加新资料

1. 优先把静态资料放到 `data/raw/static/travel_knowledge.json`。
2. 每条资料建议包含 `id/title/content/city/province/country/category/tags/source_type/updated_at`。
3. 如果资料带有 `review_status` 字段，只有 `review_status="approved"` 会进入索引；`pending/rejected` 会被跳过。没有该字段的历史人工资料会按可信资料兼容导入。
4. Pipeline 会统一转换为 Document：

```json
{
  "doc_id": "...",
  "title": "...",
  "content": "...",
  "city": "...",
  "province": "...",
  "country": "...",
  "category": "...",
  "tags": [],
  "source_type": "static_json",
  "source": "...",
  "updated_at": "...",
  "content_hash": "..."
}
```

## 全量重建

```bash
python scripts/rebuild_knowledge_base.py --mode full
```

全量重建会重新读取 raw 资料、生成 documents、切 chunks、调用当前 embedding 配置，并重建 FAISS index。

兼容旧命令：

```bash
python scripts/rebuild_index.py
```

## 增量更新

```bash
python scripts/rebuild_knowledge_base.py --mode incremental
```

增量模式会读取 `data/processed/manifest.json`，比较每个 Document 的 `content_hash`：

- hash 没变：跳过切片、embedding 和索引重建。
- hash 变化或新增：重新生成 chunks，并重建 index。
- raw 中删除的文档：在 manifest 中标记为 `inactive`。

## manifest 的作用

`manifest.json` 记录每个文档的：

- `content_hash`
- `last_processed_at`
- `chunk_count`
- `status`
- `title/city/category/source/updated_at`

它用于判断资料是否变化，避免每次都重复调用 embedding API。

## 管理接口

```text
GET  /admin/knowledge/status
POST /admin/knowledge/rebuild
POST /admin/knowledge/update
```

生产环境需要给这些接口补鉴权，当前代码已保留 TODO。

## 当前限制

- 当前 FAISS 使用 Flat index，局部删除和局部替换较麻烦；因此本版采用折中方案：无变化时完全跳过 embedding，有变化时整库重建 index。
- raw dynamic 目录已预留，但动态热榜、营业状态、实时 POI 等资料还没有自动写入。
- Markdown/txt 会作为单文档导入，复杂 front matter 暂未解析。
