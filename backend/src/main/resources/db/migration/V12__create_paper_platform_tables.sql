CREATE TABLE IF NOT EXISTS institutions (
  id BIGINT NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  country VARCHAR(255) DEFAULT NULL,
  type VARCHAR(255) DEFAULT NULL,
  website VARCHAR(255) DEFAULT NULL,
  verified BIT(1) NOT NULL DEFAULT b'0',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_institutions_name (name),
  KEY idx_institutions_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS expert_profiles (
  id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT DEFAULT NULL,
  display_name VARCHAR(255) NOT NULL,
  email VARCHAR(255) DEFAULT NULL,
  orcid VARCHAR(255) DEFAULT NULL,
  primary_institution_id BIGINT DEFAULT NULL,
  country VARCHAR(255) DEFAULT NULL,
  identity_status VARCHAR(255) NOT NULL DEFAULT 'UNMATCHED',
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_expert_profiles_orcid (orcid),
  KEY idx_expert_profiles_email (email),
  KEY idx_expert_profiles_name (display_name),
  KEY idx_expert_profiles_user (user_id),
  KEY idx_expert_profiles_primary_institution (primary_institution_id),
  CONSTRAINT fk_expert_profiles_user
    FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_expert_profiles_primary_institution
    FOREIGN KEY (primary_institution_id) REFERENCES institutions (id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS paper_profiles (
  id BIGINT NOT NULL AUTO_INCREMENT,
  post_id BIGINT NOT NULL,
  title VARCHAR(255) NOT NULL,
  abstract_text TEXT NOT NULL,
  keywords TEXT DEFAULT NULL,
  references_text TEXT DEFAULT NULL,
  manuscript_files TEXT DEFAULT NULL,
  supplementary_files TEXT DEFAULT NULL,
  subject_area VARCHAR(255) NOT NULL,
  paper_type VARCHAR(255) DEFAULT NULL,
  funding_statement TEXT DEFAULT NULL,
  conflict_of_interest TEXT DEFAULT NULL,
  data_availability TEXT DEFAULT NULL,
  ethics_statement TEXT DEFAULT NULL,
  publication_status VARCHAR(255) NOT NULL DEFAULT 'DRAFT',
  screening_status VARCHAR(255) NOT NULL DEFAULT 'NOT_SCREENED',
  primary_institution_id BIGINT DEFAULT NULL,
  created_by BIGINT NOT NULL,
  published_at DATETIME(6) DEFAULT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_paper_profiles_post (post_id),
  KEY idx_paper_profiles_status (publication_status),
  KEY idx_paper_profiles_subject (subject_area),
  KEY idx_paper_profiles_published_at (published_at),
  KEY idx_paper_profiles_primary_institution (primary_institution_id),
  KEY idx_paper_profiles_created_by (created_by),
  CONSTRAINT fk_paper_profiles_post
    FOREIGN KEY (post_id) REFERENCES posts (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_paper_profiles_primary_institution
    FOREIGN KEY (primary_institution_id) REFERENCES institutions (id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_paper_profiles_created_by
    FOREIGN KEY (created_by) REFERENCES users (id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS paper_authors (
  id BIGINT NOT NULL AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  user_id BIGINT DEFAULT NULL,
  expert_profile_id BIGINT DEFAULT NULL,
  display_name VARCHAR(255) NOT NULL,
  email VARCHAR(255) DEFAULT NULL,
  orcid VARCHAR(255) DEFAULT NULL,
  institution_id BIGINT DEFAULT NULL,
  country VARCHAR(255) DEFAULT NULL,
  author_order INT NOT NULL,
  corresponding_author BIT(1) NOT NULL DEFAULT b'0',
  equal_contribution BIT(1) NOT NULL DEFAULT b'0',
  contribution_roles TEXT DEFAULT NULL,
  identity_status VARCHAR(255) NOT NULL DEFAULT 'UNMATCHED',
  PRIMARY KEY (id),
  KEY idx_paper_authors_paper (paper_id),
  KEY idx_paper_authors_name (display_name),
  KEY idx_paper_authors_user (user_id),
  KEY idx_paper_authors_expert_profile (expert_profile_id),
  KEY idx_paper_authors_institution (institution_id),
  CONSTRAINT fk_paper_authors_paper
    FOREIGN KEY (paper_id) REFERENCES paper_profiles (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_paper_authors_user
    FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_paper_authors_expert_profile
    FOREIGN KEY (expert_profile_id) REFERENCES expert_profiles (id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_paper_authors_institution
    FOREIGN KEY (institution_id) REFERENCES institutions (id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS ai_screening_results (
  id BIGINT NOT NULL AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  status VARCHAR(255) NOT NULL,
  risk_level VARCHAR(255) NOT NULL,
  detected_subject_area VARCHAR(255) DEFAULT NULL,
  detected_paper_type VARCHAR(255) DEFAULT NULL,
  summary TEXT DEFAULT NULL,
  issues_json TEXT DEFAULT NULL,
  raw_response_json TEXT DEFAULT NULL,
  screened_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY idx_ai_screening_results_paper (paper_id),
  CONSTRAINT fk_ai_screening_results_paper
    FOREIGN KEY (paper_id) REFERENCES paper_profiles (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS paper_ratings (
  id BIGINT NOT NULL AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  rater_id BIGINT NOT NULL,
  overall_score INT NOT NULL,
  innovation_score INT NOT NULL,
  method_score INT NOT NULL,
  impact_score INT NOT NULL,
  comment TEXT DEFAULT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_paper_ratings_paper_rater (paper_id, rater_id),
  KEY idx_paper_ratings_paper (paper_id),
  KEY idx_paper_ratings_rater (rater_id),
  CONSTRAINT fk_paper_ratings_paper
    FOREIGN KEY (paper_id) REFERENCES paper_profiles (id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_paper_ratings_rater
    FOREIGN KEY (rater_id) REFERENCES users (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS paper_score_snapshots (
  id BIGINT NOT NULL AUTO_INCREMENT,
  paper_id BIGINT NOT NULL,
  rating_count INT NOT NULL DEFAULT 0,
  average_overall_score DOUBLE NOT NULL DEFAULT 0,
  average_innovation_score DOUBLE NOT NULL DEFAULT 0,
  average_method_score DOUBLE NOT NULL DEFAULT 0,
  average_impact_score DOUBLE NOT NULL DEFAULT 0,
  composite_score DOUBLE NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uk_paper_score_snapshots_paper (paper_id),
  KEY idx_paper_score_snapshots_paper (paper_id),
  KEY idx_paper_score_snapshots_composite (composite_score),
  CONSTRAINT fk_paper_score_snapshots_paper
    FOREIGN KEY (paper_id) REFERENCES paper_profiles (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
