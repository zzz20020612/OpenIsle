"""
检索 REST API 与 Python SDK

基于 Python 标准库 http.server，零额外依赖。
提供 REST API 与 Python SDK 两种调用方式，同时托管前端 SPA。

REST API 端点：
  前端：
    GET  /                        -> frontend/index.html
    GET  /static/<path>           -> 静态资源
  检索：
    GET  /search?q=...&mode=keyword&fields=title,abstract&year_from=2020&journal=...&limit=20&offset=0&sort=relevance
    GET  /aggregate?q=...&mode=keyword
    GET  /vector/search?q=...&top_k=10&chunk_type=section
    GET  /vector/stats?top_k=10&chunk_type=section
    GET  /hybrid/search?q=...&top_k=10&fts_weight=0.4&vector_weight=0.6
  论文：
    GET  /paper/<id>              论文详情
    GET  /paper/<id>/similar      相似论文推荐
    GET  /paper/<id>/knowledge    知识卡片
    GET  /paper/<id>/methods      方法流程
    GET  /paper/<id>/data_points  数据点
    GET  /paper/<id>/citations    引用网络
    GET  /compare/metric?metric_name=...&top_k=20  跨论文指标对比
  知识库：
    GET  /papers/list?q=...&sort=year_desc
    GET  /data_points/list?metric_name=...
    GET  /knowledge/list?q=...&year_from=...&year_to=...
    GET  /methods/list?q=...&year_from=...&year_to=...
    GET  /timeline?year_from=2010&year_to=2024
  管理：
    GET  /stats                   索引统计
    GET  /health                  健康检查
    POST /rebuild                 异步重建索引，返回 task_id
    POST /sync                    异步同步单篇论文，返回 task_id
    GET  /progress/<task_id>      查询任务进度

启动：
    python code/search/api.py --port 8088
    python code/search/api.py --port 8088 --host 0.0.0.0

SDK 用法：
    from search.api import SearchClient
    client = SearchClient("http://localhost:8088")
    result = client.search("livestock grazing", year_from=2020)
"""
from __future__ import annotations

import json
import argparse
import datetime
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# 确保 code/ 根目录在 sys.path 中，支持直接运行 python code/search/api.py
_CODE_ROOT = Path(__file__).resolve().parents[1]
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

import requests  # 仅 SDK 客户端需要

import config
from logger import get_logger
from db import get_connection
from search.engine import SearchEngine
from search.tasks import submit_task, get_task
import search.authors_api as authors_api
import workflow_settings as wf_settings

LOGGER = get_logger("search_api")

# 前端目录
FRONTEND_DIR = getattr(config, "FRONTEND_DIR", Path(__file__).resolve().parents[2] / "frontend")


