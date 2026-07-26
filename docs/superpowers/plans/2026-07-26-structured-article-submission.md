# Structured Article Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an owner-scoped structured article editor to paper submission and publish a complete HTML article containing sections, paragraphs, figures, equations, tables, references, and Supporting Information.

**Architecture:** Store the editable article as one versioned JSON aggregate attached to `PaperSubmissionDraft`, validate it on the server, and copy a sanitized immutable snapshot to `PaperProfile` in the existing final-submission transaction. Render draft preview and public detail from the same Vue article components; retain DOCX as the authoritative source file and use normalized paper files for figures and SI.

**Tech Stack:** Spring Boot 3, Java 17, JPA/Hibernate, Flyway, Jackson, Jsoup, MySQL/H2, Nuxt 4, Vue 3, KaTeX, Docker Compose.

---

## File Map

Backend files:

- Create `backend/src/main/resources/db/migration/V15__add_structured_paper_articles.sql`: versioned draft aggregate and final snapshot columns.
- Create `backend/src/main/java/com/openisle/model/PaperArticleStatus.java`: draft article status enum.
- Create `backend/src/main/java/com/openisle/dto/PaperArticleDto.java`: article aggregate API contract.
- Create `backend/src/main/java/com/openisle/dto/PaperArticleSectionDto.java`: nested section contract.
- Create `backend/src/main/java/com/openisle/dto/PaperArticleBlockDto.java`: typed block contract.
- Create `backend/src/main/java/com/openisle/dto/PaperArticleValidationDto.java`: validation result and issues.
- Create `backend/src/main/java/com/openisle/service/PaperArticleValidator.java`: structural and referenced-file validation.
- Create `backend/src/main/java/com/openisle/service/PaperArticleService.java`: owner-scoped load/save/ready/reopen operations and snapshot finalization.
- Create `backend/src/main/java/com/openisle/controller/PaperArticleController.java`: draft and public article endpoints.
- Modify `backend/src/main/java/com/openisle/model/PaperSubmissionDraft.java`: draft article JSON, status, version, ready timestamp.
- Modify `backend/src/main/java/com/openisle/model/PaperProfile.java`: immutable article JSON snapshot.
- Modify `backend/src/main/java/com/openisle/model/PaperFileRole.java`: add `FIGURE`.
- Modify `backend/src/main/java/com/openisle/service/PaperSubmissionDraftService.java`: require ready article and snapshot it transactionally.
- Modify `backend/src/main/java/com/openisle/service/PaperFilePolicy.java`: figure image policy and public visibility.
- Modify `backend/src/main/java/com/openisle/service/PaperService.java`: expose article snapshot and finalized figure metadata.
- Test `backend/src/test/java/com/openisle/service/PaperArticleValidatorTest.java`.
- Test `backend/src/test/java/com/openisle/service/PaperArticleServiceTest.java`.
- Test `backend/src/test/java/com/openisle/service/PaperSubmissionFinalizationTest.java`.

Frontend files:

- Add dependency `katex` in `frontend_nuxt/package.json` and lockfile.
- Create `frontend_nuxt/config/paperArticleConfig.js`: block types and article factory helpers.
- Create `frontend_nuxt/composables/usePaperArticleDraft.js`: versioned article load/save/ready/reopen state.
- Create `frontend_nuxt/components/paper-article/PaperArticleRenderer.vue`: shared full-text renderer.
- Create `frontend_nuxt/components/paper-article/PaperEquation.vue`: safe KaTeX rendering with error state.
- Create `frontend_nuxt/components/paper-article/PaperFigure.vue`: responsive figure with caption and alt text.
- Create `frontend_nuxt/components/paper-article/PaperTable.vue`: accessible responsive table.
- Create `frontend_nuxt/components/paper-article/ArticleOutline.vue`: section navigation and ordering.
- Create `frontend_nuxt/components/paper-article/ArticleBlockEditor.vue`: typed block editing surface.
- Create `frontend_nuxt/pages/papers/submit/[draftId]/content.vue`: three-pane article editor.
- Create `frontend_nuxt/pages/papers/submit/[draftId]/content/preview.vue`: author preview and readiness gate.
- Modify `frontend_nuxt/composables/paperApi.js`: article API calls.
- Modify `frontend_nuxt/pages/papers/submit.vue`: Article Content section and progress state.
- Modify `frontend_nuxt/pages/papers/submit/[draftId]/review.vue`: structured article summary and preview link.
- Modify `frontend_nuxt/pages/papers/[id]/index.vue`: full article renderer and article outline.

