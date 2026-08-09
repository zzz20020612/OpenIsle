"""
数据质量定期报告生成器

定期运行 dq_checker，输出带时间戳的报告并维护历史趋势。
报告结构：
  dq_output/
  ├── dq_issues.csv            # 最新一次的问题清单
  ├── dq_report.json           # 最新一次的总报告
  ├── trend.json               # 历史趋势（每次运行追加一行）
  └── history/
      └── YYYY-MM-DD_HHMMSS/
          ├── dq_issues.csv
          └── dq_report.json

使用方式：
  # 单次生成
  python dq_report_generator.py

  # 每周生成（搭配 cron/Task Scheduler）
  python dq_report_generator.py --period weekly

  # 仅对比上次报告（不重新检查）
  python dq_report_generator.py --diff
"""
import json
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 确保独立运行时能找到同级模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from logger import get_logger
from quality.checker import run_all_checks

LOGGER = get_logger("dq_report")

DEFAULT_OUTPUT_DIR = config.ROOT_DIR / "db" / "dq_output"
TREND_FILE = DEFAULT_OUTPUT_DIR / "trend.json"
HISTORY_DIR = DEFAULT_OUTPUT_DIR / "history"


def generate_report(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict:
    """生成一份 DQ 报告，归档到 history 并更新 trend。"""
    # 1. 运行检查（结果会写入 output_dir/dq_issues.csv 与 dq_report.json）
    result = run_all_checks(output_dir)
    metrics = result["metrics"]
    by_dim = result["by_dimension"]

    # 2. 归档到 history（同秒时追加序号保证唯一）
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_dir = HISTORY_DIR / ts
    suffix = 1
    while archive_dir.exists() and any(archive_dir.iterdir()):
        archive_dir = HISTORY_DIR / f"{ts}_{suffix:02d}"
        suffix += 1
    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_dir / "dq_issues.csv", archive_dir / "dq_issues.csv")
    shutil.copy2(output_dir / "dq_report.json", archive_dir / "dq_report.json")

    # 3. 追加到 trend.json
    snapshot = {
        "timestamp": ts,
        "total_papers": metrics.get("total_papers", 0),
        "total_issues": result["total_issues"],
        "by_dimension": by_dim,
        "key_metrics": {
            "doi_completeness": metrics.get("doi_completeness", 0),
            "abstract_completeness": metrics.get("abstract_completeness", 0),
            "doi_valid_rate": metrics.get("doi_valid_rate", 0),
            "date_normalized_rate": metrics.get("date_normalized_rate", 0),
            "orcid_coverage": metrics.get("orcid_coverage", 0),
            "pdf_fulltext_rate": metrics.get("pdf_fulltext_rate", 0),
        },
    }
    trend = load_trend()
    trend.append(snapshot)
    TREND_FILE.write_text(json.dumps(trend, indent=2, ensure_ascii=False), encoding="utf-8")

    LOGGER.info(f"已归档到 {archive_dir}")
    LOGGER.info(f"趋势数据已写入 {TREND_FILE}（共 {len(trend)} 条历史）")
    return snapshot


