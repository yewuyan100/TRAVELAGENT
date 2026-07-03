from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.travel_agent import create_travel_agent
from app.main import _stream_chat_events
from app.schemas import ChatRequest


EVAL_CASES_PATH = PROJECT_ROOT / "tests" / "eval_cases.json"


def load_cases() -> list[dict[str, Any]]:
    return json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8-sig"))


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def contains_any(text: str, words: list[str]) -> bool:
    if not words:
        return True
    return any(word in text for word in words)


def contains_none(text: str, words: list[str]) -> bool:
    return all(word not in text for word in words)


def is_allowed_fallback(answer: str) -> bool:
    markers = [
        "根据当前资料，我无法确认",
        "检索置信度不足",
        "资料不足",
        "工具调用失败",
        "暂未配置",
        "暂时不可用",
        "缺少城市信息",
        "无法生成可靠路线建议",
    ]
    return any(marker in answer for marker in markers)


def check_equal_or_any(actual: str, case: dict[str, Any], key: str) -> tuple[bool, str]:
    expected = case.get(key)
    expected_any = case.get(f"{key}_any")
    if expected is not None:
        passed = actual == expected
        return passed, f"{key}={actual}，期望 {expected}"
    if expected_any is not None:
        options = as_list(expected_any)
        passed = actual in options
        return passed, f"{key}={actual}，期望之一 {options}"
    return True, f"{key} 未配置，跳过"


def evaluate_chat_case(case: dict[str, Any], agent) -> dict[str, Any]:
    result = agent.run(case["question"])
    response = result.to_response().model_dump()
    answer = str(response.get("answer", ""))
    cards = response.get("cards", []) or []
    sources = response.get("sources", []) or []
    failures = []
    fallback_ok = bool(case.get("allow_fallback")) and is_allowed_fallback(answer)

    passed, detail = check_equal_or_any(response.get("intent", ""), case, "expected_intent")
    if not passed:
        failures.append(detail)

    passed, detail = check_equal_or_any(response.get("selected_tool", ""), case, "expected_tool")
    if not passed:
        failures.append(detail)

    if not fallback_ok and not contains_any(answer, as_list(case.get("must_include_any"))):
        failures.append(f"answer 未包含任一关键词：{case.get('must_include_any')}")

    if not contains_none(answer, as_list(case.get("must_not_include"))):
        failures.append(f"answer 包含禁止关键词：{case.get('must_not_include')}")

    if case.get("requires_sources") and not sources and not fallback_ok:
        failures.append("sources 为空，且不是可接受的 fallback / 拒答")

    required_card_type = case.get("requires_cards_type")
    if required_card_type and not any(card.get("type") == required_card_type for card in cards if isinstance(card, dict)):
        failures.append(f"cards 未包含类型：{required_card_type}")

    max_confidence = case.get("max_confidence")
    if max_confidence is not None and float(response.get("confidence", 0.0)) > float(max_confidence):
        failures.append(f"confidence={response.get('confidence')} 高于上限 {max_confidence}")

    return {
        "id": case["id"],
        "question": case["question"],
        "passed": not failures,
        "failures": failures,
        "intent": response.get("intent"),
        "selected_tool": response.get("selected_tool"),
        "confidence": response.get("confidence"),
        "answer_preview": answer[:180],
    }


def parse_stream_events(question: str) -> list[dict[str, Any]]:
    events = []
    for line in _stream_chat_events(ChatRequest(question=question)):
        stripped = line.strip()
        if stripped:
            events.append(json.loads(stripped))
    return events


def evaluate_stream_case(case: dict[str, Any]) -> dict[str, Any]:
    events = parse_stream_events(case["question"])
    event_types = [event.get("type") for event in events]
    metadata = next((event for event in events if event.get("type") == "metadata"), {})
    answer = "".join(str(event.get("content", "")) for event in events if event.get("type") == "chunk")
    failures = []
    fallback_ok = bool(case.get("allow_fallback")) and is_allowed_fallback(answer)

    for event_type in as_list(case.get("expected_event_types")):
        if event_type not in event_types:
            failures.append(f"缺少 stream event：{event_type}")

    passed, detail = check_equal_or_any(metadata.get("selected_tool", ""), case, "expected_tool")
    if not passed:
        failures.append(detail)

    if not fallback_ok and not contains_any(answer, as_list(case.get("must_include_any"))):
        failures.append(f"stream chunk 未包含任一关键词：{case.get('must_include_any')}")

    if not contains_none(answer, as_list(case.get("must_not_include"))):
        failures.append(f"stream chunk 包含禁止关键词：{case.get('must_not_include')}")

    return {
        "id": case["id"],
        "question": case["question"],
        "passed": not failures,
        "failures": failures,
        "intent": metadata.get("intent"),
        "selected_tool": metadata.get("selected_tool"),
        "confidence": metadata.get("confidence"),
        "answer_preview": answer[:180],
        "event_types": event_types,
    }


def evaluate_case(case: dict[str, Any], agent) -> dict[str, Any]:
    if case.get("endpoint") == "stream":
        return evaluate_stream_case(case)
    return evaluate_chat_case(case, agent)


def main() -> None:
    cases = load_cases()
    agent = create_travel_agent()
    results = [evaluate_case(case, agent) for case in cases]

    passed_count = 0
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        if result["passed"]:
            passed_count += 1
        print(f"[{status}] {result['id']} - {result['question']}")
        print(f"  intent={result.get('intent')} tool={result.get('selected_tool')} confidence={result.get('confidence')}")
        if result.get("answer_preview"):
            print(f"  {result['answer_preview']}")
        for failure in result.get("failures", []):
            print(f"  - {failure}")

    total = len(results)
    print(f"\nEval 汇总：{passed_count}/{total} 通过")
    if passed_count != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
