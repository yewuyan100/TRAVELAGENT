from __future__ import annotations

import copy
import logging
import math
import re
from collections import Counter, OrderedDict, defaultdict

from app.config import settings
from app.rag.embeddings import EmbeddingProvider, embeddings_to_numpy
from app.rag.loader import VectorStore
from app.rag.reranker import RerankProvider
from app.schemas import QueryAnalysis, RetrievalReport


logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = {
    "food": ["美食", "吃", "小吃", "好吃", "火锅", "餐厅", "特色菜", "当地菜", "夜市"],
    "attractions": ["景点", "去哪玩", "好玩", "打卡", "游玩", "景区", "名胜", "路线"],
    "audience": ["适合", "人群", "亲子", "情侣", "老人", "朋友", "慢节奏", "轻松", "休闲", "不适合"],
    "tips": ["建议", "注意", "避坑", "攻略", "怎么安排", "推荐安排", "注意事项"],
    "overview": ["介绍", "概况", "怎么样", "什么样", "季节", "什么时候去", "最佳季节"],
}

TAG_ALIASES = {
    "慢节奏": "慢生活",
    "慢旅行": "慢生活",
    "慢游": "慢生活",
    "轻松": "休闲",
    "放松": "休闲",
    "看海": "海滨",
    "海边": "海滨",
    "带孩子": "亲子",
    "小孩": "亲子",
    "孩子": "亲子",
    "吃东西": "美食",
    "好吃的": "美食",
    "古城": "古都",
}

REALTIME_KEYWORDS = [
    "今天",
    "今日",
    "现在",
    "实时",
    "当前",
    "此刻",
    "明天",
    "今晚",
    "几点开门",
    "几点关门",
    "营业时间",
    "开放时间",
    "票价",
    "门票",
    "天气",
    "人多吗",
    "排队",
    "闭园",
    "开园",
]
ROUTE_KEYWORDS = ["路线", "怎么去", "如何去", "到达", "交通", "地铁", "公交", "打车", "自驾", "从"]
RECOMMENDATION_KEYWORDS = ["推荐", "适合", "去哪", "哪里", "安排", "行程", "值得"]
KNOWN_ENTITY_MARKERS = ["东京", "迪士尼", "西湖", "兵马俑", "熊猫基地", "鼓浪屿", "洪崖洞"]


def tokenize(text: str) -> list[str]:
    text = str(text).lower()
    ascii_terms = re.findall(r"[a-z0-9]+", text)
    cjk_blocks = re.findall(r"[\u4e00-\u9fff]+", text)

    tokens = list(ascii_terms)
    for block in cjk_blocks:
        if len(block) <= 8:
            tokens.append(block)
        tokens.extend(block[index : index + 1] for index in range(len(block)))
        tokens.extend(block[index : index + 2] for index in range(max(len(block) - 1, 0)))
        tokens.extend(block[index : index + 3] for index in range(max(len(block) - 2, 0)))
    return [token for token in tokens if token]


def chunk_to_text(item: dict | str) -> str:
    if not isinstance(item, dict):
        return str(item)

    fields = [
        item.get("title", ""),
        item.get("city", ""),
        item.get("province", ""),
        item.get("category", ""),
        " ".join(str(tag) for tag in item.get("tags", []) if tag),
        item.get("content", ""),
    ]
    return "\n".join(field for field in fields if field)


