"""对 Nature 系列 farm 论文执行完整 pipeline：parse → extract。

用法:
    python scripts/process_nature_farm.py
    python scripts/process_nature_farm.py --parse-only  # 仅解析
    python scripts/process_nature_farm.py --extract-only  # 仅提取
    python scripts/process_nature_farm.py --force  # 强制重新执行
"""
import sys
from pathlib import Path

_CODE_ROOT = Path(__file__).resolve().parent.parent / "code"
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

import argparse
import time

from db import get_connection
from logger import get_logger

logger = get_logger("process_nature_farm")

# 本次采集的 Nature farm 论文 paper_id 范围
NATURE_FARM_PAPER_IDS = list(range(92, 102))  # 92-101


def get_paper_info(paper_id: int) -> dict:
    conn = get_connection(init_schema=False, row_factory=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, doi, title, journal, oa_url FROM papers WHERE id=?", (paper_id,))
        row = cur.fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def parse_papers(paper_ids: list, force: bool = False):
    """执行 PDF 解析。"""
    from pdf.scheduler import process_paper

    print(f"\n{'='*60}")
    print(f"Phase 1: PDF 解析 ({len(paper_ids)} 篇)")
    print(f"{'='*60}")

    success = skipped = failed = 0
    for pid in paper_ids:
        info = get_paper_info(pid)
        title = (info.get("title") or "(no title)")[:60]
        print(f"\n[{pid}] {title}")
        try:
            result = process_paper(pid, force=force)
            status = result.get("status", "unknown")
            if status == "done":
                success += 1
                print(f"  ✓ 解析成功 (parser: {result.get('parser_used', 'unknown')})")
            elif status == "skipped":
                skipped += 1
                print(f"  → 跳过 (已有解析记录)")
            else:
                failed += 1
                print(f"  ✗ 解析失败: {result.get('error_msg', 'unknown')[:100]}")
        except Exception as e:
            failed += 1
            print(f"  ✗ 异常: {e}")

    print(f"\n解析完成: 成功={success}, 跳过={skipped}, 失败={failed}")
    return success, skipped, failed


def extract_papers(paper_ids: list, force: bool = False):
    """执行 LLM 知识提取。"""
    from phase3.extractor import extract_all_in_one
    from phase3.llm_client import LLMClient
    from phase3.embedder import embed_paper

    print(f"\n{'='*60}")
    print(f"Phase 2: LLM 知识提取 ({len(paper_ids)} 篇)")
    print(f"{'='*60}")

    llm = LLMClient()
    kc = methods = dp = errors = 0

    for pid in paper_ids:
        info = get_paper_info(pid)
        title = (info.get("title") or "(no title)")[:60]
        print(f"\n[{pid}] {title}")
        try:
            result = extract_all_in_one(pid, llm, force=force)
            if "card" in result:
                claims = len(result["card"].get("key_claims", []))
                print(f"  ✓ 知识卡片: OK (claims={claims})")
                kc += 1
            if "methods" in result:
                steps = len(result["methods"].get("workflow", []))
                print(f"  ✓ 方法流程: OK (steps={steps})")
                methods += 1
            if "data_points" in result:
                dps = result["data_points"]
                count = len(dps) if isinstance(dps, list) else dps.get("count", 0)
                print(f"  ✓ 数据数值: OK (count={count})")
                dp += count
            errs = sum(1 for k in ("card_error", "methods_error", "data_points_error") if k in result)
            if errs:
                errors += errs
                print(f"  ⚠ 部分失败: {errs} 类")

            # 向量化
            try:
                embed_paper(pid)
                print(f"  ✓ 向量化: OK")
            except Exception as e:
                print(f"  ⚠ 向量化失败: {e}")
        except Exception as e:
            errors += 1
            print(f"  ✗ 提取失败: {e}")

    print(f"\n提取完成: 知识卡片={kc}, 方法={methods}, 数据点={dp}, 错误={errors}")
    return kc, methods, dp, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parse-only", action="store_true")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    run_parse = not args.extract_only
    run_extract = not args.parse_only

    print(f"处理 Nature 系列 farm 论文 ({len(NATURE_FARM_PAPER_IDS)} 篇)")
    print(f"paper_id: {NATURE_FARM_PAPER_IDS}")
    print(f"force={args.force}")

    if run_parse:
        parse_papers(NATURE_FARM_PAPER_IDS, force=args.force)

    if run_extract:
        extract_papers(NATURE_FARM_PAPER_IDS, force=args.force)

    print(f"\n{'='*60}")
    print("全部完成!")


if __name__ == "__main__":
    main()