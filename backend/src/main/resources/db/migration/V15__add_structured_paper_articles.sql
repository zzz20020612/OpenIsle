ALTER TABLE paper_submission_drafts
  ADD COLUMN article_json LONGTEXT NULL AFTER form_data_json,
  ADD COLUMN article_status VARCHAR(32) NOT NULL DEFAULT 'NOT_STARTED' AFTER article_json,
  ADD COLUMN article_version BIGINT NOT NULL DEFAULT 0 AFTER article_status,
  ADD COLUMN article_ready_at DATETIME NULL AFTER article_version;

ALTER TABLE paper_profiles
  ADD COLUMN article_json LONGTEXT NULL AFTER references_text;