Fixture files:

- Create `backend/src/test/resources/fixtures/paper01-article.json`: representative validated article aggregate.
- Create `scripts/paper01/build-paper01-submission.ps1`: produce import JSON and browser-compatible figure files from the local manuscript source without embedding local paths in application data.
- Create `scripts/paper01/paper01-submission.json`: generated metadata/article payload checked for deterministic demo use.
- Create `scripts/paper01/README.md`: exact local demo steps and source-file mapping.

### Task 1: Database and Contracts

- [ ] Create a failing persistence test that saves draft article JSON/status/version and final article JSON.
- [ ] Run `mvn -Dtest=PaperSubmissionPersistenceTest test` and confirm missing columns/properties fail compilation.
- [ ] Add migration `V15__add_structured_paper_articles.sql` with `article_json LONGTEXT`, `article_status VARCHAR(32) NOT NULL DEFAULT 'NOT_STARTED'`, `article_version BIGINT NOT NULL DEFAULT 0`, `article_ready_at DATETIME`, and `paper_profiles.article_json LONGTEXT`.
- [ ] Add matching entity properties and `PaperArticleStatus`.
- [ ] Add DTOs with `version`, `status`, ordered `sections`, ordered typed `blocks`, and validation issues containing `sectionKey`, `blockKey`, `field`, `code`, and `message`.
- [ ] Re-run the persistence test and commit with `feat: add structured article persistence`.

### Task 2: Article Validation

- [ ] Write failing tests for: empty article, duplicate keys, invalid hierarchy, empty paragraph, invalid equation, missing figure metadata, figure file not uploaded, empty table, and a complete valid article.
- [ ] Run `mvn -Dtest=PaperArticleValidatorTest test` and confirm failures.
- [ ] Implement `PaperArticleValidator` with deterministic issue order and no HTML rendering responsibilities.
- [ ] Resolve figure IDs only from files owned by the same draft, with role `FIGURE` and status `UPLOADED`.
- [ ] Re-run validator tests and commit with `feat: validate structured paper articles`.

### Task 3: Draft Article API

- [ ] Write failing service/controller tests for owner-only GET, optimistic PUT, 409 conflicts, ready validation, reopen, and submitted-draft immutability.
- [ ] Implement `PaperArticleService` methods `getDraftArticle`, `updateDraftArticle`, `validateDraftArticle`, `markReady`, and `reopen`.
- [ ] Implement routes under `/api/paper-submission-drafts/{draftId}/article` and a public `GET /api/papers/{paperId}/article` route governed by `PaperAccessPolicy`.
- [ ] Ensure article edits increment `article_version` and return 409 with the current version for stale writes.
- [ ] Run focused tests and commit with `feat: add structured article draft API`.

### Task 4: Figure Upload Policy

- [ ] Add failing tests showing `FIGURE` accepts PNG/JPEG/WebP, rejects DOCX/PDF/TIFF, caps size at 20 MB, and resolves to public visibility after publication.
- [ ] Add `FIGURE` to `PaperFileRole`, `PaperFilePolicy`, submission file configuration, and file labels.
- [ ] Ensure unreferenced figure files remain draft-only and only finalized referenced figure files are copied to `PaperFile`.
- [ ] Run file policy and finalization tests and commit with `feat: support structured article figures`.

### Task 5: Transactional Finalization

- [ ] Write a failing finalization test that submits a valid draft and asserts identical article structure on `PaperProfile`, finalized figure records, and linked `Post` creation.
- [ ] Add failing rollback assertions for article snapshot failure and missing referenced figure.
- [ ] Require article status `READY` in `PaperSubmissionValidator.validateForSubmission`.
- [ ] Copy the validated JSON snapshot and referenced figures inside `PaperSubmissionDraftService.submitDraft` before marking the draft submitted.
- [ ] Keep `Post.content` as a plain searchable excerpt derived from abstract and article paragraphs, never raw HTML.
- [ ] Run finalization tests and commit with `feat: finalize structured article snapshots`.

