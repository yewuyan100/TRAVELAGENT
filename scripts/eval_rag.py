import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.pipeline import UNCERTAIN_ANSWER, create_pipeline


EVAL_CASES_PATH = PROJECT_ROOT / "tests" / "eval_cases.json"


def evaluate_case(case: dict, pipeline) -> dict:
    question = case["question"]
    expected = case["expected"]
    analysis = pipeline.retriever.analyze_query(question)

    if expected == "should_refuse_realtime_without_tool":
        result = pipeline.run(question)
        passed = analysis.needs_realtime and UNCERTAIN_ANSWER in result.answer
    elif expected == "should_not_hallucinate":
        result = pipeline.run(question)
        passed = UNCERTAIN_ANSWER in result.answer
    else:
        report = pipeline.retriever.retrieve_with_report(question)
        result = None
        passed = report.is_confident and bool(report.results)

    return {
        "id": case["id"],
        "question": question,
        "expected": expected,
        "passed": passed,
        "analysis": analysis.to_dict(),
        "answer_preview": "" if result is None else result.answer[:160],
    }


def main() -> None:
    pipeline = create_pipeline()
    cases = json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8-sig"))
    results = [evaluate_case(case, pipeline) for case in cases]

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {result['id']} - {result['question']}")
        if result["answer_preview"]:
            print(f"  {result['answer_preview']}")

    failed = [result for result in results if not result["passed"]]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
