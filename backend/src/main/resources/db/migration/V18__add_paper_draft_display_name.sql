-- Forward-only Flyway migration. Nullable by design so existing drafts require no backfill.
ALTER TABLE paper_submission_drafts
  ADD COLUMN display_name VARCHAR(160) NULL AFTER manuscript_type;
