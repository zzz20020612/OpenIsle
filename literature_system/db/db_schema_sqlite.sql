PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS papers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doi TEXT NOT NULL UNIQUE,
  wos_id TEXT,
  source TEXT,
  title TEXT,
  author TEXT,
  publisher TEXT,
  published_date TEXT,
  abstract TEXT,
  journal TEXT,
  journal_abbr TEXT,
  volume TEXT,
  issue TEXT,
  page TEXT,
  issn TEXT,
  article_type TEXT,
  subject TEXT,
  keywords TEXT,
  journal_tier TEXT,
  oa_url TEXT,
  oa_category TEXT,
  citation_count INTEGER DEFAULT 0,
  wos_times_cited INTEGER DEFAULT 0,
  references_count INTEGER DEFAULT 0,
  language TEXT,
  external_ids TEXT,
  meta_json TEXT,
  is_placeholder INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS funders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doi TEXT,
  name TEXT NOT NULL,
  award TEXT,
  UNIQUE (doi, name)
);

CREATE TABLE IF NOT EXISTS licenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  content_version TEXT NOT NULL DEFAULT '',
  start_date TEXT,
  UNIQUE (url, content_version)
);

CREATE TABLE IF NOT EXISTS relations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  relation_type TEXT NOT NULL,
  relation_id TEXT NOT NULL,
  relation_id_type TEXT NOT NULL,
  asserted_by TEXT NOT NULL DEFAULT '',
  UNIQUE (relation_type, relation_id, relation_id_type, asserted_by)
);

CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  content_type TEXT NOT NULL DEFAULT '',
  content_version TEXT NOT NULL DEFAULT '',
  intended_application TEXT NOT NULL DEFAULT '',
  UNIQUE (url, content_type, content_version, intended_application)
);

CREATE TABLE IF NOT EXISTS paper_funders (
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  funder_id INTEGER NOT NULL REFERENCES funders(id) ON DELETE CASCADE,
  PRIMARY KEY (paper_id, funder_id)
);

CREATE TABLE IF NOT EXISTS paper_licenses (
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  license_id INTEGER NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
  PRIMARY KEY (paper_id, license_id)
);

CREATE TABLE IF NOT EXISTS paper_relations (
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  relation_id INTEGER NOT NULL REFERENCES relations(id) ON DELETE CASCADE,
  PRIMARY KEY (paper_id, relation_id)
);

CREATE TABLE IF NOT EXISTS paper_links (
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  link_id INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
  PRIMARY KEY (paper_id, link_id)
);

CREATE TABLE IF NOT EXISTS citations (
  citing_doi TEXT NOT NULL,
  cited_doi TEXT NOT NULL,
  PRIMARY KEY (citing_doi, cited_doi)
);

CREATE TABLE IF NOT EXISTS authors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  orcid TEXT,
  researcher_id TEXT,
  scopus_author_id TEXT,
  given_name TEXT,
  family_name TEXT,
  full_name TEXT,
  canonical_name TEXT,
  display_name TEXT,
  current_affiliation TEXT,
  affiliation TEXT,
  country TEXT,
  email TEXT,
  match_method TEXT,
  match_confidence TEXT,
  total_publications INTEGER DEFAULT 0,
  paper_count INTEGER DEFAULT 0,
  citation_count INTEGER DEFAULT 0,
  total_citations INTEGER DEFAULT 0,
  h_index REAL DEFAULT 0,
  meta_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_authors_orcid ON authors(orcid) WHERE orcid IS NOT NULL AND orcid != '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_authors_researcher_id ON authors(researcher_id) WHERE researcher_id IS NOT NULL AND researcher_id != '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_authors_scopus_id ON authors(scopus_author_id) WHERE scopus_author_id IS NOT NULL AND scopus_author_id != '';

CREATE TABLE IF NOT EXISTS paper_authors (
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
  author_order INTEGER DEFAULT 0,
  is_corresponding INTEGER DEFAULT 0,
  PRIMARY KEY (paper_id, author_id)
);