class QueryAnalyzer:
    def __init__(self, available_cities: list[str], available_tags: list[str]):
        self.available_cities = sorted(set(available_cities))
        self.available_tags = sorted(set(available_tags))

    def analyze(self, question: str) -> QueryAnalysis:
        question = question.strip()
        city = self._detect_city(question)
        categories = self._detect_categories(question)
        tags = self._detect_tags(question)
        needs_realtime = any(keyword in question for keyword in REALTIME_KEYWORDS)
        question_type = self._detect_question_type(question, needs_realtime)
        entities = self._detect_entities(question, city)

        reason_parts = []
        if needs_realtime:
            reason_parts.append("问题包含实时信号")
        if city:
            reason_parts.append(f"命中城市：{city}")
        if categories:
            reason_parts.append(f"命中类别：{','.join(categories)}")
        if tags:
            reason_parts.append(f"命中标签：{','.join(tags)}")
        if not reason_parts:
            reason_parts.append("未命中明确结构化信号，按通用问题处理")

        return QueryAnalysis(
            question=question,
            question_type=question_type,
            needs_realtime=needs_realtime,
            city=city,
            categories=categories,
            tags=tags,
            entities=entities,
            reason="；".join(reason_parts),
        )

    def _detect_city(self, question: str) -> str | None:
        for city in self.available_cities:
            if city and city in question:
                return city
        return None

    def _detect_categories(self, question: str) -> list[str]:
        categories = []
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in question for keyword in keywords):
                categories.append(category)
        return categories

    def _detect_tags(self, question: str) -> list[str]:
        detected_tags = set()
        for tag in self.available_tags:
            if tag and tag in question:
                detected_tags.add(tag)

        for keyword, mapped_tag in TAG_ALIASES.items():
            if keyword in question and mapped_tag in self.available_tags:
                detected_tags.add(mapped_tag)

        return sorted(detected_tags)

    def _detect_question_type(self, question: str, needs_realtime: bool) -> str:
        if not question:
            return "missing"
        if needs_realtime:
            return "realtime"
        if any(keyword in question for keyword in ROUTE_KEYWORDS):
            return "route"
        if any(keyword in question for keyword in RECOMMENDATION_KEYWORDS):
            return "recommendation"
        return "fact"

    def _detect_entities(self, question: str, city: str | None) -> list[str]:
        entities = []
        if city:
            entities.append(city)

        for marker in KNOWN_ENTITY_MARKERS:
            if marker in question and marker not in entities:
                entities.append(marker)

        return entities