### Task 6: Shared Article Renderer

- [ ] Install `katex` and add a focused component test or deterministic renderer test for valid and invalid LaTeX.
- [ ] Implement `PaperEquation.vue` using KaTeX with `throwOnError: false`, `trust: false`, and accessible fallback text.
- [ ] Implement `PaperFigure.vue`, `PaperTable.vue`, and `PaperArticleRenderer.vue` with semantic `article`, `section`, `figure`, `figcaption`, `table`, and heading elements.
- [ ] Render paragraph text as escaped text with constrained inline math; do not use unrestricted `v-html`.
- [ ] Add responsive constraints for images, wide tables, long equations, and headings.
- [ ] Run `npm run build` and commit with `feat: render structured paper articles`.

### Task 7: Article Editor

- [ ] Add `paperApi` calls and implement `usePaperArticleDraft` with 800 ms autosave, dirty state, retryable network errors, and conflict handling consistent with the main draft form.
- [ ] Implement `ArticleOutline.vue` for selection, add, rename, reorder, nesting up to level 3, and guarded deletion.
- [ ] Implement `ArticleBlockEditor.vue` for paragraph, subheading, figure, equation, and table payloads.
- [ ] Build the three-pane `/content` page with stable responsive layouts: desktop panes and mobile tabs.
- [ ] Add keyboard-safe commands, icon tooltips, upload status, and visible save status.
- [ ] Run `npm run build` and commit with `feat: build structured article editor`.

### Task 8: Preview and Submission Integration

- [ ] Build `/content/preview` using the shared renderer plus draft title, authors, affiliations, abstract, keywords, references, and files.
- [ ] Add `Mark Content as Ready`, `Back to Editor`, issue navigation, and reopening behavior.
- [ ] Add `Article Content` to `SUBMISSION_SECTIONS`, the submission page, right progress rail, review page, and final validation messaging.
- [ ] Show counts and status without embedding the editor inside the already long submission form.
- [ ] Run `npm run build` and commit with `feat: integrate article preview with submission`.

### Task 9: Public Paper Detail

- [ ] Fetch the public article snapshot with paper metadata and render it after Abstract and TOC Graphic.
- [ ] Add a sticky article outline on wide screens and a compact contents disclosure on mobile.
- [ ] Keep manuscript download and SI preview as supporting actions, not substitutes for full text.
- [ ] Preserve author information, declarations, rating, comments, following, and admin actions.
- [ ] Verify withdrawn/retracted visibility still flows through `PaperAccessPolicy`.
- [ ] Run backend paper tests and `npm run build`, then commit with `feat: publish complete paper full text`.

### Task 10: Real paper01 Fixture and End-to-End Submission

- [ ] Build a deterministic import payload from `paper_cnn1d_ai.qmd`: metadata, seven authors, affiliations, sections, paragraphs, equations, references, and figure captions.
- [ ] Convert or copy browser-compatible figures 1-8 and `abstract.png` into the fixture staging directory without modifying the source paper project.
- [ ] Document the mapping from source files to manuscript, TOC graphic, figures, and SI.
- [ ] Start the local stack and use an authenticated account to create a fresh draft.
- [ ] Upload `paper_cnn1d_ai.docx`, a generated cover letter, `si.docx`, TOC graphic, and eight figures through the same APIs used by the UI.
- [ ] Save the structured article, mark it ready, complete confirmations, submit, and record the resulting paper ID.
- [ ] Open the public paper page and verify the complete article, all figures, equations, references, SI, and social controls.
- [ ] Commit deterministic fixture tooling and documentation with `feat: add paper01 submission demonstration`.

### Task 11: Full Verification

- [ ] Run backend focused tests for persistence, validation, access, files, and finalization.
- [ ] Run `cd backend && mvn test` and record any unrelated pre-existing failures separately.
- [ ] Run `cd frontend_nuxt && npm run build`.
- [ ] Use browser screenshots at desktop and mobile widths for editor, preview, and published detail.
- [ ] Verify no horizontal overflow, overlapping controls, blank images, broken equations, or stale autosave status.
- [ ] Verify guest public access and owner-only draft access.
- [ ] Commit any verification fixes, update the design/technical docs where contracts changed, and provide the final demo URL.
