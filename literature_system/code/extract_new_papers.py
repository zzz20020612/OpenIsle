"""对新解析的论文运行第三阶段提取"""
import argparse
import sys
sys.path.insert(0, '.')

from phase3.extractor import extract_all_in_one
from phase3.embedder import embed_batch
from phase3.job_tracker import get_papers_needing_extraction
from phase3.llm_client import LLMClient
import config
from logger import get_logger

logger = get_logger("extract_new_papers")


def get_newly_parsed_papers():
    """获取尚未进行第三阶段提取的已解析论文。

    复用 job_tracker，支持部分失败重试。
    """
    return get_papers_needing_extraction()


def _count_result(result: dict, pid: int, stats: dict):
    """统计单篇提取结果。"""
    if "card" in result:
        claims = len(result["card"].get("key_claims", []))
        print(f"  知识卡片: OK (claims={claims})")
        stats["kc"] += 1
    if "methods" in result:
        steps = len(result["methods"].get("workflow", []))
        print(f"  方法流程: OK (steps={steps})")
        stats["methods"] += 1
    if "data_points" in result:
        dps = result["data_points"]
        count = len(dps) if isinstance(dps, list) else dps.get("count", 0)
        print(f"  数据数值: OK (count={count})")
        stats["dp_count"] += count


def main(force: bool = False):
    paper_ids = get_newly_parsed_papers()
    print(f"找到 {len(paper_ids)} 篇待提取论文: {paper_ids}")

    if not paper_ids:
        print("没有待提取论文")
        return

    llm = LLMClient()

    stats = {"kc": 0, "methods": 0, "dp_count": 0}
    errors = []

    # 第一轮：全部待提炼论文
    for pid in paper_ids:
        print(f"\n--- 首轮 paper_id={pid} ---")
        try:
            result = extract_all_in_one(pid, llm, force=force)
            _count_result(result, pid, stats)
        except Exception as e:
            print(f"  提炼失败: FAIL - {e}")
            errors.append(f"extract({pid}): {e}")

    # 第二轮：对首轮仍失败的论文执行一次性重试
    retry_ids = get_papers_needing_extraction()
    # 过滤掉第一轮未覆盖的论文，避免意外大量重试
    retry_ids = [pid for pid in retry_ids if pid in set(paper_ids)]
    if retry_ids:
        print(f"\n--- 第二轮重试 {len(retry_ids)} 篇 ---")
        for pid in retry_ids:
            print(f"\n--- 重试 paper_id={pid} ---")
            try:
                result = extract_all_in_one(pid, llm, force=True)
                _count_result(result, pid, stats)
            except Exception as e:
                print(f"  重试失败: FAIL - {e}")
                errors.append(f"retry({pid}): {e}")

    # 3.4 向量化：覆盖首轮论文 + 重试成功的论文
    all_pids = list(set(paper_ids) | set(retry_ids))
    print("\n--- 向量化 ---")
    if not config.EMBEDDING_API_KEY:
        print("  向量化: SKIPPED - EMBEDDING_API_KEY 未配置")
    else:
        try:
            embed_batch(all_pids)
            print("  向量化: OK")
        except Exception as e:
            print(f"  向量化: FAIL - {e}")
            errors.append(f"embed: {e}")

    # 汇总
    print("\n" + "=" * 60)
    print("第三阶段提取汇总")
    print("=" * 60)
    print(f"  论文数: {len(paper_ids)} / 重试: {len(retry_ids)}")
    print(f"  知识卡片: {stats['kc']}/{len(paper_ids)}")
    print(f"  方法流程: {stats['methods']}/{len(paper_ids)}")
    print(f"  数据数值: {stats['dp_count']} 条")
    if errors:
        print(f"  错误 ({len(errors)}):")
        for err in errors:
            print(f"    - {err}")
    else:
        print("  全部通过!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="对新解析论文运行第三阶段 LLM 提取")
    parser.add_argument("--force", action="store_true", help="强制重新提取（覆盖已有结果）")
    args = parser.parse_args()
    main(force=args.force)