CREATE TABLE IF NOT EXISTS paper_fulltext (
  paper_id INTEGER PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
  parser_used TEXT,
  parse_quality TEXT,
  full_text TEXT,
  full_markdown TEXT,
  char_count INTEGER DEFAULT 0,
  page_count INTEGER DEFAULT 0,
  parsed_at TEXT
);

CREATE TABLE IF NOT EXISTS paper_sections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  section_type TEXT,
  heading TEXT,
  content TEXT,
  page_start INTEGER,
  page_end INTEGER,
  order_idx INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS paper_figures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  fig_label TEXT,
  fig_type TEXT,
  caption TEXT,
  file_path TEXT,
  page INTEGER
);

CREATE TABLE IF NOT EXISTS citations_v2 (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  citing_paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  cited_doi TEXT,
  cited_title TEXT,
  cited_authors TEXT,
  cited_year INTEGER,
  cited_journal TEXT,
  raw_reference TEXT,
  match_method TEXT,
  match_confidence REAL
);

CREATE TABLE IF NOT EXISTS paper_knowledge_cards (
  paper_id INTEGER PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
  research_question TEXT,
  core_answer TEXT,
  key_claims TEXT,
  evidence_generation TEXT,
  boundaries TEXT,
  reusable_inspiration TEXT,
  source_section_ids TEXT,
  extraction_method TEXT,
  extracted_at TEXT,
  quality_score REAL,
  audit_report TEXT,
  prompt_version TEXT
);

CREATE TABLE IF NOT EXISTS paper_methods (
  paper_id INTEGER PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
  methodology TEXT,
  workflow TEXT,
  data_sources TEXT,
  models_algorithms TEXT,
  evaluation_metrics TEXT,
  methods_section_id INTEGER,
  extraction_method TEXT,
  extracted_at TEXT
);

CREATE TABLE IF NOT EXISTS paper_data_points (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  metric_name TEXT,
  metric_value TEXT,
  metric_value_numeric REAL,
  metric_value_original TEXT,
  metric_name_normalized TEXT,
  unit TEXT,
  context TEXT,
  section_id INTEGER,
  figure_id INTEGER,
  page INTEGER,
  significance TEXT,
  confidence TEXT,
  is_review_record INTEGER DEFAULT 0,
  extraction_method TEXT,
  extracted_at TEXT
);

CREATE TABLE IF NOT EXISTS paper_embeddings (
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  chunk_type TEXT NOT NULL,
  chunk_id INTEGER NOT NULL,
  embedding BLOB NOT NULL,
  model_name TEXT,
  embedded_at TEXT,
  PRIMARY KEY (paper_id, chunk_type, chunk_id)
);

CREATE TABLE IF NOT EXISTS parse_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id INTEGER REFERENCES papers(id) ON DELETE CASCADE,
  stage TEXT NOT NULL DEFAULT 'parse',
  status TEXT NOT NULL DEFAULT 'pending',
  parser_used TEXT,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,
  parent_job_id INTEGER REFERENCES parse_jobs(id),
  error_class TEXT,
  error_msg TEXT,
  mineru_task_id TEXT,
  started_at TEXT,
  finished_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parse_jobs_archive (
  id INTEGER PRIMARY KEY,
  paper_id INTEGER,
  stage TEXT,
  status TEXT,
  parser_used TEXT,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,
  parent_job_id INTEGER,
  error_class TEXT,
  error_msg TEXT,
  mineru_task_id TEXT,
  started_at TEXT,
  finished_at TEXT,
  archived_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_settings (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_papers_published_date ON papers(published_date);
CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title);
CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
CREATE INDEX IF NOT EXISTS idx_paper_sections_paper ON paper_sections(paper_id, order_idx);
CREATE INDEX IF NOT EXISTS idx_paper_figures_paper ON paper_figures(paper_id);
CREATE INDEX IF NOT EXISTS idx_data_points_paper ON paper_data_points(paper_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON parse_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_paper ON parse_jobs(paper_id);
CREATE INDEX IF NOT EXISTS idx_jobs_parent ON parse_jobs(parent_job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_error_class ON parse_jobs(error_class);