class BM25Index:
    def __init__(self, chunks: list[dict | str], k1: float = 1.5, b: float = 0.75):
        self.documents = [tokenize(chunk_to_text(item)) for item in chunks]
        self.k1 = k1
        self.b = b
        self.doc_lengths = [len(document) for document in self.documents]
        self.avg_doc_length = sum(self.doc_lengths) / max(len(self.doc_lengths), 1)
        self.term_frequencies = [Counter(document) for document in self.documents]
        self.idf = self._build_idf()

    def _build_idf(self) -> dict[str, float]:
        document_frequency = defaultdict(int)
        for document in self.documents:
            for token in set(document):
                document_frequency[token] += 1

        total_documents = len(self.documents)
        return {
            token: math.log(1 + (total_documents - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }

    def search(self, query: str, top_k: int) -> list[dict]:
        query_terms = Counter(tokenize(query))
        if not query_terms:
            return []

        scored = []
        for index, frequencies in enumerate(self.term_frequencies):
            score = 0.0
            doc_length = self.doc_lengths[index] or 1
            for token, query_frequency in query_terms.items():
                term_frequency = frequencies.get(token, 0)
                if term_frequency <= 0:
                    continue

                idf = self.idf.get(token, 0.0)
                denominator = term_frequency + self.k1 * (
                    1 - self.b + self.b * doc_length / max(self.avg_doc_length, 1)
                )
                score += idf * ((term_frequency * (self.k1 + 1)) / denominator) * query_frequency

            if score > 0:
                scored.append({"chunk_index": index, "bm25_score": float(score)})

        return sorted(scored, key=lambda item: item["bm25_score"], reverse=True)[:top_k]


class LRUQueryCache:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.items: OrderedDict[tuple[str, int], RetrievalReport] = OrderedDict()

    def get(self, key: tuple[str, int]) -> RetrievalReport | None:
        item = self.items.get(key)
        if item is None:
            return None
        self.items.move_to_end(key)
        return copy.deepcopy(item)

    def set(self, key: tuple[str, int], value: RetrievalReport) -> None:
        self.items[key] = copy.deepcopy(value)
        self.items.move_to_end(key)
        while len(self.items) > self.max_size:
            self.items.popitem(last=False)


class Retriever:
    def __init__(
        self,
        store: VectorStore,
        embedding_model: EmbeddingProvider | None,
        rerank_provider: RerankProvider | None = None,
        vector_enabled: bool = True,
    ):
        self.store = store
        self.embedding_model = embedding_model
        self.rerank_provider = rerank_provider
        self.vector_enabled = vector_enabled
        self.available_cities = self._collect_available_cities()
        self.available_tags = self._collect_available_tags()
        self.query_analyzer = QueryAnalyzer(self.available_cities, self.available_tags)
        self.bm25 = BM25Index(self.store.chunks)
        self.query_cache = LRUQueryCache(settings.query_cache_size)

    def analyze_query(self, question: str) -> QueryAnalysis:
        return self.query_analyzer.analyze(question)

    def retrieve_with_report(self, question: str, top_k: int = settings.top_k) -> RetrievalReport:
        question = question.strip()
        cache_key = (question, top_k)
        cached = self.query_cache.get(cache_key)
        if cached is not None:
            logger.info("[RAG] 命中 Query 检索缓存")
            return cached

        analysis = self.analyze_query(question)
        logger.info("[RAG] Query Analysis | %s", analysis.to_dict())

        candidate_k = max(settings.candidate_k, top_k * 6, settings.rerank_top_k)
        vector_results = self._vector_search(question, candidate_k)
        bm25_results = self.bm25.search(query=question, top_k=candidate_k)

        candidates = self._merge_candidates(vector_results, bm25_results)
        reranked_results = self._rerank(candidates, analysis)
        selected_results = reranked_results[:top_k]
        is_confident, confidence_reason, diagnostics = self._confidence(selected_results, len(candidates))

        report = RetrievalReport(
            question=question,
            analysis=analysis,
            results=selected_results,
            candidate_count=len(candidates),
            is_confident=is_confident,
            confidence_reason=confidence_reason,
            diagnostics=diagnostics,
        )
        self.query_cache.set(cache_key, report)
        return report

    def _vector_search(self, question: str, candidate_k: int) -> list[dict]:
        if not settings.rag_enable_vector or not self.vector_enabled:
            logger.info("[RAG] 向量检索未启用或索引配置不匹配，本次使用关键词检索")
            return []
        if self.embedding_model is None:
            logger.warning("[RAG] Embedding Provider 不可用，本次检索降级为 BM25-only")
            return []

        try:
            query_vector = embeddings_to_numpy(self.embedding_model.embed([question]))
            return self.store.search(query_vector=query_vector, top_k=candidate_k)
        except Exception as exc:
            logger.warning("[RAG] 向量检索失败，本次降级为 BM25-only：%s", exc)
            if settings.rag_fallback_to_keyword:
                return []
            raise

    def retrieve(self, question: str, top_k: int = settings.top_k) -> list[dict]:
        return self.retrieve_with_report(question=question, top_k=top_k).results

    def _collect_available_cities(self) -> list[str]:
        return sorted({str(item["city"]) for item in self.store.chunks if isinstance(item, dict) and item.get("city")})

    def _collect_available_tags(self) -> list[str]:
        tags = set()
        for item in self.store.chunks:
            if isinstance(item, dict):
                for tag in item.get("tags", []) or []:
                    if tag:
                        tags.add(str(tag))
        return sorted(tags)

    def _result_from_chunk_index(self, chunk_index: int) -> dict:
        item = self.store.chunks[chunk_index]
        if isinstance(item, dict):
            content = item.get("content", "")
            metadata = {key: value for key, value in item.items() if key != "content"}
        else:
            content = str(item)
            metadata = {}

        return {"chunk_index": chunk_index, "chunk": content, "metadata": metadata}

    def _normalize_scores(self, results: list[dict], score_key: str, normalized_key: str) -> None:
        positive_scores = [float(result.get(score_key, 0.0)) for result in results if float(result.get(score_key, 0.0)) > 0]
        if not positive_scores:
            for result in results:
                result[normalized_key] = 0.0
            return

        min_score = min(positive_scores)
        max_score = max(positive_scores)
        for result in results:
            score = float(result.get(score_key, 0.0))
            if score <= 0:
                result[normalized_key] = 0.0
            elif max_score == min_score:
                result[normalized_key] = 1.0
            else:
                result[normalized_key] = (score - min_score) / (max_score - min_score)

    def _merge_candidates(self, vector_results: list[dict], bm25_results: list[dict]) -> list[dict]:
        merged: dict[int, dict] = {}

        for result in vector_results:
            chunk_index = result.get("chunk_index")
            if chunk_index is None:
                continue
            merged[chunk_index] = {
                **result,
                "faiss_score": float(result.get("score", 0.0)),
                "vector_score": float(result.get("score", 0.0)),
                "bm25_score": 0.0,
                "retrieval_sources": ["faiss"],
            }

        for result in bm25_results:
            chunk_index = result["chunk_index"]
            current = merged.get(chunk_index)
            if current is None:
                current = self._result_from_chunk_index(chunk_index)
                current.update({
                    "faiss_score": 0.0,
                    "vector_score": 0.0,
                    "bm25_score": float(result.get("bm25_score", 0.0)),
                    "retrieval_sources": ["bm25"],
                })
                merged[chunk_index] = current
            else:
                current["bm25_score"] = float(result.get("bm25_score", 0.0))
                if "bm25" not in current["retrieval_sources"]:
                    current["retrieval_sources"].append("bm25")

        candidates = list(merged.values())
        self._normalize_scores(candidates, "faiss_score", "faiss_norm")
        self._normalize_scores(candidates, "bm25_score", "bm25_norm")

        for result in candidates:
            result["hybrid_score"] = (
                settings.faiss_weight * result.get("faiss_norm", 0.0)
                + settings.bm25_weight * result.get("bm25_norm", 0.0)
            )
            result["score"] = result["hybrid_score"]

        return sorted(candidates, key=lambda item: item["hybrid_score"], reverse=True)

    def _metadata_bonus(self, result: dict, analysis: QueryAnalysis) -> tuple[float, dict]:
        metadata = result.get("metadata", {})
        result_tags = metadata.get("tags", [])
        if not isinstance(result_tags, list):
            result_tags = []

        matched_tags = sorted(set(analysis.tags).intersection(set(result_tags)))
        match_info = {
            "city": bool(analysis.city and metadata.get("city") == analysis.city),
            "category": bool(metadata.get("category") in set(analysis.categories)),
            "tags": matched_tags,
        }

        bonus = 0.0
        if match_info["city"]:
            bonus += 0.18
        if match_info["category"]:
            bonus += 0.12
        if matched_tags:
            bonus += min(0.12, 0.04 * len(matched_tags))
        return bonus, match_info

    def _lexical_overlap_score(self, question: str, chunk: str) -> float:
        query_tokens = set(tokenize(question))
        chunk_tokens = set(tokenize(chunk))
        if not query_tokens or not chunk_tokens:
            return 0.0
        return len(query_tokens.intersection(chunk_tokens)) / len(query_tokens)

    def _rerank(self, candidates: list[dict], analysis: QueryAnalysis) -> list[dict]:
        prepared = self._prepare_candidates(candidates, analysis)
        if not self.rerank_provider:
            return prepared

        rerank_input = prepared[: max(settings.rerank_top_k, settings.rerank_top_n)]
        try:
            return self.rerank_provider.rerank(analysis.question, rerank_input)
        except Exception as exc:
            logger.warning("[RAG] Reranker 调用失败，保留原始召回顺序：%s", exc)
            if settings.rerank_fallback_to_original_order:
                return prepared
            raise

    def _prepare_candidates(self, candidates: list[dict], analysis: QueryAnalysis) -> list[dict]:
        prepared = []
        for result in candidates:
            metadata_bonus, match_info = self._metadata_bonus(result, analysis)
            overlap_score = self._lexical_overlap_score(analysis.question, result.get("chunk", ""))
            agreement_bonus = 0.08 if result.get("faiss_norm", 0.0) > 0 and result.get("bm25_norm", 0.0) > 0 else 0.0
            rule_score = 0.58 * result.get("hybrid_score", 0.0) + 0.22 * overlap_score + metadata_bonus + agreement_bonus

            new_result = dict(result)
            new_result["overlap_score"] = overlap_score
            new_result["rule_score"] = float(rule_score)
            new_result["final_score"] = float(result.get("hybrid_score", 0.0))
            new_result["match_info"] = match_info
            prepared.append(new_result)

        return sorted(prepared, key=lambda item: item.get("hybrid_score", 0.0), reverse=True)

    def _confidence(self, results: list[dict], candidate_count: int) -> tuple[bool, str, dict]:
        if not results:
            return False, "没有召回任何资料", {"best_score": 0.0}

        top = results[0]
        best_final_score = float(top.get("final_score", top.get("score", 0.0)) or 0.0)
        best_component = max(float(top.get("faiss_norm", 0.0)), float(top.get("bm25_norm", 0.0)))
        agreement = min(float(top.get("faiss_norm", 0.0)), float(top.get("bm25_norm", 0.0)))
        confident = (
            candidate_count > 0
            and best_final_score >= settings.min_rerank_score
            and best_component >= settings.min_retrieval_score
            and (agreement >= settings.min_result_agreement or float(top.get("bm25_norm", 0.0)) >= 0.80)
        )

        diagnostics = {
            "best_rerank_score": best_final_score,
            "best_final_score": best_final_score,
            "best_component_score": best_component,
            "agreement_score": agreement,
            "rerank_enabled": bool(self.rerank_provider),
            "candidate_count": candidate_count,
            "thresholds": {
                "min_rerank_score": settings.min_rerank_score,
                "min_retrieval_score": settings.min_retrieval_score,
                "min_result_agreement": settings.min_result_agreement,
            },
        }

        if confident:
            return True, "召回分数、重排分数和召回一致性达到阈值", diagnostics

        reason = f"检索置信度不足：最终分={best_final_score:.3f}，组件分={best_component:.3f}，一致性={agreement:.3f}"
        return False, reason, diagnostics
