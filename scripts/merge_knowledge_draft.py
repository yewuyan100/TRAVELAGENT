from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = PROJECT_ROOT / "data" / "knowledge" / "travel_knowledge.json"
DEFAULT_DRAFT = PROJECT_ROOT / "data" / "knowledge_drafts" / "travel_guide_import.json"
DEFAULT_RAW = PROJECT_ROOT / "data" / "raw" / "static" / "travel_knowledge.json"


def load_json_list(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"{path} 最外层必须是 JSON 数组")
    return data


def write_json(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="把审核后的知识草稿合并进 travel_knowledge.json")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--out", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--raw-out", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--copy-raw", action="store_true", help="同步写入 data/raw/static/travel_knowledge.json")
    args = parser.parse_args()

    base_items = load_json_list(args.base)
    draft_items = load_json_list(args.draft)
    merged_by_id = {str(item.get("id") or item.get("doc_id")): item for item in base_items}

    inserted = 0
    replaced = 0
    for item in draft_items:
        item_id = str(item.get("id") or item.get("doc_id") or "").strip()
        if not item_id:
            continue
        if item_id in merged_by_id:
            replaced += 1
        else:
            inserted += 1
        merged_by_id[item_id] = item

    if args.out.resolve() == args.base.resolve() and args.base.exists():
        backup = args.base.with_name(
            f"{args.base.stem}.backup_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}{args.base.suffix}"
        )
        shutil.copy2(args.base, backup)
    else:
        backup = None

    merged = list(merged_by_id.values())
    write_json(args.out, merged)

    if args.copy_raw:
        write_json(args.raw_out, merged)

    result = {
        "base_count": len(base_items),
        "draft_count": len(draft_items),
        "merged_count": len(merged),
        "inserted": inserted,
        "replaced": replaced,
        "out": str(args.out),
        "raw_out": str(args.raw_out) if args.copy_raw else None,
        "backup": str(backup) if backup else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
