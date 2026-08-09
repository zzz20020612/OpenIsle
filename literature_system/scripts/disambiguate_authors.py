#!/usr/bin/env python3
"""
作者消歧脚本
自动识别并合并重复的作者记录

消歧规则：
1. ORCID 完全相同 -> 合并
2. 姓名 + 机构完全相同 -> 合并
3. 姓名相似度高 + 有共同论文 -> 合并（需要人工确认）

使用方法：
    python scripts/disambiguate_authors.py [--dry-run] [--auto-merge]
    
参数：
    --dry-run      仅检测，不执行合并
    --auto-merge   自动合并高置信度的重复记录（ORCID 或 姓名+机构）
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

# 添加项目路径（code/ 目录）
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root / "code"))

from db import get_connection
from logger import get_logger

logger = get_logger(__name__)


def normalize_name(name):
    """标准化作者姓名"""
    if not name:
        return ""
    # 移除多余空格，转小写
    return " ".join(name.strip().lower().split())


def name_similarity(name1, name2):
    """计算姓名相似度 (0-1)"""
    if not name1 or not name2:
        return 0
    return SequenceMatcher(None, normalize_name(name1), normalize_name(name2)).ratio()


def get_all_authors():
    """获取所有作者及其关联信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            a.id,
            a.full_name,
            a.orcid,
            a.affiliation,
            COUNT(DISTINCT pa.paper_id) as paper_count
        FROM authors a
        LEFT JOIN paper_authors pa ON a.id = pa.author_id
        GROUP BY a.id
        ORDER BY a.full_name, a.id
    """)
    
    authors = []
    for row in cursor.fetchall():
        authors.append({
            'id': row[0],
            'full_name': row[1],
            'orcid': row[2],
            'affiliation': row[3],
            'paper_count': row[4]
        })
    
    conn.close()
    return authors


def get_author_papers(author_id):
    """获取作者的所有论文 ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT paper_id FROM paper_authors WHERE author_id = ?
    """, (author_id,))
    
    papers = set(row[0] for row in cursor.fetchall())
    conn.close()
    return papers


def find_duplicates_by_orcid(authors):
    """按 ORCID 查找重复"""
    orcid_groups = defaultdict(list)
    
    for author in authors:
        if author['orcid']:
            orcid_groups[author['orcid']].append(author)
    
    # 只返回有重复的组
    return {k: v for k, v in orcid_groups.items() if len(v) > 1}


def find_duplicates_by_name_affiliation(authors):
    """按姓名+机构查找重复"""
    groups = defaultdict(list)
    
    for author in authors:
        if author['full_name'] and author['affiliation']:
            key = (normalize_name(author['full_name']), 
                   normalize_name(author['affiliation']))
            groups[key].append(author)
    
    # 只返回有重复的组
    return {k: v for k, v in groups.items() if len(v) > 1}


def find_duplicates_by_name_coauthor(authors, threshold=0.85):
    """按姓名相似度+共同论文查找重复（需要人工确认）"""
    candidates = []
    
    # 按姓名首字母分组，减少比较次数
    name_groups = defaultdict(list)
    for author in authors:
        if author['full_name']:
            first_letter = normalize_name(author['full_name'])[0]
            name_groups[first_letter].append(author)
    
    # 在每个分组内比较
    for letter, group in name_groups.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a1 = group[i]
                a2 = group[j]
                
                sim = name_similarity(a1['full_name'], a2['full_name'])
                if sim >= threshold:
                    # 检查是否有共同论文
                    papers1 = get_author_papers(a1['id'])
                    papers2 = get_author_papers(a2['id'])
                    common_papers = papers1 & papers2
                    
                    if common_papers:
                        candidates.append({
                            'author1': a1,
                            'author2': a2,
                            'similarity': sim,
                            'common_papers': len(common_papers)
                        })
    
    return candidates


def merge_authors(primary_id, duplicate_ids):
    """合并作者记录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 更新 paper_authors 表
        for dup_id in duplicate_ids:
            # 先检查是否有冲突（同一论文不能有两个作者记录）
            cursor.execute("""
                SELECT paper_id FROM paper_authors 
                WHERE author_id = ?
            """, (dup_id,))
            dup_papers = [row[0] for row in cursor.fetchall()]
            
            for paper_id in dup_papers:
                # 检查主作者是否已经有这篇论文
                cursor.execute("""
                    SELECT author_id FROM paper_authors 
                    WHERE paper_id = ? AND author_id = ?
                """, (paper_id, primary_id))
                
                if cursor.fetchone():
                    # 主作者已有此论文，删除重复记录
                    cursor.execute("""
                        DELETE FROM paper_authors 
                        WHERE author_id = ? AND paper_id = ?
                    """, (dup_id, paper_id))
                else:
                    # 转移论文关联
                    cursor.execute("""
                        UPDATE paper_authors 
                        SET author_id = ? 
                        WHERE author_id = ? AND paper_id = ?
                    """, (primary_id, dup_id, paper_id))
        
        # 删除重复作者
        placeholders = ','.join(['?'] * len(duplicate_ids))
        cursor.execute(f"""
            DELETE FROM authors WHERE id IN ({placeholders})
        """, duplicate_ids)
        
        conn.commit()
        return True, f"成功合并 {len(duplicate_ids)} 条记录"
        
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='作者消歧脚本')
    parser.add_argument('--dry-run', action='store_true', 
                       help='仅检测，不执行合并')
    parser.add_argument('--auto-merge', action='store_true',
                       help='自动合并高置信度的重复记录')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("开始作者消歧分析")
    logger.info("=" * 60)
    
    # 获取所有作者
    authors = get_all_authors()
    logger.info(f"总作者数: {len(authors)}")
    
    # 1. 按 ORCID 查找
    logger.info("\n[1/3] 按 ORCID 查找重复...")
    orcid_dups = find_duplicates_by_orcid(authors)
    if orcid_dups:
        logger.info(f"发现 {len(orcid_dups)} 组 ORCID 重复")
        for orcid, group in orcid_dups.items():
            logger.info(f"  ORCID {orcid}:")
            for a in group:
                logger.info(f"    - ID {a['id']}: {a['full_name']} ({a['paper_count']} 篇)")
            
            if args.auto_merge and not args.dry_run:
                primary = group[0]
                duplicates = [a['id'] for a in group[1:]]
                success, msg = merge_authors(primary['id'], duplicates)
                if success:
                    logger.info(f"    ✓ 已合并到 ID {primary['id']}")
                else:
                    logger.error(f"    ✗ 合并失败: {msg}")
    else:
        logger.info("未发现 ORCID 重复")
    
    # 2. 按姓名+机构查找
    logger.info("\n[2/3] 按姓名+机构查找重复...")
    name_aff_dups = find_duplicates_by_name_affiliation(authors)
    if name_aff_dups:
        logger.info(f"发现 {len(name_aff_dups)} 组姓名+机构重复")
        for (name, aff), group in name_aff_dups.items():
            logger.info(f"  {name} @ {aff}:")
            for a in group:
                logger.info(f"    - ID {a['id']}: {a['full_name']} ({a['paper_count']} 篇)")
            
            if args.auto_merge and not args.dry_run:
                primary = group[0]
                duplicates = [a['id'] for a in group[1:]]
                success, msg = merge_authors(primary['id'], duplicates)
                if success:
                    logger.info(f"    ✓ 已合并到 ID {primary['id']}")
                else:
                    logger.error(f"    ✗ 合并失败: {msg}")
    else:
        logger.info("未发现姓名+机构重复")
    
    # 3. 按姓名相似度查找（仅检测）
    logger.info("\n[3/3] 按姓名相似度查找潜在重复...")
    logger.info("（此部分需要人工确认，不会自动合并）")
    candidates = find_duplicates_by_name_coauthor(authors, threshold=0.85)
    if candidates:
        logger.info(f"发现 {len(candidates)} 对潜在重复")
        for cand in candidates:
            a1 = cand['author1']
            a2 = cand['author2']
            logger.info(f"  相似度 {cand['similarity']:.2f}, 共同论文 {cand['common_papers']} 篇:")
            logger.info(f"    - ID {a1['id']}: {a1['full_name']} @ {a1['affiliation'] or '-'}")
            logger.info(f"    - ID {a2['id']}: {a2['full_name']} @ {a2['affiliation'] or '-'}")
    else:
        logger.info("未发现姓名相似的潜在重复")
    
    logger.info("\n" + "=" * 60)
    if args.dry_run:
        logger.info("检测完成（dry-run 模式，未执行合并）")
    else:
        logger.info("消歧完成")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
