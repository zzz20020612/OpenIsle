import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
load_dotenv(CONFIG_DIR / ".env")
# In the integrated OpenIsle workspace, reuse the same private environment file
# as the AI screening service. A literature-specific config file still wins.
load_dotenv(ROOT_DIR.parent / ".env")

# 前端与 API 服务配置
# 留空或未设置时回退到 ROOT_DIR/frontend，避免不同 cwd 下相对路径解析失败
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR") or ROOT_DIR / "frontend")
SEARCH_API_PORT = int(os.getenv("SEARCH_API_PORT", "8088"))

# Crossref 配置
CROSSREF_API_URL = os.getenv("CROSSREF_API_URL", "https://api.crossref.org/works")
CROSSREF_MAILTO = os.getenv("CROSSREF_MAILTO", "")
CROSSREF_USER_AGENT = os.getenv("CROSSREF_USER_AGENT", "literature-system/0.1")
KEYWORD = os.getenv("CROSSREF_KEYWORD", "machine learning")
ROWS_PER_PAGE = int(os.getenv("CROSSREF_ROWS_PER_PAGE", "100"))
MAX_PAGES = int(os.getenv("CROSSREF_MAX_PAGES", "10"))
SLEEP_BETWEEN = float(os.getenv("CROSSREF_SLEEP_BETWEEN", "1"))
CROSSREF_START_DATE = os.getenv("CROSSREF_START_DATE", "")
CROSSREF_END_DATE = os.getenv("CROSSREF_END_DATE", "")
POLITE_REQUESTING = os.getenv("POLITE_REQUESTING", "true").lower() in ("true", "1", "t")
# Article Type 标准化映射表（Crossref API原始值 → 标准化中文/英文标签）
ARTICLE_TYPE_MAPPING = {
    # 期刊类
    "journal-article": "Journal Article",
    "journal-issue": "Journal Issue",
    "journal-review-article": "Journal Review",
    # 会议类
    "proceedings-article": "Conference Paper",
    # 书籍类
    "book-chapter": "Book Chapter",
    "book": "Book",
    "edited-book": "Edited Book",
    "reference-book": "Reference Book",
    "monograph": "Monograph",
    "proceedings": "Proceedings",
    # 报告类
    "report": "Report",
    "report-component": "Report Component",
    # 预印本/ posted content
    "posted-content": "Preprint",
    # 同行评审
    "peer-review": "Peer Review",
    # 数据集
    "dataset": "Dataset",
    # 其他
    "other": "Other",
    "component": "Component",
    "reference-entry": "Reference Entry",
    "dissertation": "Dissertation",
    "book-series": "Book Series",
    "book-set": "Book Set",
    "journal-volume": "Journal Volume",
    "book-part": "Book Part",
    "standard": "Standard",
    "reference-edition": "Reference Edition",
    "news": "News",
    "magazine-article": "Magazine Article",
    "newspaper-article": "Newspaper Article",
}

# Article types filter: comma-separated list of Crossref type values
# Examples: "journal-article", "proceedings-article", "book-chapter"
# Empty string means no filter (keep all types)
ARTICLE_TYPES_FILTER = os.getenv("CROSSREF_ARTICLE_TYPES_FILTER", "")

# Unpaywall requires a real contact address. Keep it configurable so the
# downloader is not tied to a developer's personal account.
UNPAYWALL_EMAIL = os.getenv(
    "UNPAYWALL_EMAIL",
    CROSSREF_MAILTO or "adminmail@openisle.com",
)

# 数据存储路径
RAW_JSON_DIR = Path(os.getenv("RAW_JSON_DIR", ROOT_DIR / "data"))
CHECKPOINT_DIR = Path(os.getenv("CHECKPOINT_DIR", ROOT_DIR / "data" / "checkpoints"))

# 数据库配置
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname": os.getenv("DB_NAME", "literature"),
    "sslmode": os.getenv("DB_SSLMODE", "prefer"),
}
# 留空时回退到 ROOT_DIR/db/literature.db，避免不同 cwd 下相对路径指向空壳 db
SQLITE_PATH = Path(os.getenv("SQLITE_PATH") or ROOT_DIR / "db" / "literature.db")