# ============================================================
# REST API 服务端
# ============================================================
class SearchAPIHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器。"""

    # 类级别共享 SearchEngine 实例
    engine: SearchEngine = None

    def _send_json(self, status: int, data: Any):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: int, msg: str):
        self._send_json(status, {"error": msg})

    def _serve_static(self, relative_path: str):
        """托管静态文件；SPA 路由回退到 index.html。"""
        if not FRONTEND_DIR.exists():
            self._send_error(404, "前端目录不存在")
            return

        # 安全校验：防止越界访问
        target = (FRONTEND_DIR / relative_path).resolve()
        if not str(target).startswith(str(FRONTEND_DIR.resolve())):
            self._send_error(403, "非法路径")
            return

        if target.is_dir() or not target.exists():
            # SPA 回退
            target = FRONTEND_DIR / "index.html"
            if not target.exists():
                self._send_error(404, "前端入口不存在")
                return

        mime, _ = mimetypes.guess_type(str(target))
        content_type = mime or "application/octet-stream"
        try:
            data = target.read_bytes()
        except Exception as exc:
            self._send_error(500, f"读取文件失败: {exc}")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        # 开发阶段禁用静态资源缓存，避免版本更新后浏览器仍使用旧文件
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)
        LOGGER.info(f"DEBUG do_GET path={path}")

        try:
            # 静态文件 / SPA
            if path == "/" or path.startswith("/static/"):
                relative = path[1:] if path != "/" else "index.html"
                self._serve_static(relative)
                return

            if path == "/health":
                self._send_json(200, {"status": "ok", "service": "search_api"})
                return

            if path == "/stats":
                self._send_json(200, self._handle_stats())
                return

            if path == "/search":
                result = self._handle_search(qs)
                self._send_json(200, result)
                return

            if path == "/aggregate":
                result = self._handle_aggregate(qs)
                self._send_json(200, result)
                return

            if path == "/vector/search":
                result = self._handle_vector_search(qs)
                self._send_json(200, result)
                return

            if path == "/vector/stats":
                result = self._handle_vector_stats(qs)
                self._send_json(200, result)
                return

            if path == "/hybrid/search":
                result = self._handle_hybrid_search(qs)
                self._send_json(200, result)
                return

            if path == "/graph":
                result = self._handle_graph(qs)
                self._send_json(200, result)
                return

            if path == "/graph/diagnostics":
                result = self._handle_graph_diagnostics(qs)
                self._send_json(200, result)
                return

            if path == "/papers/list":
                result = self._handle_papers_list(qs)
                self._send_json(200, result)
                return

            if path == "/data_points/list":
                result = self._handle_data_points_list(qs)
                self._send_json(200, result)
                return

            if path == "/knowledge/list":
                result = self._handle_knowledge_list(qs)
                self._send_json(200, result)
                return

            if path == "/methods/list":
                result = self._handle_methods_list(qs)
                self._send_json(200, result)
                return

            if path == "/timeline":
                result = self._handle_timeline(qs)
                self._send_json(200, result)
                return

            if path == "/jobs":
                result = self._handle_jobs(qs)
                self._send_json(200, result)
                return

            if path == "/jobs/stats":
                result = self._handle_jobs_stats()
                self._send_json(200, result)
                return

            if path.startswith("/paper/"):
                result = self._handle_paper_path(path, qs)
                if result is not None:
                    self._send_json(result["status"], result["data"])
                return

            if path == "/compare/metric":
                result = self._handle_compare_metric(qs)
                self._send_json(200, result)
                return

            if path == "/authors/list":
                result = self._handle_authors_list(qs)
                self._send_json(200, result)
                return

            if path.startswith("/author/"):
                result = self._handle_author_path(path, qs)
                if result is not None:
                    self._send_json(result["status"], result["data"])
                return

            if path == "/institution/network":
                result = self._handle_institution_network(qs)
                self._send_json(200, result)
                return

            if path == "/workflow/settings":
                self._send_json(200, wf_settings.get_settings(mask_sensitive=True))
                return

            if path == "/quality/stats":
                self._send_json(200, self._handle_quality_stats())
                return

            if path == "/quality/low_quality":
                result = self._handle_quality_low_quality(qs)
                self._send_json(200, result)
                return

            if path == "/quality/prompt_compare":
                result = self._handle_quality_prompt_compare(qs)
                self._send_json(200, result)
                return

            if path.startswith("/progress/"):
                task_id = path.split("/")[-1]
                task = get_task(task_id)
                if task:
                    self._send_json(200, task)
                else:
                    self._send_error(404, "任务不存在")
                return

            self._send_error(404, f"[v2] 未知路径: {path}")
        except Exception as e:
            LOGGER.exception("处理请求失败")
            self._send_error(500, f"内部错误: {e}")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path == "/rebuild":
                task_id = submit_task(_rebuild_task)
                self._send_json(200, {"status": "ok", "task_id": task_id})
                return

            if path == "/sync":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                pid = int(data.get("paper_id", 0))
                if not pid:
                    self._send_error(400, "缺少 paper_id")
                    return
                task_id = submit_task(_sync_task, pid)
                self._send_json(200, {"status": "ok", "task_id": task_id, "paper_id": pid})
                return

            if path == "/collect":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                keyword = (data.get("keyword") or "").strip()
                if not keyword:
                    self._send_error(400, "缺少 keyword")
                    return
                rows = int(data.get("rows", 20) or 20)
                max_pages = int(data.get("max_pages", 5) or 5)
                year_from = (data.get("year_from") or "").strip()
                year_to = (data.get("year_to") or "").strip()
                journal = (data.get("journal") or "").strip()
                task_id = submit_task(_collect_task, keyword, rows, max_pages, year_from, year_to, journal)
                self._send_json(200, {"status": "ok", "task_id": task_id, "keyword": keyword})
                return

            if path == "/parse":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                source = (data.get("source") or "arxiv").strip()
                limit = int(data.get("limit", 15) or 15)
                force = bool(data.get("force", False))
                task_id = submit_task(_parse_task, source, limit, force)
                self._send_json(200, {"status": "ok", "task_id": task_id, "source": source, "limit": limit})
                return

            if path == "/extract":
                task_id = submit_task(_extract_task)
                self._send_json(200, {"status": "ok", "task_id": task_id})
                return

            if path == "/jobs/archive":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                days = int(data.get("days", 7) or 7)
                batch = int(data.get("batch", 1000) or 1000)
                task_id = submit_task(_archive_jobs_task, days, batch)
                self._send_json(200, {"status": "ok", "task_id": task_id, "days": days, "batch": batch})
                return

            if path == "/retry":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                paper_id = int(data.get("paper_id", 0) or 0)
                stage = (data.get("stage") or "").strip()
                job_id = data.get("job_id")
                if job_id is not None:
                    job_id = int(job_id)
                if not paper_id:
                    self._send_error(400, "缺少 paper_id")
                    return
                if stage not in ("parse", "extract"):
                    self._send_error(400, "stage 必须是 parse 或 extract")
                    return

                # 确定重试来源 job，用于 parent_job_id 链路追踪
                parent_job_id = job_id
                if parent_job_id is None:
                    parent_job_id = self._find_latest_failed_job(paper_id, stage)

                if stage == "parse":
                    task_id = submit_task(_retry_parse_task, paper_id, parent_job_id)
                else:
                    task_id = submit_task(_retry_extract_task, paper_id, parent_job_id)
                self._send_json(200, {
                    "status": "ok",
                    "task_id": task_id,
                    "paper_id": paper_id,
                    "stage": stage,
                    "parent_job_id": parent_job_id,
                })
                return

            if path == "/workflow/settings":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                if not isinstance(data, dict):
                    self._send_error(400, "请求体必须是 JSON 对象")
                    return
                updated = wf_settings.set_settings(data)
                wf_settings.apply_to_config()
                self._send_json(200, {"status": "ok", "settings": updated})
                return

            if path == "/quality/re_extract":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                paper_id = int(data.get("paper_id", 0) or 0)
                if not paper_id:
                    self._send_error(400, "缺少 paper_id")
                    return
                task_id = submit_task(_quality_re_extract_task, paper_id)
                self._send_json(200, {"status": "ok", "task_id": task_id, "paper_id": paper_id})
                return

            if path == "/authors/merge":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                primary_id = int(data.get("primary_id", 0) or 0)
                duplicate_ids = data.get("duplicate_ids", [])
                if not primary_id or not isinstance(duplicate_ids, list) or not duplicate_ids:
                    self._send_error(400, "缺少 primary_id 或 duplicate_ids")
                    return
                try:
                    duplicate_ids = [int(x) for x in duplicate_ids]
                    result = self._merge_authors(primary_id, duplicate_ids)
                    self._send_json(200, result)
                except Exception as e:
                    self._send_error(500, f"合并失败: {e}")
                return

            if path == "/test/connection":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                service = (data.get("service") or "").strip()
                if not service:
                    self._send_error(400, "缺少 service 参数")
                    return
                result = self._test_connection(service, data)
                self._send_json(200, result)
                return

            if path == "/pipeline/run":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
                keyword = (data.get("keyword") or "").strip()
                if not keyword:
                    self._send_error(400, "缺少 keyword")
                    return
                rows = int(data.get("rows", 20) or 20)
                max_pages = int(data.get("max_pages", 5) or 5)
                year_from = (data.get("year_from") or "").strip()
                year_to = (data.get("year_to") or "").strip()
                journal = (data.get("journal") or "").strip()
                parse_source = (data.get("parse_source") or "all").strip()
                parse_limit = int(data.get("parse_limit", 15) or 15)
                task_id = submit_task(_pipeline_task, keyword, rows, max_pages, year_from, year_to, journal, parse_source, parse_limit)
                self._send_json(200, {"status": "ok", "task_id": task_id, "keyword": keyword})
                return

            self._send_error(404, f"未知路径: {path}")
        except Exception as e:
            LOGGER.exception("处理请求失败")
            self._send_error(500, f"内部错误: {e}")

    # ------------------ 处理器辅助 ------------------
    def _merge_authors(self, primary_id: int, duplicate_ids: list) -> Dict:
        """合并重复作者记录。
        
        将 duplicate_ids 中的所有作者记录合并到 primary_id，
        更新 paper_authors 关联，保留最完整的元数据。
        
        Args:
            primary_id: 主作者 ID（保留的记录）
            duplicate_ids: 重复作者 ID 列表（将被删除）
        
        Returns:
            合并结果统计
        """
        cur = self.engine.conn.cursor()
        
        try:
            # 验证主作者存在
            cur.execute("SELECT id, full_name FROM authors WHERE id = ?", (primary_id,))
            primary = cur.fetchone()
            if not primary:
                return {"error": f"主作者 {primary_id} 不存在"}
            
            # 验证所有重复作者存在
            placeholders = ",".join("?" * len(duplicate_ids))
            cur.execute(f"SELECT id, full_name FROM authors WHERE id IN ({placeholders})", duplicate_ids)
            duplicates = cur.fetchall()
            
            if len(duplicates) != len(duplicate_ids):
                return {"error": "部分重复作者不存在"}
            
            # 获取主作者当前信息
            cur.execute("""
                SELECT * FROM authors WHERE id = ?
            """, (primary_id,))
            primary_data = dict(cur.fetchone())
            
            # 合并策略：保留最完整的元数据
            updates = {}
            for dup_id in duplicate_ids:
                cur.execute("SELECT * FROM authors WHERE id = ?", (dup_id,))
                dup_data = dict(cur.fetchone())
                
                # 如果主作者缺少某些字段，从重复记录中补充
                if not primary_data.get("orcid") and dup_data.get("orcid"):
                    updates["orcid"] = dup_data["orcid"]
                if not primary_data.get("current_affiliation") and dup_data.get("current_affiliation"):
                    updates["current_affiliation"] = dup_data["current_affiliation"]
                if not primary_data.get("given_name") and dup_data.get("given_name"):
                    updates["given_name"] = dup_data["given_name"]
                if not primary_data.get("family_name") and dup_data.get("family_name"):
                    updates["family_name"] = dup_data["family_name"]
            
            # 更新主作者元数据
            if updates:
                set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
                values = list(updates.values()) + [primary_id]
                cur.execute(f"UPDATE authors SET {set_clause} WHERE id = ?", values)
            
            # 更新 paper_authors 关联表
            # 将所有指向重复作者的记录改为指向主作者
            merged_papers = 0
            for dup_id in duplicate_ids:
                # 获取重复作者关联的所有论文
                cur.execute("""
                    SELECT paper_id FROM paper_authors WHERE author_id = ?
                """, (dup_id,))
                dup_papers = [row["paper_id"] for row in cur.fetchall()]
                
                for paper_id in dup_papers:
                    # 检查主作者是否已经关联该论文
                    cur.execute("""
                        SELECT author_id FROM paper_authors 
                        WHERE paper_id = ? AND author_id = ?
                    """, (paper_id, primary_id))
                    
                    if cur.fetchone():
                        # 主作者已关联，删除重复关联
                        cur.execute("""
                            DELETE FROM paper_authors 
                            WHERE paper_id = ? AND author_id = ?
                        """, (paper_id, dup_id))
                    else:
                        # 主作者未关联，更新关联
                        cur.execute("""
                            UPDATE paper_authors 
                            SET author_id = ? 
                            WHERE paper_id = ? AND author_id = ?
                        """, (primary_id, paper_id, dup_id))
                        merged_papers += 1
            
            # 删除重复作者记录
            cur.execute(f"DELETE FROM authors WHERE id IN ({placeholders})", duplicate_ids)
            
            self.engine.conn.commit()
            
            return {
                "status": "success",
                "primary_id": primary_id,
                "primary_name": primary["full_name"],
                "merged_count": len(duplicate_ids),
                "merged_papers": merged_papers,
                "message": f"成功合并 {len(duplicate_ids)} 条重复记录"
            }
            
        except Exception as e:
            self.engine.conn.rollback()
            raise e
    
    def _test_connection(self, service: str, data: Dict) -> Dict:
        """测试 API 连接。
        
        Args:
            service: 服务类型 (llm/embedding/mineru/wos/scopus)
            data: 包含 api_key, base_url 等参数
        
        Returns:
            测试结果
        """
        try:
            if service == "llm":
                api_key = data.get("api_key", "").strip()
                base_url = data.get("base_url", "").strip()
                model = data.get("model", "").strip()
                
                if not api_key or not base_url:
                    return {"success": False, "message": "缺少 API Key 或 Base URL"}
                
                # 测试 LLM 连接
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model or "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5
                }
                
                response = requests.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "LLM 连接成功"}
                else:
                    return {"success": False, "message": f"连接失败: {response.status_code} - {response.text[:100]}"}
            
            elif service == "embedding":
                api_key = data.get("api_key", "").strip()
                base_url = data.get("base_url", "").strip()
                model = data.get("model", "").strip()
                
                if not api_key or not base_url:
                    return {"success": False, "message": "缺少 API Key 或 Base URL"}
                
                # 测试 Embedding 连接
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model or "text-embedding-ada-002",
                    "input": "test"
                }
                
                response = requests.post(
                    f"{base_url.rstrip('/')}/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "Embedding 连接成功"}
                else:
                    return {"success": False, "message": f"连接失败: {response.status_code} - {response.text[:100]}"}
            
            elif service == "mineru":
                api_key = data.get("api_key", "").strip()
                if not api_key:
                    return {"success": False, "message": "缺少 API Key"}
                
                # MinerU 测试连接
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get(
                    "https://mineru.net/api/v4/status",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "MinerU 连接成功"}
                else:
                    return {"success": False, "message": f"连接失败: {response.status_code}"}
            
            elif service == "wos":
                api_key = data.get("api_key", "").strip()
                if not api_key:
                    return {"success": False, "message": "缺少 API Key"}
                
                # WoS 测试连接
                headers = {"X-ApiKey": api_key}
                response = requests.get(
                    "https://api.clarivate.com/apis/wos-starter/v1/documents",
                    headers=headers,
                    params={"limit": 1},
                    timeout=10
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "Web of Science 连接成功"}
                else:
                    return {"success": False, "message": f"连接失败: {response.status_code}"}
            
            elif service == "scopus":
                api_key = data.get("api_key", "").strip()
                if not api_key:
                    return {"success": False, "message": "缺少 API Key"}
                
                # Scopus 测试连接
                headers = {"X-ELS-APIKey": api_key}
                response = requests.get(
                    "https://api.elsevier.com/content/search/scopus",
                    headers=headers,
                    params={"query": "test", "count": 1},
                    timeout=10
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "Scopus 连接成功"}
                else:
                    return {"success": False, "message": f"连接失败: {response.status_code}"}
            
            else:
                return {"success": False, "message": f"不支持的服务类型: {service}"}
        
        except requests.exceptions.Timeout:
            return {"success": False, "message": "连接超时"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "无法连接到服务"}
        except Exception as e:
            return {"success": False, "message": f"测试失败: {str(e)}"}
    
    def _handle_stats(self) -> Dict:
        cur = self.engine.conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM papers_fts")
        n = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM papers")
        p = cur.fetchone()["c"]
        # 2026-08-01：过滤 is_placeholder=1 的噪声
        cur.execute("SELECT COUNT(*) AS c FROM papers WHERE COALESCE(is_placeholder, 0) = 0")
        p_valid = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM paper_sections")
        sections = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM paper_figures")
        figures = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM paper_data_points")
        data_points = cur.fetchone()["c"]
        cur.execute("""
            SELECT COUNT(*) AS c
            FROM paper_data_points dp
            JOIN papers p ON p.id = dp.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
        """)
        data_points_valid = cur.fetchone()["c"]
        cur.execute("""
            SELECT stage, status, COUNT(*) AS c
            FROM parse_jobs
            GROUP BY stage, status
        """)
        job_summary = [dict(r) for r in cur.fetchall()]

        # 年份分布
        cur.execute("""
            SELECT substr(published_date, 1, 4) AS year, COUNT(*) AS c
            FROM papers
            WHERE published_date IS NOT NULL AND substr(published_date, 1, 4) != ''
            GROUP BY year
            ORDER BY year
        """)
        year_distribution = [dict(r) for r in cur.fetchall()]

        # 期刊分布
        cur.execute("""
            SELECT journal, COUNT(*) AS c
            FROM papers
            WHERE journal IS NOT NULL AND journal != ''
            GROUP BY journal
            ORDER BY c DESC
            LIMIT 10
        """)
        top_journals = [dict(r) for r in cur.fetchall()]

        # 关键词分布（从 papers.keywords 解析）
        cur.execute("SELECT keywords FROM papers WHERE keywords IS NOT NULL AND keywords != ''")
        keyword_counts: Dict[str, int] = {}
        for row in cur.fetchall():
            for kw in _parse_keyword_row(row["keywords"]):
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        top_keywords = sorted(
            [{"keyword": k, "count": v} for k, v in keyword_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:20]

        return {
            "indexed_papers": n,
            "total_papers": p,
            "valid_papers": p_valid,
            "coverage": round(n / p * 100, 2) if p else 0,
            "sections": sections,
            "figures": figures,
            "data_points": data_points,
            "data_points_valid": data_points_valid,
            "parse_jobs": job_summary,
            "year_distribution": year_distribution,
            "top_journals": top_journals,
            "top_keywords": top_keywords,
        }

    def _handle_search(self, qs: Dict) -> Dict:
        q = (qs.get("q", [""])[0] or "").strip()
        mode = (qs.get("mode", ["keyword"])[0] or "keyword").lower()
        if mode not in ("keyword", "phrase", "fuzzy"):
            mode = "keyword"

        fields_str = qs.get("fields", [""])[0] or ""
        fields = [f.strip() for f in fields_str.split(",") if f.strip()] or None

        sort_by = (qs.get("sort", ["relevance"])[0] or "relevance").lower()
        if sort_by not in ("relevance", "date_desc", "date_asc"):
            sort_by = "relevance"

        filters = {}
        for k in ("year_from", "year_to"):
            if qs.get(k):
                try:
                    filters[k] = int(qs[k][0])
                except ValueError:
                    pass
        for k in ("year", "journal", "author", "language", "source", "doi"):
            if qs.get(k):
                filters[k] = qs[k][0]
        # 期刊分级：journal_tiers（多值，逗号分隔） / journal_tier（单值，向后兼容）
        if qs.get("journal_tiers"):
            tiers_raw = qs["journal_tiers"][0] or ""
            tiers_list = [t.strip() for t in tiers_raw.split(",") if t.strip()]
            if tiers_list:
                filters["journal_tiers"] = tiers_list
        elif qs.get("journal_tier"):
            tier_val = (qs["journal_tier"][0] or "").strip()
            if tier_val:
                filters["journal_tier"] = tier_val

        try:
            limit = int(qs.get("limit", ["20"])[0])
            offset = int(qs.get("offset", ["0"])[0])
        except ValueError:
            limit, offset = 20, 0

        highlight = qs.get("highlight", ["1"])[0] not in ("0", "false", "no")

        return self.engine.search(
            q, fields=fields, filters=filters, mode=mode,
            limit=limit, offset=offset, sort_by=sort_by, highlight=highlight,
        )

    def _handle_aggregate(self, qs: Dict) -> Dict:
        q = (qs.get("q", ["*"])[0] or "*").strip()
        mode = (qs.get("mode", ["keyword"])[0] or "keyword").lower()
        return self.engine.aggregate(q, mode=mode)

    def _handle_vector_search(self, qs: Dict) -> Dict:
        q = (qs.get("q", [""])[0] or "").strip()
        if not q:
            return {"error": "缺少 q 参数"}
        try:
            top_k = int(qs.get("top_k", ["10"])[0])
        except ValueError:
            top_k = 10
        chunk_type = qs.get("chunk_type", [""])[0] or None
        paper_id = None
        if qs.get("paper_id"):
            try:
                paper_id = int(qs["paper_id"][0])
            except ValueError:
                pass

        from phase3 import vector_search as vs
        results = vs.vector_search(q, top_k=top_k, chunk_type=chunk_type, paper_id=paper_id)
        return {"query": q, "top_k": top_k, "results": results}

    def _handle_vector_stats(self, qs: Dict) -> Dict:
        """向量库统计与抽样读取。"""
        try:
            top_k = int(qs.get("top_k", ["10"])[0])
        except ValueError:
            top_k = 10
        chunk_type = qs.get("chunk_type", [""])[0] or None

        cur = self.engine.conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM paper_embeddings")
        total = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(DISTINCT paper_id) AS c FROM paper_embeddings")
        papers = cur.fetchone()["c"]
        cur.execute("SELECT chunk_type, COUNT(*) AS c FROM paper_embeddings GROUP BY chunk_type ORDER BY c DESC")
        by_type = [dict(r) for r in cur.fetchall()]

        # 读取维度：取第一条 embedding 的 BLOB 长度 / 4
        dim = 0
        cur.execute("SELECT embedding FROM paper_embeddings LIMIT 1")
        row = cur.fetchone()
        if row and row["embedding"]:
            dim = len(row["embedding"]) // 4

        # 抽样读取最近插入的 chunk
        where = "WHERE chunk_type=?" if chunk_type else ""
        params = [chunk_type] if chunk_type else []
        cur.execute(
            f"SELECT paper_id, chunk_type, chunk_id FROM paper_embeddings {where} ORDER BY rowid DESC LIMIT ?",
            params + [top_k],
        )
        samples = [dict(r) for r in cur.fetchall()]
        from phase3 import vector_search as vs
        for s in samples:
            text, metadata = vs._get_chunk_text(s["paper_id"], s["chunk_type"], s["chunk_id"])
            s["text"] = text[:500] if text else ""
            s["metadata"] = metadata

        # 检测 sqlite-vec 是否可用
        vec_available = False
        try:
            import sqlite_vec
            vec_available = True
        except Exception:
            pass

        return {
            "total_embeddings": total,
            "papers_with_embeddings": papers,
            "dimension": dim,
            "by_chunk_type": by_type,
            "sqlite_vec_available": vec_available,
            "samples": samples,
        }

    def _handle_hybrid_search(self, qs: Dict) -> Dict:
        q = (qs.get("q", [""])[0] or "").strip()
        if not q:
            return {"error": "缺少 q 参数"}
        try:
            top_k = int(qs.get("top_k", ["10"])[0])
        except ValueError:
            top_k = 10
        try:
            fts_weight = float(qs.get("fts_weight", ["0.4"])[0])
            vector_weight = float(qs.get("vector_weight", ["0.6"])[0])
        except ValueError:
            fts_weight, vector_weight = 0.4, 0.6
        chunk_type = qs.get("chunk_type", [""])[0] or None
        paper_id = None
        if qs.get("paper_id"):
            try:
                paper_id = int(qs["paper_id"][0])
            except ValueError:
                pass

        from phase3 import vector_search as vs
        results = vs.hybrid_search(
            q, top_k=top_k, chunk_type=chunk_type, paper_id=paper_id,
            fts_weight=fts_weight, vector_weight=vector_weight
        )
        return {"query": q, "top_k": top_k, "chunk_type": chunk_type,
                "fts_weight": fts_weight, "vector_weight": vector_weight,
                "results": results}

    def _handle_paper_path(self, path: str, qs: Dict) -> Optional[Dict]:
        """处理 /paper/<id> 及其子路径。"""
        parts = path.split("/")
        if len(parts) < 3:
            return {"status": 400, "data": {"error": "缺少 paper_id"}}
        try:
            pid = int(parts[2])
        except ValueError:
            return {"status": 400, "data": {"error": "无效的 paper_id"}}

        sub_path = "/".join(parts[3:]) if len(parts) > 3 else ""

        if sub_path == "" or sub_path == "detail":
            paper = self.engine.get_paper_detail(pid)
            if paper:
                return {"status": 200, "data": paper}
            return {"status": 404, "data": {"error": f"论文 {pid} 不存在"}}

        if sub_path == "similar":
            try:
                top_k = int(qs.get("top_k", ["5"])[0])
            except ValueError:
                top_k = 5
            from phase3 import vector_search as vs
            results = vs.find_similar_papers(pid, top_k=top_k)
            return {"status": 200, "data": {"paper_id": pid, "top_k": top_k, "results": results}}

        if sub_path == "knowledge":
            return {"status": 200, "data": self._get_paper_knowledge(pid)}

        if sub_path == "methods":
            return {"status": 200, "data": self._get_paper_methods(pid)}

        if sub_path == "data_points":
            return {"status": 200, "data": self._get_paper_data_points(pid)}

        if sub_path == "citations":
            return {"status": 200, "data": self._get_paper_citations(pid)}

        if sub_path == "authors":
            return {"status": 200, "data": authors_api.get_paper_authors(self.engine.conn, pid)}

        return {"status": 404, "data": {"error": f"未知子路径: {sub_path}"}}

    def _get_paper_knowledge(self, paper_id: int) -> Dict:
        cur = self.engine.conn.cursor()
        cur.execute("""
            SELECT research_question, core_answer, key_claims, evidence_generation,
                   boundaries, reusable_inspiration, source_section_ids,
                   extraction_method, extracted_at, quality_score, audit_report
            FROM paper_knowledge_cards WHERE paper_id = ?
        """, (paper_id,))
        row = cur.fetchone()
        if not row:
            return {"paper_id": paper_id, "knowledge": None}
        knowledge = dict(row)
        for k in ("key_claims", "boundaries", "reusable_inspiration",
                  "source_section_ids", "audit_report"):
            if knowledge.get(k) and isinstance(knowledge[k], str):
                try:
                    knowledge[k] = json.loads(knowledge[k])
                except json.JSONDecodeError:
                    pass
        return {"paper_id": paper_id, "knowledge": knowledge}

    def _get_paper_methods(self, paper_id: int) -> Dict:
        cur = self.engine.conn.cursor()
        cur.execute("""
            SELECT methodology, workflow, data_sources, models_algorithms,
                   evaluation_metrics, methods_section_id, extraction_method, extracted_at
            FROM paper_methods WHERE paper_id = ?
        """, (paper_id,))
        row = cur.fetchone()
        if not row:
            return {"paper_id": paper_id, "methods": None}
        methods = dict(row)
        for k in ("workflow", "data_sources", "models_algorithms", "evaluation_metrics"):
            if methods.get(k) and isinstance(methods[k], str):
                try:
                    methods[k] = json.loads(methods[k])
                except json.JSONDecodeError:
                    pass
        return {"paper_id": paper_id, "methods": methods}

    def _get_paper_data_points(self, paper_id: int) -> Dict:
        cur = self.engine.conn.cursor()
        cur.execute("""
            SELECT id, metric_name, metric_value, unit, context, section_id,
                   figure_id, page, significance, confidence, is_review_record,
                   extraction_method, extracted_at
            FROM paper_data_points WHERE paper_id = ?
            ORDER BY id
        """, (paper_id,))
        rows = [dict(r) for r in cur.fetchall()]
        return {"paper_id": paper_id, "count": len(rows), "data_points": rows}

    def _get_paper_citations(self, paper_id: int) -> Dict:
        cur = self.engine.conn.cursor()
        cur.execute("""
            SELECT id, cited_doi, cited_title, cited_authors, cited_year,
                   cited_journal, raw_reference, match_method, match_confidence
            FROM citations_v2 WHERE citing_paper_id = ?
            ORDER BY id
        """, (paper_id,))
        rows = [dict(r) for r in cur.fetchall()]
        return {"paper_id": paper_id, "count": len(rows), "citations": rows}

    def _handle_compare_metric(self, qs: Dict) -> Dict:
        metric_name = (qs.get("metric_name", [""])[0] or "").strip()
        if not metric_name:
            return {"error": "缺少 metric_name 参数"}
        try:
            top_k = int(qs.get("top_k", ["20"])[0])
        except ValueError:
            top_k = 20
        from phase3 import vector_search as vs
        results = vs.compare_metric_across_papers(metric_name, top_k=top_k)
        return {"metric_name": metric_name, "top_k": top_k, "count": len(results), "results": results}

    # ------------------ 学者画像与机构合作网络接口 ------------------
    def _handle_authors_list(self, qs: Dict) -> Dict:
        """学者列表与检索。"""
        return authors_api.list_authors(self.engine.conn, qs)

    def _handle_author_path(self, path: str, qs: Dict) -> Optional[Dict]:
        """处理 /author/<id> 及其子路径。"""
        parts = path.split("/")
        if len(parts) < 3:
            return {"status": 400, "data": {"error": "缺少 author_id"}}
        try:
            author_id = int(parts[2])
        except ValueError:
            return {"status": 400, "data": {"error": "无效的 author_id"}}

        sub_path = "/".join(parts[3:]) if len(parts) > 3 else ""

        if sub_path == "" or sub_path == "profile":
            profile = authors_api.get_author_profile(self.engine.conn, author_id)
            if profile:
                return {"status": 200, "data": profile}
            return {"status": 404, "data": {"error": f"学者 {author_id} 不存在"}}

        if sub_path == "papers":
            try:
                limit = int(qs.get("limit", ["50"])[0])
                offset = int(qs.get("offset", ["0"])[0])
            except ValueError:
                limit, offset = 50, 0
            return {"status": 200, "data": authors_api.get_author_papers(self.engine.conn, author_id, limit, offset)}

        if sub_path == "network":
            try:
                max_nodes = int(qs.get("max_nodes", ["50"])[0])
            except ValueError:
                max_nodes = 50
            return {"status": 200, "data": authors_api.get_author_network(self.engine.conn, author_id, max_nodes)}

        return {"status": 404, "data": {"error": f"未知子路径: {sub_path}"}}

    def _handle_institution_network(self, qs: Dict) -> Dict:
        """机构合作网络。"""
        affiliation = (qs.get("affiliation", [""])[0] or "").strip()
        try:
            max_nodes = int(qs.get("max_nodes", ["60"])[0])
        except ValueError:
            max_nodes = 60
        try:
            min_papers = int(qs.get("min_papers", ["1"])[0])
        except ValueError:
            min_papers = 1
        return authors_api.get_institution_network(
            self.engine.conn, affiliation=affiliation or None, max_nodes=max_nodes, min_papers=min_papers
        )

    # ------------------ 质量监控相关接口 ------------------
    def _handle_quality_stats(self) -> Dict:
        """质量监控统计：覆盖率、字段完整率、quality_score 分布。"""
        cur = self.engine.conn.cursor()

        # 总论文数（排除占位论文）
        cur.execute("SELECT COUNT(*) AS c FROM papers WHERE COALESCE(is_placeholder, 0) = 0")
        total_papers = cur.fetchone()["c"]

        # 知识卡片覆盖率
        cur.execute("""
            SELECT COUNT(*) AS c FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
        """)
        kc_count = cur.fetchone()["c"]
        kc_coverage = round(kc_count / total_papers * 100, 2) if total_papers else 0

        # 方法流程覆盖率
        cur.execute("""
            SELECT COUNT(*) AS c FROM paper_methods m
            JOIN papers p ON p.id = m.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
        """)
        methods_count = cur.fetchone()["c"]
        methods_coverage = round(methods_count / total_papers * 100, 2) if total_papers else 0

        # 数据点覆盖率
        cur.execute("""
            SELECT COUNT(DISTINCT dp.paper_id) AS c FROM paper_data_points dp
            JOIN papers p ON p.id = dp.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
        """)
        dp_papers_count = cur.fetchone()["c"]
        dp_coverage = round(dp_papers_count / total_papers * 100, 2) if total_papers else 0

        # 数据点总数
        cur.execute("""
            SELECT COUNT(*) AS c FROM paper_data_points dp
            JOIN papers p ON p.id = dp.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
        """)
        dp_total = cur.fetchone()["c"]

        # 字段完整率：key_claims 非空且有内容
        cur.execute("""
            SELECT COUNT(*) AS c FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
              AND k.key_claims IS NOT NULL AND k.key_claims != '[]' AND k.key_claims != ''
        """)
        kc_with_claims = cur.fetchone()["c"]
        claims_completeness = round(kc_with_claims / kc_count * 100, 2) if kc_count else 0

        # 字段完整率：core_answer 非空
        cur.execute("""
            SELECT COUNT(*) AS c FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
              AND k.core_answer IS NOT NULL AND k.core_answer != ''
        """)
        kc_with_answer = cur.fetchone()["c"]
        answer_completeness = round(kc_with_answer / kc_count * 100, 2) if kc_count else 0

        # quality_score 分布
        cur.execute("""
            SELECT
                CASE
                    WHEN k.quality_score IS NULL THEN 'null'
                    WHEN k.quality_score < 0.4 THEN 'low'
                    WHEN k.quality_score < 0.6 THEN 'medium'
                    WHEN k.quality_score < 0.8 THEN 'good'
                    ELSE 'excellent'
                END AS tier,
                COUNT(*) AS c
            FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
            GROUP BY tier
        """)
        score_distribution = {r["tier"]: r["c"] for r in cur.fetchall()}

        # 平均 quality_score
        cur.execute("""
            SELECT AVG(k.quality_score) AS avg_score
            FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0 AND k.quality_score IS NOT NULL
        """)
        avg_score = cur.fetchone()["avg_score"]

        # 提取失败任务统计
        cur.execute("""
            SELECT stage, error_class, COUNT(*) AS c
            FROM parse_jobs
            WHERE status IN ('failed', 'permanent_failed')
            GROUP BY stage, error_class
        """)
        failure_stats = [dict(r) for r in cur.fetchall()]

        return {
            "total_papers": total_papers,
            "coverage": {
                "knowledge_cards": {"count": kc_count, "coverage": kc_coverage},
                "methods": {"count": methods_count, "coverage": methods_coverage},
                "data_points": {"papers_count": dp_papers_count, "total_points": dp_total, "coverage": dp_coverage},
            },
            "completeness": {
                "has_key_claims": {"count": kc_with_claims, "rate": claims_completeness},
                "has_core_answer": {"count": kc_with_answer, "rate": answer_completeness},
            },
            "quality_score": {
                "distribution": score_distribution,
                "average": round(avg_score, 3) if avg_score else None,
            },
            "failures": failure_stats,
        }

    def _handle_quality_low_quality(self, qs: Dict) -> Dict:
        """低质量论文列表（quality_score < 0.6 或未评分）。"""
        try:
            limit = int(qs.get("limit", ["50"])[0])
        except ValueError:
            limit = 50
        try:
            offset = int(qs.get("offset", ["0"])[0])
        except ValueError:
            offset = 0
        threshold = float(qs.get("threshold", ["0.6"])[0] or "0.6")
        include_unscored = qs.get("include_unscored", ["1"])[0] not in ("0", "false", "no")

        cur = self.engine.conn.cursor()

        # 构建 WHERE 条件
        where_clauses = ["COALESCE(p.is_placeholder, 0) = 0"]
        params = []

        if include_unscored:
            # 低质量或未评分
            where_clauses.append("(k.quality_score IS NULL OR k.quality_score < ?)")
            params.append(threshold)
        else:
            # 仅低质量
            where_clauses.append("k.quality_score IS NOT NULL AND k.quality_score < ?")
            params.append(threshold)

        where_sql = " AND ".join(where_clauses)

        # 总数
        cur.execute(f"""
            SELECT COUNT(*) AS c
            FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE {where_sql}
        """, params)
        total = cur.fetchone()["c"]

        # 列表
        cur.execute(f"""
            SELECT k.paper_id, p.title, p.published_date, p.journal,
                   k.quality_score, k.research_question, k.core_answer,
                   k.prompt_version, k.extraction_method
            FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE {where_sql}
            ORDER BY CASE WHEN k.quality_score IS NULL THEN 1 ELSE 0 END, k.quality_score ASC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        papers = [dict(r) for r in cur.fetchall()]

        return {
            "total": total,
            "threshold": threshold,
            "include_unscored": include_unscored,
            "limit": limit,
            "offset": offset,
            "papers": papers,
        }

    def _handle_quality_prompt_compare(self, qs: Dict) -> Dict:
        """Prompt A/B 测试对比：按 prompt_version 分组统计 quality_score。"""
        cur = self.engine.conn.cursor()

        # 按 prompt_version 分组统计
        cur.execute("""
            SELECT
                COALESCE(k.prompt_version, 'unknown') AS version,
                COUNT(*) AS count,
                SUM(CASE WHEN k.quality_score IS NOT NULL THEN 1 ELSE 0 END) AS scored_count,
                SUM(CASE WHEN k.quality_score IS NULL THEN 1 ELSE 0 END) AS unscored_count,
                AVG(k.quality_score) AS avg_score,
                MIN(k.quality_score) AS min_score,
                MAX(k.quality_score) AS max_score,
                SUM(CASE WHEN k.quality_score >= 0.6 THEN 1 ELSE 0 END) AS pass_count
            FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE COALESCE(p.is_placeholder, 0) = 0
              AND k.prompt_version IS NOT NULL
            GROUP BY k.prompt_version
            ORDER BY count DESC
        """)
        versions = [dict(r) for r in cur.fetchall()]

        # 计算通过率（基于已评分数）
        for v in versions:
            v["pass_rate"] = round(v["pass_count"] / v["scored_count"] * 100, 2) if v["scored_count"] else 0
            v["avg_score"] = round(v["avg_score"], 3) if v["avg_score"] else None

        return {"versions": versions}

    # ------------------ 可视化相关接口 ------------------
    def _handle_graph(self, qs: Dict) -> Dict:
        """构建论文 / 作者 / 关键词 / 数据点的关系图谱。"""
        max_nodes = int(qs.get("max_nodes", [os.getenv("GRAPH_MAX_NODES", "500")])[0])
        year_from = _int_or_none(qs, "year_from")
        year_to = _int_or_none(qs, "year_to")
        min_citations = _int_or_none(qs, "min_citations") or 0
        entity_types = {t.strip() for t in (qs.get("entity_types", [""])[0] or "").split(",") if t.strip()}
        if not entity_types:
            entity_types = {"paper", "author", "keyword", "data_point"}

        cur = self.engine.conn.cursor()

        # 1. 获取论文节点
        where_clauses = [
            "(p.title IS NOT NULL OR p.abstract IS NOT NULL)",
            # 过滤完全无数据的论文：没有作者也没有关键词，无法与图谱其他部分关联
            # 注意：字段可能是空字符串 "" 而非 NULL，需 trim 后判断
            "(TRIM(COALESCE(p.author, '')) <> '' OR TRIM(COALESCE(p.keywords, '')) <> '')",
            # 2026-08-01：过滤占位论文（is_placeholder=1）以避免主题漂移噪声
            "COALESCE(p.is_placeholder, 0) = 0",
        ]
        params: List[Any] = []
        if year_from is not None:
            where_clauses.append("substr(p.published_date, 1, 4) >= ?")
            params.append(str(year_from))
        if year_to is not None:
            where_clauses.append("substr(p.published_date, 1, 4) <= ?")
            params.append(str(year_to))
        if min_citations:
            where_clauses.append("COALESCE(p.citation_count, 0) >= ?")
            params.append(min_citations)

        cur.execute(
            f"""
            SELECT p.id, p.title, p.published_date, p.citation_count, p.keywords, p.doi, p.author
            FROM papers p
            WHERE {' AND '.join(where_clauses)}
            ORDER BY COALESCE(p.citation_count, 0) DESC
            LIMIT ?
            """,
            params + [max_nodes],
        )
        paper_rows = [dict(r) for r in cur.fetchall()]
        paper_ids = [r["id"] for r in paper_rows]
        paper_id_set = set(paper_ids)

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_ids: Set[str] = set()

        for r in paper_rows:
            pid = f"p{r['id']}"
            node_ids.add(pid)
            nodes.append({
                "id": pid,
                "label": r["title"] or f"论文 {r['id']}",
                "type": "paper",
                "paper_id": r["id"],
                "year": _extract_year(r["published_date"]),
                "citation_count": r["citation_count"] or 0,
                "doi": r["doi"],
            })

        if not paper_ids:
            return {"nodes": nodes, "edges": edges, "total_nodes": 0, "total_edges": 0}

        # 2. 论文 -> 作者
        if "author" in entity_types:
            author_rows = []
            if paper_ids:
                cur.execute(
                    """
                    SELECT pa.paper_id, a.id AS author_id, a.full_name
                    FROM paper_authors pa
                    JOIN authors a ON a.id = pa.author_id
                    WHERE pa.paper_id IN ({})
                    """.format(",".join("?" * len(paper_ids))),
                    paper_ids,
                )
                author_rows = [dict(r) for r in cur.fetchall()]

            # 若 paper_authors / authors 表为空，降级为从 papers.author JSON 解析
            if not author_rows:
                seen_authors: Dict[str, int] = {}
                next_author_id = 1
                for r in paper_rows:
                    parsed = _safe_json_loads(r.get("author"))
                    if not isinstance(parsed, list):
                        continue
                    for a in parsed:
                        if not isinstance(a, dict):
                            continue
                        name = " ".join([a.get("given", ""), a.get("family", "")]).strip()
                        if not name:
                            name = a.get("name", "")
                        if not name:
                            continue
                        if name not in seen_authors:
                            seen_authors[name] = next_author_id
                            next_author_id += 1
                        author_rows.append({
                            "paper_id": r["id"],
                            "author_id": seen_authors[name],
                            "full_name": name,
                        })

            for r in author_rows:
                if r["paper_id"] not in paper_id_set:
                    continue
                aid = f"a{r['author_id']}"
                if aid not in node_ids:
                    # 仅在「新增节点」时检查 max_nodes；已有作者仍然允许继续添加边
                    if len(nodes) >= max_nodes:
                        continue
                    node_ids.add(aid)
                    nodes.append({
                        "id": aid,
                        "label": r["full_name"] or f"作者 {r['author_id']}",
                        "type": "author",
                        "author_id": r["author_id"],
                    })
                edges.append({
                    "source": f"p{r['paper_id']}",
                    "target": aid,
                    "type": "authored",
                })
            # 收尾：每篇论文保证至少 1 条 authored 边，避免被孤立。
            # 若首选作者已被收下则直接补边；否则为该论文新增一个作者节点，
            # 突破 max_nodes 限制以保证图谱连通性（边密度优先于节点数硬限）。
            # 注意：paper_id_set 是整数集合 {82, 66, 53...}，
            # 必须用原始整数 paper_id 比较，不能用格式化后的字符串 pid
            if "paper" in entity_types:
                papers_with_edge = {e["source"] for e in edges if e["type"] == "authored"}
                for r in author_rows:
                    raw_pid = r["paper_id"]
                    if raw_pid not in paper_id_set:
                        continue
                    pid = f"p{raw_pid}"
                    if pid in papers_with_edge:
                        continue
                    aid = f"a{r['author_id']}"
                    if aid not in node_ids:
                        # 突破 max_nodes：每篇孤立论文分配一个新作者节点，确保连通
                        node_ids.add(aid)
                        nodes.append({
                            "id": aid,
                            "label": r["full_name"] or f"作者 {r['author_id']}",
                            "type": "author",
                            "author_id": r["author_id"],
                        })
                    edges.append({"source": pid, "target": aid, "type": "authored"})
                    papers_with_edge.add(pid)

        # 3. 论文 -> 关键词
        if "keyword" in entity_types:
            keyword_counter: Dict[str, int] = {}
            keyword_context: Dict[str, List[int]] = {}
            for r in paper_rows:
                for kw in _parse_keyword_row(r.get("keywords")):
                    keyword_counter[kw] = keyword_counter.get(kw, 0) + 1
                    keyword_context.setdefault(kw, []).append(r["id"])
            top_keywords = sorted(
                keyword_counter.items(), key=lambda x: x[1], reverse=True
            )[:max(0, max_nodes - len(nodes))]
            used_keyword_ids: Set[str] = set()
            for kw, count in top_keywords:
                if len(nodes) >= max_nodes:
                    break
                base = _slug(kw)
                kid = f"kw_{base}"
                suffix = 2
                while kid in used_keyword_ids:
                    kid = f"kw_{base}_{suffix}"
                    suffix += 1
                used_keyword_ids.add(kid)
                node_ids.add(kid)
                nodes.append({"id": kid, "label": kw, "type": "keyword", "count": count})
                for pid in keyword_context.get(kw, []):
                    if pid in paper_id_set:
                        edges.append({"source": f"p{pid}", "target": kid, "type": "has_keyword"})

        # 4. 论文 -> 数据点
        if "data_point" in entity_types:
            cur.execute(
                """
                SELECT id, paper_id, metric_name
                FROM paper_data_points
                WHERE paper_id IN ({})
                """.format(",".join("?" * len(paper_ids))),
                paper_ids,
            )
            for r in cur.fetchall():
                r = dict(r)
                if r["paper_id"] not in paper_id_set:
                    continue
                if len(nodes) >= max_nodes:
                    break
                dpid = f"dp{r['id']}"
                if dpid not in node_ids:
                    node_ids.add(dpid)
                    nodes.append({
                        "id": dpid,
                        "label": r["metric_name"] or f"数据 {r['id']}",
                        "type": "data_point",
                        "data_point_id": r["id"],
                    })
                if dpid in node_ids:
                    edges.append({
                        "source": f"p{r['paper_id']}",
                        "target": dpid,
                        "type": "has_data",
                    })

        # 5. 论文 -> 论文引用边
        if "paper" in entity_types:
            cur.execute("SELECT id, doi FROM papers WHERE doi IS NOT NULL AND doi != ''")
            doi_to_id = {r["doi"]: r["id"] for r in cur.fetchall()}
            cur.execute(
                """
                SELECT citing_paper_id, cited_doi
                FROM citations_v2
                WHERE citing_paper_id IN ({})
                """.format(",".join("?" * len(paper_ids))),
                paper_ids,
            )
            for r in cur.fetchall():
                r = dict(r)
                cited_id = doi_to_id.get(r["cited_doi"])
                if cited_id in paper_id_set and r["citing_paper_id"] in paper_id_set:
                    edges.append({
                        "source": f"p{r['citing_paper_id']}",
                        "target": f"p{cited_id}",
                        "type": "cites",
                    })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": sorted(entity_types),
        }

    def _handle_graph_diagnostics(self, qs: Dict) -> Dict:
        """对当前图谱数据做健康检查，返回问题节点与统计。"""
        graph = self._handle_graph(qs)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_id_set = {n["id"] for n in nodes}
        node_map = {n["id"]: n for n in nodes}
        current_year = datetime.datetime.now().year

        issues: List[Dict[str, Any]] = []

        # 1. 孤立节点：无任何边连接
        connected = set()
        for e in edges:
            connected.add(e["source"])
            connected.add(e["target"])
        for n in nodes:
            if n["id"] not in connected:
                issues.append({
                    "type": "isolated_node",
                    "node_id": n["id"],
                    "label": n.get("label", n["id"]),
                    "node_type": n.get("type"),
                    "message": "孤立节点：无连接",
                })

        # 2. 悬挂边：边指向不存在的节点
        for e in edges:
            if e["source"] not in node_id_set or e["target"] not in node_id_set:
                issues.append({
                    "type": "dangling_edge",
                    "source": e.get("source"),
                    "target": e.get("target"),
                    "edge_type": e.get("type"),
                    "message": "悬挂边：源或目标节点缺失",
                })

        # 3. 时间异常：年份早于 1900 或晚于当前年份 + 1
        for n in nodes:
            year = n.get("year")
            if year is None:
                continue
            try:
                y = int(year)
            except (ValueError, TypeError):
                continue
            if y < 1900 or y > current_year + 1:
                issues.append({
                    "type": "time_anomaly",
                    "node_id": n["id"],
                    "label": n.get("label", n["id"]),
                    "year": y,
                    "message": f"时间异常：年份 {y} 超出合理范围",
                })

        # 4. 重复机构名（仅 institution 类型）：按标签统计
        if any(n.get("type") == "institution" for n in nodes):
            from collections import Counter
            labels = [n.get("label", "").strip().lower() for n in nodes if n.get("type") == "institution"]
            dupes = {label: c for label, c in Counter(labels).items() if c > 1 and label}
            for label, count in dupes.items():
                ids = [n["id"] for n in nodes if n.get("type") == "institution" and n.get("label", "").strip().lower() == label]
                issues.append({
                    "type": "duplicate_institution",
                    "label": label,
                    "count": count,
                    "node_ids": ids,
                    "message": f"重复机构：{label} 出现 {count} 次",
                })

        # 按问题类型聚合统计
        stats: Dict[str, int] = {}
        for issue in issues:
            stats[issue["type"]] = stats.get(issue["type"], 0) + 1

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "issue_count": len(issues),
            "issue_stats": stats,
            "issues": issues[:100],  # 最多返回 100 条，避免过大响应
        }

    def _handle_papers_list(self, qs: Dict) -> Dict:
        """知识库论文表格接口。"""
        q = (qs.get("q", [""])[0] or "").strip()
        year_from = _int_or_none(qs, "year_from")
        year_to = _int_or_none(qs, "year_to")
        journal = (qs.get("journal", [""])[0] or "").strip()
        source = (qs.get("source", [""])[0] or "").strip()
        language = (qs.get("language", [""])[0] or "").strip()
        author = (qs.get("author", [""])[0] or "").strip()
        journal_tier = (qs.get("journal_tier", [""])[0] or "").strip()
        sort = (qs.get("sort", ["year_desc"])[0] or "year_desc").lower()
        try:
            limit = int(qs.get("limit", ["50"])[0])
            offset = int(qs.get("offset", ["0"])[0])
        except ValueError:
            limit, offset = 50, 0

        where_clauses = ["1=1", "COALESCE(p.is_placeholder, 0) = 0"]
        params: List[Any] = []
        if q:
            where_clauses.append("(p.title LIKE ? OR p.abstract LIKE ? OR p.journal LIKE ?)")
            like_q = f"%{q}%"
            params.extend([like_q, like_q, like_q])
        if year_from is not None:
            where_clauses.append("substr(p.published_date, 1, 4) >= ?")
            params.append(str(year_from))
        if year_to is not None:
            where_clauses.append("substr(p.published_date, 1, 4) <= ?")
            params.append(str(year_to))
        if journal:
            where_clauses.append("p.journal = ?")
            params.append(journal)
        if source:
            where_clauses.append("p.source = ?")
            params.append(source)
        if language:
            where_clauses.append("p.language = ?")
            params.append(language)
        if author:
            where_clauses.append("p.author LIKE ?")
            params.append(f"%{author}%")
        if journal_tier:
            where_clauses.append("p.journal_tier = ?")
            params.append(journal_tier)

        order_by = {
            "year_desc": "substr(p.published_date, 1, 4) DESC",
            "year_asc": "substr(p.published_date, 1, 4) ASC",
            "citations_desc": "COALESCE(p.citation_count, 0) DESC",
            "title_asc": "p.title ASC",
        }.get(sort, "substr(p.published_date, 1, 4) DESC")

        cur = self.engine.conn.cursor()
        count_sql = f"SELECT COUNT(*) AS c FROM papers p WHERE {' AND '.join(where_clauses)}"
        cur.execute(count_sql, params)
        total = cur.fetchone()["c"]

        sql = f"""
            SELECT p.id, p.doi, p.title, p.published_date, p.journal, p.author,
                   p.keywords, p.source, p.citation_count, p.language, p.journal_tier
            FROM papers p
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        cur.execute(sql, params + [limit, offset])
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["author"] = _safe_json_loads(r.get("author"))
            r["keywords"] = _safe_json_loads(r.get("keywords"))
            r["year"] = _extract_year(r.get("published_date"))

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "papers": rows,
        }

    def _handle_data_points_list(self, qs: Dict) -> Dict:
        """全局数据点表格接口。"""
        metric_name = (qs.get("metric_name", [""])[0] or "").strip()
        year_from = _int_or_none(qs, "year_from")
        year_to = _int_or_none(qs, "year_to")
        paper_id = _int_or_none(qs, "paper_id")
        try:
            limit = int(qs.get("limit", ["100"])[0])
            offset = int(qs.get("offset", ["0"])[0])
        except ValueError:
            limit, offset = 100, 0

        where_clauses = ["1=1", "COALESCE(p.is_placeholder, 0) = 0"]
        params: List[Any] = []
        if metric_name:
            where_clauses.append("dp.metric_name LIKE ?")
            params.append(f"%{metric_name}%")
        if year_from is not None:
            where_clauses.append("substr(p.published_date, 1, 4) >= ?")
            params.append(str(year_from))
        if year_to is not None:
            where_clauses.append("substr(p.published_date, 1, 4) <= ?")
            params.append(str(year_to))
        if paper_id is not None:
            where_clauses.append("dp.paper_id = ?")
            params.append(paper_id)

        cur = self.engine.conn.cursor()
        count_sql = f"""
            SELECT COUNT(*) AS c
            FROM paper_data_points dp
            JOIN papers p ON p.id = dp.paper_id
            WHERE {' AND '.join(where_clauses)}
        """
        cur.execute(count_sql, params)
        total = cur.fetchone()["c"]

        sql = f"""
            SELECT dp.id, dp.paper_id, dp.metric_name, dp.metric_value, dp.unit,
                   dp.context, dp.page, dp.confidence,
                   p.title AS paper_title, p.published_date
            FROM paper_data_points dp
            JOIN papers p ON p.id = dp.paper_id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY dp.id DESC
            LIMIT ? OFFSET ?
        """
        cur.execute(sql, params + [limit, offset])
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["year"] = _extract_year(r.get("published_date"))

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "data_points": rows,
        }

    def _handle_knowledge_list(self, qs: Dict) -> Dict:
        """全局知识卡片表格接口。"""
        q = (qs.get("q", [""])[0] or "").strip()
        year_from = _int_or_none(qs, "year_from")
        year_to = _int_or_none(qs, "year_to")
        try:
            limit = int(qs.get("limit", ["100"])[0])
            offset = int(qs.get("offset", ["0"])[0])
        except ValueError:
            limit, offset = 100, 0

        where_clauses = ["1=1", "COALESCE(p.is_placeholder, 0) = 0"]
        params: List[Any] = []
        if q:
            where_clauses.append("""(
                k.research_question LIKE ? OR k.core_answer LIKE ? OR
                k.key_claims LIKE ? OR k.evidence_generation LIKE ? OR
                k.boundaries LIKE ? OR k.reusable_inspiration LIKE ? OR
                p.title LIKE ?
            )""")
            like = f"%{q}%"
            params.extend([like, like, like, like, like, like, like])
        if year_from is not None:
            where_clauses.append("substr(p.published_date, 1, 4) >= ?")
            params.append(str(year_from))
        if year_to is not None:
            where_clauses.append("substr(p.published_date, 1, 4) <= ?")
            params.append(str(year_to))

        cur = self.engine.conn.cursor()
        count_sql = f"""
            SELECT COUNT(*) AS c
            FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE {' AND '.join(where_clauses)}
        """
        cur.execute(count_sql, params)
        total = cur.fetchone()["c"]

        sql = f"""
            SELECT k.paper_id, k.research_question, k.core_answer, k.key_claims,
                   k.evidence_generation, k.boundaries, k.reusable_inspiration,
                   p.title AS paper_title, p.published_date
            FROM paper_knowledge_cards k
            JOIN papers p ON p.id = k.paper_id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY p.published_date DESC
            LIMIT ? OFFSET ?
        """
        cur.execute(sql, params + [limit, offset])
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["year"] = _extract_year(r.get("published_date"))
            r["key_claims_count"] = _json_array_length(r.get("key_claims"))
            r["has_boundaries"] = bool(r.get("boundaries"))
            r["has_reusable_inspiration"] = bool(r.get("reusable_inspiration"))

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "knowledge": rows,
        }

    def _handle_methods_list(self, qs: Dict) -> Dict:
        """全局方法流程表格接口。"""
        q = (qs.get("q", [""])[0] or "").strip()
        year_from = _int_or_none(qs, "year_from")
        year_to = _int_or_none(qs, "year_to")
        try:
            limit = int(qs.get("limit", ["100"])[0])
            offset = int(qs.get("offset", ["0"])[0])
        except ValueError:
            limit, offset = 100, 0

        where_clauses = ["1=1", "COALESCE(p.is_placeholder, 0) = 0"]
        params: List[Any] = []
        if q:
            where_clauses.append("""(
                m.methodology LIKE ? OR m.workflow LIKE ? OR
                m.data_sources LIKE ? OR m.models_algorithms LIKE ? OR
                m.evaluation_metrics LIKE ? OR p.title LIKE ?
            )""")
            like = f"%{q}%"
            params.extend([like, like, like, like, like, like])
        if year_from is not None:
            where_clauses.append("substr(p.published_date, 1, 4) >= ?")
            params.append(str(year_from))
        if year_to is not None:
            where_clauses.append("substr(p.published_date, 1, 4) <= ?")
            params.append(str(year_to))

        cur = self.engine.conn.cursor()
        count_sql = f"""
            SELECT COUNT(*) AS c
            FROM paper_methods m
            JOIN papers p ON p.id = m.paper_id
            WHERE {' AND '.join(where_clauses)}
        """
        cur.execute(count_sql, params)
        total = cur.fetchone()["c"]

        sql = f"""
            SELECT m.paper_id, m.methodology, m.workflow, m.data_sources,
                   m.models_algorithms, m.evaluation_metrics,
                   p.title AS paper_title, p.published_date
            FROM paper_methods m
            JOIN papers p ON p.id = m.paper_id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY p.published_date DESC
            LIMIT ? OFFSET ?
        """
        cur.execute(sql, params + [limit, offset])
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["year"] = _extract_year(r.get("published_date"))

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "methods": rows,
        }

    def _handle_timeline(self, qs: Dict) -> Dict:
        """按年份统计论文、数据点、解析任务完成情况。"""
        year_from = _int_or_none(qs, "year_from")
        year_to = _int_or_none(qs, "year_to")

        cur = self.engine.conn.cursor()
        # 统一：只接受 4 位数字年份，避免空字符串或异常格式进入时间线
        _valid_year = "substr(published_date, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'"
        cur.execute(f"""
            SELECT substr(published_date, 1, 4) AS year, COUNT(*) AS c
            FROM papers
            WHERE published_date IS NOT NULL AND {_valid_year}
            GROUP BY year
            ORDER BY year
        """)
        paper_counts = {r["year"]: r["c"] for r in cur.fetchall()}

        cur.execute(f"""
            SELECT substr(p.published_date, 1, 4) AS year, COUNT(*) AS c
            FROM paper_data_points dp
            JOIN papers p ON p.id = dp.paper_id
            WHERE p.published_date IS NOT NULL AND {_valid_year}
            GROUP BY year
            ORDER BY year
        """)
        data_counts = {r["year"]: r["c"] for r in cur.fetchall()}

        cur.execute(f"""
            SELECT substr(p.published_date, 1, 4) AS year, COUNT(*) AS c
            FROM parse_jobs j
            JOIN papers p ON p.id = j.paper_id
            WHERE j.status = 'done' AND p.published_date IS NOT NULL
                  AND {_valid_year}
            GROUP BY year
            ORDER BY year
        """)
        parse_counts = {r["year"]: r["c"] for r in cur.fetchall()}

        all_years = set(paper_counts.keys()) | set(data_counts.keys()) | set(parse_counts.keys())
        if year_from is not None:
            all_years = {y for y in all_years if y and int(y) >= year_from}
        if year_to is not None:
            all_years = {y for y in all_years if y and int(y) <= year_to}

        years = sorted(all_years)
        return {
            "years": [
                {
                    "year": y,
                    "paper_count": paper_counts.get(y, 0),
                    "data_point_count": data_counts.get(y, 0),
                    "parse_done_count": parse_counts.get(y, 0),
                }
                for y in years
            ],
            "year_from": year_from,
            "year_to": year_to,
        }

    def _handle_jobs(self, qs: Dict) -> Dict:
        """查询解析任务状态与进度（支持分页、状态/阶段/错误类别过滤）。"""
        try:
            limit = int(qs.get("limit", ["50"])[0])
        except ValueError:
            limit = 50
        try:
            offset = int(qs.get("offset", ["0"])[0])
        except ValueError:
            offset = 0
        status_filter = (qs.get("status", [""])[0] or "").strip()
        stage_filter = (qs.get("stage", [""])[0] or "").strip()
        error_class_filter = (qs.get("error_class", [""])[0] or "").strip()

        cur = self.engine.conn.cursor()
        where = []
        params: List[Any] = []
        if status_filter:
            where.append("status = ?")
            params.append(status_filter)
        if stage_filter:
            where.append("stage = ?")
            params.append(stage_filter)
        if error_class_filter:
            where.append("error_class = ?")
            params.append(error_class_filter)
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        # 总数
        cur.execute(f"SELECT COUNT(*) AS c FROM parse_jobs {where_sql}", params)
        total = cur.fetchone()["c"]

        cur.execute(f"""
            SELECT id, paper_id, stage, status, parser_used, retry_count, max_retries,
                   parent_job_id, error_class, error_msg, mineru_task_id, started_at, finished_at
            FROM parse_jobs
            {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        rows = []
        for r in cur.fetchall():
            row = dict(r)
            status = row.get("status") or "pending"
            if status == "done":
                progress = 100
            elif status == "running":
                progress = 50
            elif status in ("failed", "permanent_failed"):
                progress = 100
            else:
                progress = 0
            row["progress"] = progress
            row["message"] = row.get("error_msg") or row.get("parser_used") or ""
            row["error"] = row.get("error_msg") or ""
            row["created_at"] = row.get("started_at") or ""
            rows.append(row)

        # 汇总统计
        cur.execute("""
            SELECT stage, status, COUNT(*) AS c
            FROM parse_jobs
            GROUP BY stage, status
        """)
        summary = [dict(r) for r in cur.fetchall()]

        return {
            "jobs": rows,
            "summary": summary,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _find_latest_failed_job(self, paper_id: int, stage: str) -> Optional[int]:
        """查找某论文某阶段最近一条失败 job 的 id。"""
        cur = self.engine.conn.cursor()
        cur.execute(
            """SELECT id FROM parse_jobs
               WHERE paper_id = ? AND stage = ? AND status IN ('failed', 'permanent_failed')
               ORDER BY id DESC LIMIT 1""",
            (paper_id, stage),
        )
        row = cur.fetchone()
        return row["id"] if row else None

    def _handle_jobs_stats(self) -> Dict[str, Any]:
        """返回任务失败统计与归档计数。"""
        from workflow.job_archive import get_failure_stats, count_archived
        stats = get_failure_stats(self.engine.conn)
        stats["archived_count"] = count_archived(self.engine.conn)
        return stats

    def log_message(self, fmt, *args):
        LOGGER.info(f"{self.address_string()} - {fmt % args}")


# ============================================================
# 工具函数
# ============================================================
def _int_or_none(qs: Dict, key: str) -> Optional[int]:
    if not qs.get(key):
        return None
    try:
        return int(qs[key][0])
    except (ValueError, TypeError):
        return None


def _extract_year(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    m = re.match(r"(\d{4})", str(date_str))
    return int(m.group(1)) if m else None


def _json_array_length(value: Any) -> int:
    """安全获取 JSON 数组长度；非数组返回 0。"""
    if value is None:
        return 0
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return len(parsed) if isinstance(parsed, list) else 0
        except json.JSONDecodeError:
            return 0
    return 0


def _safe_json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed
        except json.JSONDecodeError:
            pass
        # 尝试作为逗号/分号分隔的字符串列表返回
        return [x.strip() for x in re.split(r"[,;]", value) if x.strip()]
    return value


def _parse_keyword_row(value: Any) -> List[str]:
    """把 keywords 字段解析为关键词字符串列表。"""
    parsed = _safe_json_loads(value)
    if isinstance(parsed, list):
        return [str(x).strip() for x in parsed if str(x).strip()]
    if isinstance(parsed, str):
        return [parsed.strip()] if parsed.strip() else []
    return []


def _slug(text: str) -> str:
    """为关键词生成可用的节点 ID 后缀。"""
    return re.sub(r"[^\w\u4e00-\u9fff]+", "_", text).strip("_")[:60] or "kw"


# ============================================================
# 异步任务函数（各自新建 SearchEngine，避免连接跨线程共享）
# ============================================================
def _rebuild_task(proxy) -> Dict[str, Any]:
    engine = SearchEngine()
    try:
        proxy.set_progress(5, "检查索引...")
        engine.ensure_index()
        proxy.set_progress(10, "重建索引...")

        def _progress(current: int, total: int) -> None:
            pct = 10 + int((current / max(1, total)) * 85)
            proxy.set_progress(pct, f"索引论文 {current}/{total}")

        n = engine.rebuild_index(progress_callback=_progress)
        proxy.set_progress(100, "完成")
        return {"indexed": n}
    finally:
        engine.close()


def _sync_task(proxy, paper_id: int) -> Dict[str, Any]:
    engine = SearchEngine()
    try:
        proxy.set_progress(30, f"同步论文 {paper_id}...")
        engine.ensure_index()
        proxy.set_progress(60, "写入索引...")
        ok = engine.sync_paper(paper_id)
        proxy.set_progress(100, "完成")
        return {"paper_id": paper_id, "synced": ok}
    finally:
        engine.close()


def _collect_task(proxy, keyword: str, rows: int, max_pages: int, year_from: str = "", year_to: str = "", journal: str = "") -> Dict[str, Any]:
    """多源文献采集任务。
    
    参数:
        keyword: 检索关键词
        rows: 每页条数
        max_pages: 最大翻页数
        year_from: 起始年份（Crossref API 原生支持）
        year_to: 截止年份（Crossref API 原生支持）
        journal: 期刊名称筛选（预留，Crossref 列表 API 不支持原生过滤）
    """
    proxy.set_progress(5, f"开始采集关键词: {keyword}")
    wf_settings.apply_to_config()
    from collect.multi_source_collector import run_collection
    from config import SQLITE_PATH
    start_date = year_from.strip() if year_from else None
    end_date = year_to.strip() if year_to else None
    collection = run_collection(
        keyword,
        rows,
        max_pages,
        start_date,
        end_date,
        str(SQLITE_PATH),
        fix_authors_flag=True,
        return_details=True,
    )
    inserted = collection["inserted"]
    proxy.set_progress(100, f"采集完成，入库 {inserted} 条")
    return {
        "keyword": keyword,
        "inserted": inserted,
        "paper_ids": collection["paper_ids"],
    }


def _parse_task(proxy, source: str, limit: int, force: bool, paper_ids=None) -> Dict[str, Any]:
    """PDF 解析任务。"""
    proxy.set_progress(5, "查找待解析论文...")
    wf_settings.apply_to_config()
    from parse_new_papers import get_new_papers_with_oa
    from pdf.scheduler import process_paper
    from pdf.downloader import download_pdf_with_fallback

    papers = get_new_papers_with_oa(
        limit=limit,
        source_prefer=source,
        paper_ids=paper_ids,
    )
    total = len(papers)
    proxy.set_progress(10, f"找到 {total} 篇待解析论文")
    success = skipped = failed = 0

    for i, p in enumerate(papers):
        pct = 10 + int((i / max(1, total)) * 85)
        proxy.set_progress(pct, f"解析 {i + 1}/{total}: {p['title'][:40]}...")
        pdf_url = p.get('oa_url')
        if not pdf_url and p['doi'] and p['doi'].startswith('oa:'):
            pdf_url = p['doi'][3:]
        ok, file_path, err = download_pdf_with_fallback(
            p['doi'] or str(p['id']),
            oa_url=pdf_url,
            timeout=60,
            max_retries=2,
        )
        if not ok:
            LOGGER.warning("PDF download failed for paper_id=%s: %s", p['id'], err)
            failed += 1
            continue
        try:
            result = process_paper(p['id'], force=force)
            status = result.get('status', 'unknown')
            if status == 'done':
                success += 1
            elif status == 'skipped':
                skipped += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            LOGGER.exception("解析论文 %s 失败", p['id'])

    proxy.set_progress(100, f"解析完成: 成功={success}, 跳过={skipped}, 失败={failed}")
    return {"source": source, "limit": limit, "success": success, "skipped": skipped, "failed": failed}


def _extract_task(proxy, paper_ids=None) -> Dict[str, Any]:
    """LLM 提炼任务：首轮提取后，对仍失败的类型自动重试一次。"""
    proxy.set_progress(5, "查找待提炼论文...")
    wf_settings.apply_to_config()
    from extract_new_papers import get_newly_parsed_papers
    from phase3.extractor import extract_all_in_one
    from phase3.job_tracker import get_papers_needing_extraction
    from phase3.llm_client import LLMClient
    from phase3.embedder import embed_batch

    pending_ids = get_newly_parsed_papers()
    if paper_ids is not None:
        scoped = {int(paper_id) for paper_id in paper_ids}
        pending_ids = [paper_id for paper_id in pending_ids if paper_id in scoped]
    paper_ids = pending_ids
    total = len(paper_ids)
    proxy.set_progress(10, f"找到 {total} 篇待提炼论文")
    kc = methods_count = dp_count = errors = 0
    llm = LLMClient()

    def _count_result(result: Dict[str, Any]) -> None:
        nonlocal kc, methods_count, dp_count, errors
        if "card" in result:
            kc += 1
        if "methods" in result:
            methods_count += 1
        if "data_points" in result:
            dps = result["data_points"]
            dp_count += len(dps) if isinstance(dps, list) else dps.get("count", 0)
        errors += sum(1 for k in ("card_error", "methods_error", "data_points_error") if k in result)

    # 第一轮：全部待提炼论文（合并为一次 LLM 调用）
    for i, pid in enumerate(paper_ids):
        pct = 10 + int((i / max(1, total)) * 45)
        proxy.set_progress(pct, f"提炼 {i + 1}/{total}: 论文 {pid}")
        try:
            result = extract_all_in_one(pid, llm, force=False)
            _count_result(result)
        except Exception:
            errors += 1
            LOGGER.exception("提炼论文失败: %s", pid)

    # 第二轮：对首轮仍失败的论文执行一次性重试
    retry_ids = get_papers_needing_extraction()
    retry_ids = [paper_id for paper_id in retry_ids if paper_id in set(paper_ids)]
    retry_total = len(retry_ids)
    if retry_total:
        proxy.set_progress(60, f"首轮完成，{retry_total} 篇需重试")
        for i, pid in enumerate(retry_ids):
            pct = 60 + int((i / max(1, retry_total)) * 30)
            proxy.set_progress(pct, f"重试 {i + 1}/{retry_total}: 论文 {pid}")
            try:
                result = extract_all_in_one(pid, llm, force=True)
                _count_result(result)
            except Exception:
                errors += 1
                LOGGER.exception("重试提炼论文失败: %s", pid)

    if config.EMBEDDING_API_KEY:
        proxy.set_progress(95, "向量化...")
        try:
            embed_batch(paper_ids)
        except Exception:
            errors += 1
            LOGGER.exception("向量化失败")
    else:
        proxy.set_progress(95, "未配置 Embedding 服务，跳过可选向量化")

    proxy.set_progress(100, f"提炼完成: 知识卡片={kc}, 方法={methods_count}, 数据点={dp_count}, 错误={errors}")
    return {
        "papers": total,
        "retried": retry_total,
        "knowledge_cards": kc,
        "methods": methods_count,
        "data_points": dp_count,
        "errors": errors,
    }


def _retry_parse_task(proxy, paper_id: int, parent_job_id: Optional[int] = None) -> Dict[str, Any]:
    """重试单篇论文的 PDF 解析。"""
    proxy.set_progress(5, f"准备重新解析论文 {paper_id}")
    wf_settings.apply_to_config()
    with get_connection(row_factory=True) as conn:
        cur = conn.cursor()
        cur.execute("SELECT doi, oa_url FROM papers WHERE id = ?", (paper_id,))
        paper = cur.fetchone()
    if not paper:
        raise ValueError(f"论文不存在: {paper_id}")

    proxy.set_progress(15, "重新寻找并下载开放 PDF")
    from pdf.downloader import download_pdf_with_fallback
    ok, file_path, error = download_pdf_with_fallback(
        paper["doi"],
        oa_url=paper["oa_url"],
        timeout=config.PDF_DOWNLOAD_TIMEOUT,
        max_retries=config.PDF_MAX_RETRIES,
    )
    if not ok:
        raise RuntimeError(error or "无法下载开放 PDF")

    proxy.set_progress(55, "PDF 下载完成，开始解析全文")
    from pdf.scheduler import process_paper
    result = process_paper(paper_id, force=True, parent_job_id=parent_job_id)
    status = result.get("status", "unknown")
    proxy.set_progress(100, f"解析结果: {status}")
    return {
        "paper_id": paper_id,
        "status": status,
        "parser_used": result.get("parser_used"),
        "pdf_path": str(file_path),
    }


def _retry_extract_task(proxy, paper_id: int, parent_job_id: Optional[int] = None) -> Dict[str, Any]:
    """重试单篇论文的 LLM 提炼（仅重试失败类型）。"""
    proxy.set_progress(10, f"重新提炼论文 {paper_id}")
    wf_settings.apply_to_config()
    from phase3.extractor import extract_missing
    from phase3.llm_client import LLMClient
    from phase3.embedder import embed_paper
    llm = LLMClient()
    result = extract_missing(paper_id, llm, force=False, parent_job_id=parent_job_id)
    errors = sum(1 for k in ("card_error", "methods_error", "data_points_error") if k in result)
    if config.EMBEDDING_API_KEY:
        try:
            embed_paper(paper_id)
        except Exception:
            errors += 1
            LOGGER.exception("向量化失败: %s", paper_id)
    proxy.set_progress(100, f"提炼完成，错误数: {errors}")
    return {"paper_id": paper_id, "status": "done" if errors == 0 else "partial", "errors": errors}


def _quality_re_extract_task(proxy, paper_id: int) -> Dict[str, Any]:
    """质量监控面板触发的单篇论文重提取任务（force=True，强制覆盖全部三件套）。

    与 ``_retry_extract_task`` 的区别：
    - 本任务 ``force=True``，会覆盖 paper_knowledge_cards / paper_methods / paper_data_points 三张表；
    - 不传 parent_job_id，避免和历史失败任务形成复杂链路；
    - 终态仅汇报错误数，由前端展示给用户。
    """
    proxy.set_progress(10, f"重新提取论文 {paper_id}")
    wf_settings.apply_to_config()
    from phase3.extractor import extract_missing
    from phase3.llm_client import LLMClient
    from phase3.embedder import embed_paper
    llm = LLMClient()
    result = extract_missing(paper_id, llm, force=True, parent_job_id=None)
    errors = sum(1 for k in ("card_error", "methods_error", "data_points_error") if k in result)
    if config.EMBEDDING_API_KEY:
        try:
            embed_paper(paper_id)
        except Exception:
            errors += 1
            LOGGER.exception("向量化失败: %s", paper_id)
    proxy.set_progress(100, f"提取完成，错误数: {errors}")
    return {
        "paper_id": paper_id,
        "status": "done" if errors == 0 else "partial",
        "errors": errors,
    }


def _pipeline_task(proxy, keyword: str, rows: int, max_pages: int, year_from: str, year_to: str, journal: str, parse_source: str, parse_limit: int) -> Dict[str, Any]:
    """一键全流程任务：采集 → 解析 → 提炼，自动串联执行。"""
    result = {"keyword": keyword, "collect": {}, "parse": {}, "extract": {}}

    # 阶段 1: 采集 (0-30%)
    proxy.set_progress(0, f"【采集】开始: {keyword}")
    collect_result = _collect_task(proxy, keyword, rows, max_pages, year_from, year_to, journal)
    result["collect"] = collect_result
    if collect_result.get("inserted", 0) == 0:
        proxy.set_progress(100, "全流程结束: 采集无新增论文")
        return result

    # 阶段 2: 解析 (30-60%)
    proxy.set_progress(30, f"【解析】开始: {parse_source}, 上限 {parse_limit} 篇")
    paper_ids = collect_result.get("paper_ids", [])
    parse_result = _parse_task(
        proxy,
        parse_source,
        parse_limit,
        False,
        paper_ids=paper_ids,
    )
    result["parse"] = parse_result

    # 阶段 3: 提炼 (60-100%)
    proxy.set_progress(60, "【提炼】开始 LLM 知识提取")
    extract_result = _extract_task(proxy, paper_ids=paper_ids)
    result["extract"] = extract_result

    proxy.set_progress(100, f"全流程完成: 采集={collect_result.get('inserted',0)}, 解析成功={parse_result.get('success',0)}, 知识卡片={extract_result.get('knowledge_cards',0)}")
    return result


def _archive_jobs_task(proxy, days: int, batch: int) -> Dict[str, Any]:
    """归档旧 parse_jobs 记录到 parse_jobs_archive。"""
    proxy.set_progress(10, f"开始归档 {days} 天前的任务...")
    from workflow.job_archive import archive_old_jobs
    result = archive_old_jobs(days=days, batch=batch)
    proxy.set_progress(100, f"归档完成: {result['archived']} 条")
    return result


# ============================================================
# 启动
# ============================================================
def run_server(host: str = "127.0.0.1", port: int = 8088, ensure_index: bool = True):
    """启动 HTTP 服务器。"""
    engine = SearchEngine()
    if ensure_index:
        engine.ensure_index()
    SearchAPIHandler.engine = engine

    server = HTTPServer((host, port), SearchAPIHandler)
    LOGGER.info(f"检索 API 已启动: http://{host}:{port}")
    LOGGER.info(f"端口来源：环境变量 SEARCH_API_PORT 或命令行 --port（可在 config/.env 中修改 SEARCH_API_PORT）")
    LOGGER.info("端点:")
    LOGGER.info("  GET  /")
    LOGGER.info("  GET  /search?q=...&mode=keyword&year_from=2020&limit=20")
    LOGGER.info("  GET  /aggregate?q=...")
    LOGGER.info("  GET  /vector/search?q=...")
    LOGGER.info("  GET  /hybrid/search?q=...")
    LOGGER.info("  GET  /graph?entity_types=paper,author,keyword,data_point")
    LOGGER.info("  GET  /graph/diagnostics")
    LOGGER.info("  GET  /papers/list?q=...&sort=year_desc")
    LOGGER.info("  GET  /data_points/list?metric_name=...")
    LOGGER.info("  GET  /knowledge/list?q=...&year_from=...&year_to=...")
    LOGGER.info("  GET  /methods/list?q=...&year_from=...&year_to=...")
    LOGGER.info("  GET  /timeline?year_from=2010&year_to=2024")
    LOGGER.info("  GET  /paper/<id>")
    LOGGER.info("  GET  /paper/<id>/similar")
    LOGGER.info("  GET  /paper/<id>/knowledge")
    LOGGER.info("  GET  /paper/<id>/methods")
    LOGGER.info("  GET  /paper/<id>/data_points")
    LOGGER.info("  GET  /paper/<id>/citations")
    LOGGER.info("  GET  /compare/metric?metric_name=...")
    LOGGER.info("  GET  /authors/list?q=...&affiliation=...")
    LOGGER.info("  GET  /author/<id>")
    LOGGER.info("  GET  /author/<id>/papers")
    LOGGER.info("  GET  /author/<id>/network")
    LOGGER.info("  GET  /institution/network?affiliation=...")
    LOGGER.info("  GET  /stats")
    LOGGER.info("  GET  /health")
    LOGGER.info("  POST /rebuild")
    LOGGER.info("  POST /sync")
    LOGGER.info("  GET  /progress/<task_id>")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("服务器已停止")
    finally:
        engine.close()


# ============================================================
# Python SDK 客户端
# ============================================================
class SearchClient:
    """检索 API 的 Python SDK 客户端。

    用法：
        client = SearchClient("http://localhost:8088")
        result = client.search("livestock grazing", year_from=2020)
        for hit in result["hits"]:
            print(hit["title"])
    """

    def __init__(self, base_url: str = "http://localhost:8088", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(self, q: str, mode: str = "keyword", fields: Optional[List[str]] = None,
               year_from: Optional[int] = None, year_to: Optional[int] = None,
               year: Optional[str] = None, journal: Optional[str] = None,
               author: Optional[str] = None, language: Optional[str] = None,
               source: Optional[str] = None, doi: Optional[str] = None,
               journal_tier: Optional[str] = None,
               journal_tiers: Optional[List[str]] = None,
               limit: int = 20, offset: int = 0,
               sort: str = "relevance", highlight: bool = True) -> Dict:
        """执行检索。"""
        params = {
            "q": q, "mode": mode, "limit": limit, "offset": offset,
            "sort": sort, "highlight": "1" if highlight else "0",
        }
        if fields:
            params["fields"] = ",".join(fields)
        if year_from: params["year_from"] = year_from
        if year_to: params["year_to"] = year_to
        if year: params["year"] = year
        if journal: params["journal"] = journal
        if author: params["author"] = author
        if language: params["language"] = language
        if source: params["source"] = source
        if doi: params["doi"] = doi
        if journal_tiers:
            params["journal_tiers"] = ",".join(journal_tiers)
        elif journal_tier:
            params["journal_tier"] = journal_tier

        r = requests.get(f"{self.base_url}/search", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def aggregate(self, q: str = "*", mode: str = "keyword") -> Dict:
        """获取聚合面板。"""
        r = requests.get(f"{self.base_url}/aggregate",
                        params={"q": q, "mode": mode}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def vector_search(self, q: str, top_k: int = 10, chunk_type: Optional[str] = None,
                      paper_id: Optional[int] = None) -> Dict:
        """向量语义检索。"""
        params = {"q": q, "top_k": top_k}
        if chunk_type:
            params["chunk_type"] = chunk_type
        if paper_id:
            params["paper_id"] = paper_id
        r = requests.get(f"{self.base_url}/vector/search", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def hybrid_search(self, q: str, top_k: int = 10,
                      fts_weight: float = 0.4, vector_weight: float = 0.6) -> Dict:
        """混合检索。"""
        params = {
            "q": q, "top_k": top_k,
            "fts_weight": fts_weight, "vector_weight": vector_weight,
        }
        r = requests.get(f"{self.base_url}/hybrid/search", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_paper(self, paper_id: int) -> Dict:
        """获取论文详情。"""
        r = requests.get(f"{self.base_url}/paper/{paper_id}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_paper_similar(self, paper_id: int, top_k: int = 5) -> Dict:
        """获取相似论文。"""
        r = requests.get(f"{self.base_url}/paper/{paper_id}/similar",
                        params={"top_k": top_k}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_paper_knowledge(self, paper_id: int) -> Dict:
        """获取论文知识卡片。"""
        r = requests.get(f"{self.base_url}/paper/{paper_id}/knowledge", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_paper_methods(self, paper_id: int) -> Dict:
        """获取论文方法流程。"""
        r = requests.get(f"{self.base_url}/paper/{paper_id}/methods", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_paper_data_points(self, paper_id: int) -> Dict:
        """获取论文数据点。"""
        r = requests.get(f"{self.base_url}/paper/{paper_id}/data_points", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def compare_metric(self, metric_name: str, top_k: int = 20) -> Dict:
        """跨论文指标对比。"""
        r = requests.get(f"{self.base_url}/compare/metric",
                        params={"metric_name": metric_name, "top_k": top_k},
                        timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_authors(self, q: str = "", affiliation: str = "",
                     limit: int = 50, offset: int = 0) -> Dict:
        """学者列表与检索。"""
        params = {"q": q, "limit": limit, "offset": offset}
        if affiliation:
            params["affiliation"] = affiliation
        r = requests.get(f"{self.base_url}/authors/list", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_author(self, author_id: int) -> Dict:
        """学者画像。"""
        r = requests.get(f"{self.base_url}/author/{author_id}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_author_papers(self, author_id: int, limit: int = 50, offset: int = 0) -> Dict:
        """学者论文列表。"""
        r = requests.get(f"{self.base_url}/author/{author_id}/papers",
                         params={"limit": limit, "offset": offset}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_author_network(self, author_id: int, max_nodes: int = 50) -> Dict:
        """学者合作网络。"""
        r = requests.get(f"{self.base_url}/author/{author_id}/network",
                         params={"max_nodes": max_nodes}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_institution_network(self, affiliation: str = "", max_nodes: int = 60, min_papers: int = 1) -> Dict:
        """机构合作网络。"""
        params = {"max_nodes": max_nodes, "min_papers": min_papers}
        if affiliation:
            params["affiliation"] = affiliation
        r = requests.get(f"{self.base_url}/institution/network", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def stats(self) -> Dict:
        """获取索引统计。"""
        r = requests.get(f"{self.base_url}/stats", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def health(self) -> Dict:
        """健康检查。"""
        r = requests.get(f"{self.base_url}/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def rebuild(self) -> Dict:
        """异步重建索引（管理操作）。"""
        r = requests.post(f"{self.base_url}/rebuild", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def sync(self, paper_id: int) -> Dict:
        """异步同步单篇论文。"""
        r = requests.post(f"{self.base_url}/sync",
                         json={"paper_id": paper_id}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_progress(self, task_id: str) -> Dict:
        """查询任务进度。"""
        r = requests.get(f"{self.base_url}/progress/{task_id}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="检索 REST API")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8088, help="监听端口")
    parser.add_argument("--no-ensure-index", action="store_true", help="启动时不自动创建索引")
    args = parser.parse_args()

    run_server(args.host, args.port, ensure_index=not args.no_ensure_index)


if __name__ == "__main__":
    main()
