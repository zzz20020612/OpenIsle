ALTER TABLE paper_authors
  ADD COLUMN given_name VARCHAR(255) DEFAULT NULL,
  ADD COLUMN middle_name VARCHAR(255) DEFAULT NULL,
  ADD COLUMN family_name VARCHAR(255) DEFAULT NULL,
  ADD COLUMN author_role VARCHAR(255) DEFAULT NULL;

ALTER TABLE paper_profiles
  ADD COLUMN preprint_statement TEXT DEFAULT NULL,
  ADD COLUMN ai_use_disclosure TEXT DEFAULT NULL,
  ADD COLUMN private_comments TEXT DEFAULT NULL,
  ADD COLUMN all_authors_consent BIT(1) NOT NULL DEFAULT b'0',
  ADD COLUMN originality_confirmed BIT(1) NOT NULL DEFAULT b'0',
  ADD COLUMN rights_confirmed BIT(1) NOT NULL DEFAULT b'0',
  ADD COLUMN corresponding_author_contact_confirmed BIT(1) NOT NULL DEFAULT b'0',
  ADD COLUMN corresponding_author_contact_confirmed_at DATETIME(6) DEFAULT NULL,
  ADD COLUMN corresponding_author_contact_confirmed_by BIGINT DEFAULT NULL,
  ADD KEY idx_paper_profiles_contact_confirmed_by (corresponding_author_contact_confirmed_by),
  ADD CONSTRAINT fk_paper_profiles_contact_confirmed_by
    FOREIGN KEY (corresponding_author_contact_confirmed_by) REFERENCES users (id)
    ON DELETE SET NULL ON UPDATE CASCADE;

CREATE TABLE paper_submission_drafts (
  id BIGINT NOT NULL AUTO_INCREMENT,
  created_by BIGINT NOT NULL,
  manuscript_type VARCHAR(255) DEFAULT NULL,
  form_data_json LONGTEXT NOT NULL,
  current_section VARCHAR(255) DEFAULT NULL,
  status VARCHAR(255) NOT NULL DEFAULT 'IN_PROGRESS',
  submitted_paper_id BIGINT DEFAULT NULL,
  idempotency_key VARCHAR(255) DEFAULT NULL,
  version BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_paper_submission_drafts_submitted_paper (submitted_paper_id),
  UNIQUE KEY uk_paper_submission_drafts_idempotency_key (idempotency_key),
  KEY idx_paper_submission_drafts_owner_status (created_by, status, updated_at),
  CONSTRAINT fk_paper_submission_drafts_created_by
    FOREIGN KEY (created_by) REFERENCES users (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_paper_submission_drafts_submitted_paper
    FOREIGN KEY (submitted_paper_id) REFERENCES paper_profiles (id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE paper_submission_files (
  id BIGINT NOT NULL AUTO_INCREMENT,
  draft_id BIGINT NOT NULL,
  original_file_name VARCHAR(255) NOT NULL,
  display_name VARCHAR(255) NOT NULL,
  content_type VARCHAR(255) NOT NULL,
  file_size BIGINT NOT NULL,
  role VARCHAR(255) NOT NULL,
  description TEXT DEFAULT NULL,
  visibility VARCHAR(255) NOT NULL DEFAULT 'PRIVATE',
  storage_key VARCHAR(512) NOT NULL,
  upload_status VARCHAR(255) NOT NULL DEFAULT 'PENDING',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_paper_submission_files_draft_order (draft_id, sort_order, id),
  CONSTRAINT fk_paper_submission_files_draft
    FOREIGN KEY (draft_id) REFERENCES paper_submission_drafts (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE paper_files (
  id BIGINT NOT NULL AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  original_file_name VARCHAR(255) NOT NULL,
  display_name VARCHAR(255) NOT NULL,
  content_type VARCHAR(255) NOT NULL,
  file_size BIGINT NOT NULL,
  role VARCHAR(255) NOT NULL,
  description TEXT DEFAULT NULL,
  visibility VARCHAR(255) NOT NULL DEFAULT 'PRIVATE',
  storage_key VARCHAR(512) NOT NULL,
  upload_status VARCHAR(255) NOT NULL DEFAULT 'UPLOADED',
  sort_order INT NOT NULL DEFAULT 0,
  view_count BIGINT NOT NULL DEFAULT 0,
  download_count BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_paper_files_paper_order (paper_id, sort_order, id),
  KEY idx_paper_files_paper_role (paper_id, role),
  CONSTRAINT fk_paper_files_paper
    FOREIGN KEY (paper_id) REFERENCES paper_profiles (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE paper_author_affiliations (
  id BIGINT NOT NULL AUTO_INCREMENT,
  paper_author_id BIGINT NOT NULL,
  institution_id BIGINT NOT NULL,
  organization_name VARCHAR(255) NOT NULL,
  department VARCHAR(255) DEFAULT NULL,
  address_line_1 VARCHAR(255) DEFAULT NULL,
  address_line_2 VARCHAR(255) DEFAULT NULL,
  country VARCHAR(255) NOT NULL,
  region VARCHAR(255) DEFAULT NULL,
  city VARCHAR(255) NOT NULL,
  postal_code VARCHAR(255) DEFAULT NULL,
  primary_affiliation BIT(1) NOT NULL DEFAULT b'0',
  display_order INT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_paper_author_affiliations_author_order (paper_author_id, display_order, id),
  KEY idx_paper_author_affiliations_institution (institution_id),
  CONSTRAINT fk_paper_author_affiliations_author
    FOREIGN KEY (paper_author_id) REFERENCES paper_authors (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_paper_author_affiliations_institution
    FOREIGN KEY (institution_id) REFERENCES institutions (id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE paper_funding_records (
  id BIGINT NOT NULL AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  funder_name VARCHAR(255) NOT NULL,
  grant_id VARCHAR(255) DEFAULT NULL,
  display_order INT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  KEY idx_paper_funding_records_paper_order (paper_id, display_order, id),
  CONSTRAINT fk_paper_funding_records_paper
    FOREIGN KEY (paper_id) REFERENCES paper_profiles (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