# Semantic Scholar API 配置
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
SEMANTIC_SCHOLAR_API_URL = os.getenv("SEMANTIC_SCHOLAR_API_URL", "https://api.semanticscholar.org/graph/v1")
SEMANTIC_SCHOLAR_RATE_LIMIT = int(os.getenv("SEMANTIC_SCHOLAR_RATE_LIMIT", "1000"))  # 次/5分钟（有Key时）

# MinerU API 配置（PDF解析）
MINERU_API_KEY = os.getenv("MINERU_API_KEY", "")
MINERU_RESULT_FALLBACK_PROXY = os.getenv("MINERU_RESULT_FALLBACK_PROXY", "")
MINERU_API_URL = os.getenv("MINERU_API_URL", "https://mineru.net/api/v4/extract/task")
MINERU_MAX_RETRIES = int(os.getenv("MINERU_MAX_RETRIES", "5"))
MINERU_UPLOAD_TIMEOUT = int(os.getenv("MINERU_UPLOAD_TIMEOUT", "120"))
MINERU_TASK_POLL_INTERVAL = int(os.getenv("MINERU_TASK_POLL_INTERVAL", "10"))
MINERU_TASK_MAX_WAIT = int(os.getenv("MINERU_TASK_MAX_WAIT", "600"))
MINERU_DAILY_QUOTA = int(os.getenv("MINERU_DAILY_QUOTA", "200"))

# Web of Science API 配置（Clarivate，需机构订阅）
WOS_API_KEY = os.getenv("WOS_API_KEY", "")
WOS_API_URL = os.getenv("WOS_API_URL", "https://api.clarivate.com/apis/wos")
WOS_USER_AGENT = os.getenv("WOS_USER_AGENT", "literature-system/0.1 (Academic Research)")
WOS_SLEEP_BETWEEN = float(os.getenv("WOS_SLEEP_BETWEEN", "1"))

# Scopus API 配置（用于论文检索与作者画像补全）
SCOPUS_API_KEYS = [
    k.strip() for k in os.getenv("SCOPUS_API_KEYS", "").split(",") if k.strip()
]
SCOPUS_INSTTOKEN = os.getenv("SCOPUS_INSTTOKEN", "")
SCOPUS_SLEEP_BETWEEN = float(os.getenv("SCOPUS_SLEEP_BETWEEN", "1"))

# PDF 下载策略优先级（数字越小优先级越高）
# 0: 跳过, 1: 最高, 2: 次高, 3: 第三, 4: 第四
PDF_DOWNLOAD_STRATEGY = {
    "crossref_text_mining": int(os.getenv("PDF_STRATEGY_CROSSREF_TEXT_MINING", "1")),  # Crossref API text-mining 链接
    "crossref_pdf": int(os.getenv("PDF_STRATEGY_CROSSREF_PDF", "2")),  # Crossref API PDF 链接
    "oa_url": int(os.getenv("PDF_STRATEGY_OA_URL", "3")),  # OA URL 直接下载
    "doi_redirect": int(os.getenv("PDF_STRATEGY_DOI_REDIRECT", "4")),  # doi.org 重定向
    "unpaywall": int(os.getenv("PDF_STRATEGY_UNPAYWALL", "5")),  # Unpaywall API 查找 OA 版本
}

# PDF 解析策略优先级（数字越小优先级越高）
# 0: 跳过, 1: MinerU API（主力）, 2: PyMuPDF（快速兜底）, 3: Marker（最终备选）
PDF_PARSER_STRATEGY = {
    "mineru_api": int(os.getenv("PDF_PARSER_MINERU_API", "1")),  # MinerU API（主力）
    "pymupdf": int(os.getenv("PDF_PARSER_PYMUPDF", "2")),  # PyMuPDF（快速兜底）
    "marker_gpu": int(os.getenv("PDF_PARSER_MARKER_GPU", "3")),  # Marker GPU（最终备选）
    "marker_cpu": int(os.getenv("PDF_PARSER_MARKER_CPU", "4")),  # Marker CPU
}

