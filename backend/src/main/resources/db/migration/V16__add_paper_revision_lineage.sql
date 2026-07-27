ALTER TABLE paper_submission_drafts
  ADD COLUMN revision_source_paper_id BIGINT NULL AFTER submitted_paper_id,
  ADD INDEX idx_paper_submission_drafts_revision_source (revision_source_paper_id),
  ADD CONSTRAINT fk_paper_submission_drafts_revision_source
    FOREIGN KEY (revision_source_paper_id) REFERENCES paper_profiles(id);

ALTER TABLE paper_profiles
  ADD COLUMN revision_of_paper_id BIGINT NULL AFTER created_by,
  ADD COLUMN revision_number INT NOT NULL DEFAULT 1 AFTER revision_of_paper_id,
  ADD INDEX idx_paper_profiles_revision_of (revision_of_paper_id),
  ADD CONSTRAINT fk_paper_profiles_revision_of
    FOREIGN KEY (revision_of_paper_id) REFERENCES paper_profiles(id);
