from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.ingestion.pipeline import run_ingestion_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="构建或增量更新 Travel Agent RAG 知识库")
    parser.add_argument("--mode", choices=["full", "incremental"], default="incremental")
    args = parser.parse_args()

    result = run_ingestion_pipeline(mode=args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