def load_trend() -> List[Dict]:
    """加载趋势历史。"""
    if TREND_FILE.exists():
        try:
            return json.loads(TREND_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def diff_with_last(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict:
    """对比当前报告与上一次历史归档。"""
    history = sorted([p for p in HISTORY_DIR.glob("*") if p.is_dir()])
    if len(history) < 2:
        return {"msg": "历史归档不足 2 份，无法对比"}

    latest = history[-1]
    prev = history[-2]
    try:
        latest_report = json.loads((latest / "dq_report.json").read_text(encoding="utf-8"))
        prev_report = json.loads((prev / "dq_report.json").read_text(encoding="utf-8"))
    except Exception as e:
        return {"msg": f"读取报告失败: {e}"}

    diff = {
        "latest_ts": latest.name,
        "prev_ts": prev.name,
        "total_papers_delta": latest_report.get("total_papers", 0) - prev_report.get("total_papers", 0),
        "total_issues_delta": latest_report.get("total_issues", 0) - prev_report.get("total_issues", 0),
        "by_dimension_delta": {},
        "field_metrics_delta": {},
    }

    # 各维度变化
    prev_dim = prev_report.get("by_dimension", {})
    latest_dim = latest_report.get("by_dimension", {})
    for k in set(prev_dim) | set(latest_dim):
        delta = latest_dim.get(k, 0) - prev_dim.get(k, 0)
        if delta != 0:
            diff["by_dimension_delta"][k] = delta

    # 关键字段指标变化
    prev_metrics = prev_report.get("field_metrics", {})
    latest_metrics = latest_report.get("field_metrics", {})
    key_fields = ["doi_completeness", "abstract_completeness", "doi_valid_rate",
                  "date_normalized_rate", "orcid_coverage", "pdf_fulltext_rate"]
    for k in key_fields:
        delta = round(latest_metrics.get(k, 0) - prev_metrics.get(k, 0), 2)
        if abs(delta) >= 0.01:
            diff["field_metrics_delta"][k] = delta

    return diff


def print_trend_summary(n: int = 10) -> None:
    """打印最近 n 次趋势摘要。"""
    trend = load_trend()
    if not trend:
        LOGGER.info("无历史趋势数据")
        return

    LOGGER.info("=" * 80)
    LOGGER.info(f"DQ 趋势（最近 {min(n, len(trend))} 次 / 共 {len(trend)} 次）")
    LOGGER.info("=" * 80)
    header = f"{'时间':<22} {'论文数':>8} {'问题数':>8} {'完整性':>8} {'唯一性':>8} {'一致性':>8} {'有效性':>8} {'DOI率':>8} {'摘要率':>8}"
    LOGGER.info(header)
    for snap in trend[-n:]:
        km = snap.get("key_metrics", {})
        LOGGER.info(
            f"{snap['timestamp']:<22} {snap.get('total_papers', 0):>8} "
            f"{snap.get('total_issues', 0):>8} "
            f"{snap.get('by_dimension', {}).get('completeness', 0):>8} "
            f"{snap.get('by_dimension', {}).get('uniqueness', 0):>8} "
            f"{snap.get('by_dimension', {}).get('consistency', 0):>8} "
            f"{snap.get('by_dimension', {}).get('validity', 0):>8} "
            f"{km.get('doi_completeness', 0):>7}% "
            f"{km.get('abstract_completeness', 0):>7}%"
        )


def parse_args():
    parser = argparse.ArgumentParser(description="DQ 定期报告生成器")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录")
    parser.add_argument("--period", choices=["daily", "weekly", "monthly"], default="daily",
                        help="报告周期（仅用于日志标记）")
    parser.add_argument("--diff", action="store_true", help="仅对比上次报告")
    parser.add_argument("--trend", type=int, default=0, help="打印最近 N 次趋势摘要")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)

    if args.diff:
        result = diff_with_last(output_dir)
        LOGGER.info("=" * 60)
        LOGGER.info("DQ 报告差异（与上次对比）")
        LOGGER.info("=" * 60)
        LOGGER.info(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.trend > 0:
        print_trend_summary(args.trend)
        return

    LOGGER.info(f"[{args.period}] 生成 DQ 报告...")
    snapshot = generate_report(output_dir)
    LOGGER.info(f"快照: {snapshot}")

    if len(load_trend()) >= 2:
        diff = diff_with_last(output_dir)
        if diff.get("by_dimension_delta") or diff.get("field_metrics_delta"):
            LOGGER.info("-" * 60)
            LOGGER.info("与上次对比变化:")
            if diff.get("total_papers_delta"):
                LOGGER.info(f"  论文数变化: {diff['total_papers_delta']:+d}")
            if diff.get("total_issues_delta"):
                LOGGER.info(f"  问题数变化: {diff['total_issues_delta']:+d}")
            for k, v in diff.get("by_dimension_delta", {}).items():
                LOGGER.info(f"  {k}: {v:+d}")
            for k, v in diff.get("field_metrics_delta", {}).items():
                LOGGER.info(f"  {k}: {v:+.2f}%")


if __name__ == "__main__":
    main()
