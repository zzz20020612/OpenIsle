"""
PDF 批量下载模块
从 DOI 或 oa_url 批量下载学术论文 PDF

使用方法:
    python pdf_downloader.py --limit 10
    python pdf_downloader.py --doi 10.3897/arphapreprints.e142608
    python pdf_downloader.py --all --resume
"""
import os
import sys
import json
import time
import hashlib
import argparse
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import config

# scansci-pdf 桥接层（可选增强）
try:
    from . import scansci_bridge
except ImportError:
    import scansci_bridge

# PDF 下载目录
PDF_DIR = Path(config.PDF_DOWNLOAD_DIR or Path(__file__).parent.parent / "pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)

# 已下载记录文件
DOWNLOADED_FILE = PDF_DIR / "downloaded.json"


def load_downloaded():
    """加载已下载记录"""
    if DOWNLOADED_FILE.exists():
        with open(DOWNLOADED_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()


def save_downloaded(downloaded_set):
    """保存已下载记录"""
    with open(DOWNLOADED_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(downloaded_set), f, ensure_ascii=False, indent=2)


def get_file_hash(content):
    """计算文件内容哈希"""
    return hashlib.md5(content[:10000]).hexdigest()[:8]


def download_pdf(url, doi, timeout=60, max_retries=3):
    """
    下载单个 PDF 并保存到 PDF_DIR。

    Args:
        url: PDF 下载链接
        doi: DOI 用于命名和记录
        timeout: 超时时间(秒)
        max_retries: 最大重试次数

    Returns:
        (success, file_path, error_message)
    """
    if not url:
        return False, None, "URL 为空"

    # 清理 DOI 用于文件名（Windows 合法字符）
    if doi:
        safe_doi = doi.replace('/', '_').replace(':', '_').replace('\\', '_').replace('?', '_').replace('*', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')[:120]
    else:
        safe_doi = hashlib.md5(url.encode()).hexdigest()[:12]
    file_path = PDF_DIR / f"{safe_doi}.pdf"

    headers = {
        "User-Agent": config.PDF_USER_AGENT,
        "Accept": "application/pdf,application/octet-stream,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)

            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()

                # 检查是否是 PDF
                if 'pdf' in content_type or response.content[:4] == b'%PDF':
                    # 直接保存文件（避免调用方重复下载）
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    return True, str(file_path), None
                else:
                    return False, None, f"不是 PDF 文件 (content-type: {content_type})"

            elif response.status_code == 403:
                return False, None, "403 禁止访问"
            elif response.status_code == 404:
                return False, None, "404 文件不存在"
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 5
                print(f"    限流，等待 {wait_time} 秒...")
                time.sleep(wait_time)
                continue
            else:
                return False, None, f"HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            return False, None, "请求超时"
        except requests.exceptions.ConnectionError as e:
            return False, None, f"连接错误: {str(e)[:50]}"
        except Exception as e:
            return False, None, f"异常: {str(e)[:50]}"

    return False, None, f"重试 {max_retries} 次后失败"


def get_pdf_url_from_doi(doi, timeout=30):
    """
    通过 DOI 从多个策略获取 PDF 链接
    
    策略优先级 (可在 config.py 或 .env 中配置):
    1. Crossref API - intended-application=text-mining 的 PDF 链接
    2. Crossref API - application/pdf 类型的链接
    3. oa_url 直接使用
    4. doi.org 重定向（机构网络会直接授权）
    5. Unpaywall API 查找合法 OA 版本
    
    Args:
        doi: DOI 标识符
        timeout: 超时时间
    
    Returns:
        PDF URL 或 None
    """
    if not doi:
        return None
    
    # 获取策略优先级配置
    strategy = config.PDF_DOWNLOAD_STRATEGY
    headers = {
        "User-Agent": config.PDF_USER_AGENT,
        "mailto": config.CROSSREF_MAILTO
    }
    
    # 按优先级尝试各策略
    strategies = [
        ("crossref_text_mining", _get_crossref_pdf_url),
        ("crossref_pdf", lambda d, t, h: _get_crossref_pdf_url(d, t, h, prefer_text_mining=False)),
        ("oa_url", lambda d, t, h: None),  # oa_url 由调用方传入
        ("doi_redirect", _get_doi_redirect_url),
        ("unpaywall", _get_unpaywall_url),
    ]
    
    for name, func in strategies:
        priority = strategy.get(name, 99)
        if priority == 0 or priority > 99:
            continue  # 跳过禁用的策略
        
        try:
            if name == "oa_url":
                continue  # oa_url 由调用方处理
            
            url = func(doi, timeout, headers)
            if url:
                return url
        except Exception as e:
            print(f"    [{name}] 策略失败: {e}")
    
    return None


def download_pdf_with_fallback(doi, oa_url=None, timeout=60, max_retries=2):
    """Download a PDF by trying every configured source in priority order.

    ``get_pdf_url_from_doi`` is retained for SDK compatibility, but it returns
    only one candidate. The processing workflow must continue when that URL is
    an HTML landing page, blocked by a publisher, or otherwise not a PDF.
    """
    if not doi and not oa_url:
        return False, None, "DOI and OA URL are both empty"

    strategy = config.PDF_DOWNLOAD_STRATEGY
    headers = {
        "User-Agent": config.PDF_USER_AGENT,
        "mailto": config.CROSSREF_MAILTO,
    }
    providers = [
        ("crossref_text_mining", lambda: _get_crossref_pdf_url(doi, timeout, headers)),
        ("crossref_pdf", lambda: _get_crossref_pdf_url(doi, timeout, headers, prefer_text_mining=False)),
        ("oa_url", lambda: oa_url),
        ("doi_redirect", lambda: _get_doi_redirect_url(doi, timeout, headers)),
        ("unpaywall", lambda: _get_unpaywall_url(doi, timeout, headers)),
    ]
    providers.sort(key=lambda item: strategy.get(item[0], 99))

    attempted = set()
    errors = []
    for name, resolve in providers:
        priority = strategy.get(name, 99)
        if priority <= 0 or priority > 99:
            continue
        try:
            url = resolve()
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            continue
        if not url or url in attempted:
            continue
        attempted.add(url)
        success, file_path, error = download_pdf(
            url,
            doi,
            timeout=timeout,
            max_retries=max_retries,
        )
        if success:
            return True, file_path, None
        errors.append(f"{name}: {error}")

    return False, None, "; ".join(errors) if errors else "No PDF URL candidate was found"


def _get_crossref_pdf_url(doi, timeout, headers, prefer_text_mining=True):
    """策略1-2: 从 Crossref API 获取 PDF 链接"""
    try:
        url = f'https://api.crossref.org/works/{doi}'
        response = requests.get(url, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json().get('message', {})
            links = data.get('link', [])
            
            # 优先选择 text-mining 或 similarity-checking 类型的 PDF
            if prefer_text_mining:
                for link in links:
                    link_url = link.get('URL', '')
                    content_type = link.get('content-type', '').lower()
                    intended_app = link.get('intended-application', '').lower()
                    
                    if 'pdf' in content_type or intended_app in ['text-mining', 'similarity-checking']:
                        if 'xml' not in content_type and link_url:
                            return link_url
            
            # 如果没有 text-mining 类型，返回第一个 PDF 链接
            for link in links:
                link_url = link.get('URL', '')
                content_type = link.get('content-type', '').lower()
                if 'pdf' in content_type and 'xml' not in content_type:
                    return link_url
                    
    except Exception as e:
        print(f"    [crossref] API 查询失败: {e}")
    
    return None


def _get_doi_redirect_url(doi, timeout, headers):
    """策略4: doi.org 重定向"""
    try:
        doi_url = f'https://doi.org/{doi}'
        headers2 = {
            "User-Agent": config.PDF_USER_AGENT,
            "Accept": "application/pdf,text/html,*/*"
        }
        response = requests.get(doi_url, headers=headers2, timeout=timeout, allow_redirects=True)
        
        final_url = response.url
        final_content_type = response.headers.get('content-type', '').lower()
        
        # 如果直接返回 PDF
        if 'pdf' in final_content_type or final_url.lower().endswith('.pdf'):
            return final_url
        
        # 如果返回 HTML，尝试构造 PDF URL
        if 'text/html' in final_content_type:
            # ScienceDirect / Elsevier
            if 'sciencedirect.com' in final_url.lower():
                return final_url + ('/pdfft' if not final_url.endswith('/pdfft') else '')
            
            # Wiley
            if 'onlinelibrary.wiley.com' in final_url.lower():
                return final_url.replace('/doi/', '/doi/pdfdirect/')
            
            # Springer
            if 'link.springer.com' in final_url.lower():
                return final_url + '.pdf'
            
            # 返回 DOI URL
            return doi_url
            
    except Exception as e:
        print(f"    [doi_redirect] 重定向失败: {e}")
    
    return None


def _get_unpaywall_url(doi, timeout, headers):
    """策略5: Unpaywall API 查找 OA 版本"""
    try:
        url = f'https://api.unpaywall.org/v2/{doi}'
        params = {"email": config.UNPAYWALL_EMAIL}
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            # 查找 best_oa_location
            best_oa = data.get('best_oa_location', {})
            if best_oa:
                best_pdf = best_oa.get('url_for_pdf')
                if best_pdf:
                    return best_pdf
            
            # 备选：查找其他 OA location
            oa_locations = data.get('oa_locations', [])
            for loc in oa_locations:
                pdf_url = loc.get('url_for_pdf')
                if pdf_url:
                    return pdf_url
                    
    except Exception as e:
        print(f"    [unpaywall] API 查询失败: {e}")
    
    return None


def download_single_pdf(doi, oa_url, force=False):
    """
    下载单个 DOI 的 PDF

    Returns:
        (success, message, saved_path)
    """
    # 检查是否已下载
    downloaded = load_downloaded()
    if doi in downloaded and not force:
        # 文件存在则跳过
        safe_doi = doi.replace('/', '_') if doi else "unknown"
        existing = PDF_DIR / f"{safe_doi}.pdf"
        if existing.exists():
            return True, "已存在，跳过", str(existing)

    # 新增：优先使用 scansci-pdf 白源桥接（如果启用）
    if getattr(config, "PDF_ENABLE_SCISCI", False):
        safe_doi = (
            doi.replace('/', '_').replace(':', '_').replace('\\', '_')
            .replace('?', '_').replace('*', '_').replace('"', '_')
            .replace('<', '_').replace('>', '_').replace('|', '_')[:120]
            if doi else "unknown"
        )
        target_path = PDF_DIR / f"{safe_doi}.pdf"
        print(f"    [scansci-pdf] 尝试多源下载: {doi}")
        try:
            sci_res = scansci_bridge.try_download(doi, oa_url=oa_url, output_path=target_path)
            if sci_res and sci_res.get("success"):
                file_size = sci_res.get("size_kb", 0)
                source = sci_res.get("source", "unknown")
                if doi:
                    downloaded.add(doi)
                    save_downloaded(downloaded)
                return True, f"成功 ({file_size:.1f} KB, source={source})", str(target_path)
            else:
                err_class = sci_res.get("error_class") if sci_res else None
                err_msg = sci_res.get("error") if sci_res else "scansci-pdf 未返回结果"
                print(f"    [scansci-pdf] 失败 [{err_class}]: {err_msg}")
        except Exception as e:
            print(f"    [scansci-pdf] 异常: {e}")
        # 桥接失败后回退到原有逻辑

    # 逐个尝试已配置来源。出版社链接常返回 HTML/403，不能因为第一个
    # 候选失败就放弃后续的 Unpaywall 或 OA 镜像。
    success, file_path, error = download_pdf_with_fallback(
        doi,
        oa_url=oa_url,
        timeout=config.PDF_DOWNLOAD_TIMEOUT,
        max_retries=config.PDF_MAX_RETRIES,
    )
    if not success:
        return False, error, None

    # 记录已下载
    if doi:
        downloaded.add(doi)
        save_downloaded(downloaded)

    file_size = Path(file_path).stat().st_size / 1024 if file_path else 0
    return True, f"成功 ({file_size:.1f} KB)", file_path


def process_papers_from_db(keyword=None, limit=None, resume=False, max_workers=3):
    """
    从数据库处理论文并下载 PDF
    
    Args:
        keyword: 关键词过滤（可选）
        limit: 限制处理数量
        resume: 是否跳过已下载
        max_workers: 并行下载数
    
    Returns:
        处理统计
    """
    import sqlite3
    
    db_path = config.SQLITE_PATH
    if not db_path:
        print("错误: 未配置 SQLITE_PATH")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 查询论文
    if keyword:
        query = """
            SELECT doi, oa_url, title 
            FROM papers 
            WHERE (doi IS NOT NULL AND doi != '') 
            AND (oa_url IS NOT NULL AND oa_url != '')
            AND (title LIKE ? OR oa_url LIKE ?)
            LIMIT ?
        """
        params = (f'%{keyword}%', f'%{keyword}%', limit or 999999)
    else:
        query = """
            SELECT doi, oa_url, title 
            FROM papers 
            WHERE doi IS NOT NULL AND doi != ''
            LIMIT ?
        """
        params = (limit or 999999,)
    
    cur.execute(query, params)
    papers = cur.fetchall()
    conn.close()
    
    print(f"从数据库找到 {len(papers)} 篇论文")
    
    # 统计
    stats = {
        'total': len(papers),
        'success': 0,
        'skipped': 0,
        'failed': 0,
    }
    
    downloaded = load_downloaded() if resume else set()
    
    def process_one(paper):
        doi, oa_url, title = paper
        title_short = title[:40] if title else 'N/A'
        
        # 检查是否已下载
        if resume and doi in downloaded:
            return 'skipped', doi, title_short
        
        # 下载
        success, msg, path = download_single_pdf(doi, oa_url, force=False)
        
        if success:
            return 'success', doi, f"{msg} | {title_short}"
        else:
            return 'failed', doi, f"{msg} | {title_short}"
    
    print(f"\n开始下载（并行数: {max_workers}）...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_one, paper): paper for paper in papers}
        
        for i, future in enumerate(as_completed(futures), 1):
            status, doi, msg = future.result()
            
            if status == 'success':
                stats['success'] += 1
                symbol = '✓'
            elif status == 'skipped':
                stats['skipped'] += 1
                symbol = '-'
            else:
                stats['failed'] += 1
                symbol = '✗'
            
            print(f"[{i}/{len(papers)}] {symbol} {doi}: {msg}")
            
            # 礼貌限流
            time.sleep(1)
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"下载完成！耗时: {elapsed:.1f} 秒")
    print(f"成功: {stats['success']} | 跳过: {stats['skipped']} | 失败: {stats['failed']}")
    print(f"保存目录: {PDF_DIR}")
    print(f"{'='*60}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='PDF 批量下载工具')
    parser.add_argument('--doi', type=str, help='单个 DOI 下载')
    parser.add_argument('--limit', type=int, help='限制处理数量')
    parser.add_argument('--keyword', type=str, help='关键词过滤')
    parser.add_argument('--resume', action='store_true', help='跳过已下载')
    parser.add_argument('--workers', type=int, default=3, help='并行下载数')
    parser.add_argument('--force', action='store_true', help='强制重新下载')
    
    args = parser.parse_args()
    
    print(f"PDF 保存目录: {PDF_DIR}")
    print(f"已下载记录: {DOWNLOADED_FILE}")
    print()
    
    if args.doi:
        # 单个 DOI 下载
        print(f"下载单个 DOI: {args.doi}")
        success, msg, path = download_single_pdf(args.doi, None, force=args.force)
        print(f"结果: {'成功' if success else '失败'} - {msg}")
        if path:
            print(f"文件: {path}")
    else:
        # 从数据库批量下载
        process_papers_from_db(
            keyword=args.keyword,
            limit=args.limit,
            resume=args.resume,
            max_workers=args.workers
        )


if __name__ == '__main__':
    main()