# PDF 下载配置
PDF_DOWNLOAD_DIR = os.getenv("PDF_DOWNLOAD_DIR", ROOT_DIR / "pdfs")
PDF_USER_AGENT = os.getenv(
    "PDF_USER_AGENT",
    f"LiteratureSystem/1.0 (Academic Research; mailto:{UNPAYWALL_EMAIL})",
)
PDF_DOWNLOAD_TIMEOUT = int(os.getenv("PDF_DOWNLOAD_TIMEOUT", "60"))
PDF_MAX_RETRIES = int(os.getenv("PDF_MAX_RETRIES", "3"))
PDF_WORKERS = int(os.getenv("PDF_WORKERS", "3"))

# scansci-pdf 桥接配置（可选增强 PDF 下载成功率）
PDF_ENABLE_SCISCI = os.getenv("PDF_ENABLE_SCISCI", "false").lower() in ("true", "1", "t")
PDF_SOURCE_WHITELIST = os.getenv(
    "PDF_SOURCE_WHITELIST",
    "oa_url,unpaywall,openalex_oa,core,europepmc,pmc,semanticscholar,arxiv,publishers",
)
PDF_SOURCE_CONNECT_TIMEOUT = int(os.getenv("PDF_SOURCE_CONNECT_TIMEOUT", "10"))
PDF_SOURCE_READ_TIMEOUT = int(os.getenv("PDF_SOURCE_READ_TIMEOUT", "20"))
PDF_TIER1_WORKERS = int(os.getenv("PDF_TIER1_WORKERS", "5"))

# 外部 API Keys（供 scansci-pdf 等来源使用）
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "")
CORE_API_KEY = os.getenv("CORE_API_KEY", "")
NETWORK_PROXY = os.getenv("NETWORK_PROXY", "")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================================
# 第三阶段：LLM 知识提炼配置
# ============================================================
# LLM 提取器配置（OpenAI 兼容接口，默认七牛云 + DeepSeek）
LLM_API_KEY = (
    os.getenv("LLM_API_KEY")
    or os.getenv("AI_SCREENING_API_KEY")
    or os.getenv("OPENAI_API_KEY", "")
)
LLM_BASE_URL = (
    os.getenv("LLM_BASE_URL")
    or os.getenv("AI_SCREENING_BASE_URL")
    or os.getenv("OPENAI_BASE_URL")
    or "https://api.qnaigc.com/v1"
)
LLM_MODEL = (
    os.getenv("LLM_MODEL")
    or os.getenv("AI_SCREENING_MODEL")
    or os.getenv("OPENAI_MODEL")
    or "deepseek/deepseek-v4-flash"
)
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))  # 低温度保证提取一致性
LLM_REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "120"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_SLEEP_BETWEEN = float(os.getenv("LLM_SLEEP_BETWEEN", "1"))

# Embedding 配置（硅基流动 + Qwen3-Embedding-4B）
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "2560"))  # Qwen3-Embedding-4B 默认 2560 维
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

# 向量检索配置（sqlite-vec 扩展）
VECTOR_SEARCH_TOP_K = int(os.getenv("VECTOR_SEARCH_TOP_K", "10"))
SQLITE_VEC_EXTENSION_PATH = os.getenv("SQLITE_VEC_EXTENSION_PATH", "")  # 留空则自动加载

# Phase3 提取配置
PHASE3_PROMPT_VERSION = os.getenv("PHASE3_PROMPT_VERSION", "v1")
PHASE3_MAX_CLAIMS = int(os.getenv("PHASE3_MAX_CLAIMS", "5"))  # key_claims 最多条数
PHASE3_AUDIT_ENABLED = os.getenv("PHASE3_AUDIT_ENABLED", "true").lower() in ("true", "1", "t")
