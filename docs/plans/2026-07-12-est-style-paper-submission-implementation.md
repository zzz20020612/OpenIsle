# EST-Style Paper Submission Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-oriented, EST-inspired OpenIsle submission workflow with durable drafts, structured files/authors/affiliations/funding/declarations, author review, transactional submission, and a formal public paper record with Supporting Information PDF preview.

**Architecture:** Keep OpenIsle's `Post` as the community object and `PaperProfile` as the paper metadata extension. Store incomplete work in owner-scoped `PaperSubmissionDraft` JSON plus normalized draft file rows, then finalize atomically into the existing `Post`/`PaperProfile` path and new normalized author-affiliation, funding, and file tables. The Nuxt frontend uses a dedicated draft composable for autosave and one continuous submission page with a sticky scrollspy; the public paper page consumes only finalized, visibility-filtered DTOs.

**Tech Stack:** Java 17, Spring Boot 3.1, Spring Data JPA, MySQL/H2, Spring Security, OpenAPI, Nuxt 3, Vue 3 Composition API, `@icon-park/vue-next`, Vitest, Vue Test Utils, Playwright, PDF.js (`pdfjs-dist`).

---

## Execution Preconditions

- Work in `D:\OpenIsle` on `feature/est-style-submission-design` or a new `feature/est-style-submission-implementation` branch created from it.
- Preserve all unrelated dirty changes. Before every commit, stage only the files listed by that task.
- The uncommitted database-baseline work currently includes `V12__create_paper_platform_tables.sql` and `V13__backfill_paper_post_type.sql`. Commit or otherwise stabilize that baseline before adding `V14`; never renumber a migration that has run in any shared database.
- Use `@openisle-paper-platform` throughout, `@superpowers:test-driven-development` for each behavior change, `@impeccable-ui-design` for Tasks 9-13, and `@superpowers:verification-before-completion` for Task 14.
- All product UI copy remains English. User-facing implementation discussion may remain Chinese.

### Task 1: Align Submission Rules Before Code

**Files:**
- Modify: `docs/paper-platform-business-rules.md`
- Modify: `docs/paper-platform-technical-plan.md`
- Modify: `docs/openisle-core-reuse-audit.md`
- Reference: `docs/plans/2026-07-12-est-style-paper-submission-design.md`

**Step 1: Add the new business invariants**

Update the submission section so it explicitly states:

```markdown
- Partial submission data lives in `PaperSubmissionDraft`; it does not create `Post` or `PaperProfile` rows.
- A final submission requires exactly one corresponding author.
- Every author requires email, given name, family name, author role, at least one affiliation, and exactly one primary affiliation.
- Required files are one DOCX manuscript, one cover letter, and one TOC graphic.
- Cover letters, review-only files, private comments, non-corresponding emails, and detailed addresses are never public.
- Final submission is idempotent and creates the `Post`, paper metadata, authors, affiliations, funding, files, and screening state in one transaction.
```

Replace the old “one or more corresponding authors” rule and the old `DRAFT` description that implies incomplete `PaperProfile` records.

**Step 2: Record the reuse boundary**

Document that finalization still uses:

```text
Post -> comments, reactions, subscriptions, notifications, moderation
PaperProfile -> formal paper metadata and publication state
PaperSubmissionDraft -> incomplete private form state only
```

State that browser draft endpoints are intentionally not exposed as MCP tools because they are interactive, owner-scoped workflows; finalized paper APIs remain the future MCP integration boundary.

**Step 3: Review the diff for contradictions**

Run: `git diff -- docs/paper-platform-business-rules.md docs/paper-platform-technical-plan.md docs/openisle-core-reuse-audit.md`

Expected: no remaining rule permits multiple corresponding authors or incomplete public paper records.

**Step 4: Commit**

```bash
git add docs/paper-platform-business-rules.md docs/paper-platform-technical-plan.md docs/openisle-core-reuse-audit.md
git commit -m "docs: align EST-style submission rules"
```

### Task 2: Add the Versioned Submission Schema

**Files:**
- Create: `backend/src/main/resources/db/migration/V14__add_est_submission_workflow.sql`
- Create: `backend/src/main/java/com/openisle/model/PaperSubmissionDraftStatus.java`
- Create: `backend/src/main/java/com/openisle/model/PaperFileRole.java`
- Create: `backend/src/main/java/com/openisle/model/PaperFileVisibility.java`
- Create: `backend/src/main/java/com/openisle/model/PaperUploadStatus.java`
- Create: `backend/src/main/java/com/openisle/model/PaperSubmissionDraft.java`
- Create: `backend/src/main/java/com/openisle/model/PaperSubmissionFile.java`
- Create: `backend/src/main/java/com/openisle/model/PaperFile.java`
- Create: `backend/src/main/java/com/openisle/model/PaperAuthorAffiliation.java`
- Create: `backend/src/main/java/com/openisle/model/PaperFundingRecord.java`
- Modify: `backend/src/main/java/com/openisle/model/PaperProfile.java`
- Modify: `backend/src/main/java/com/openisle/model/PaperAuthor.java`
- Create: `backend/src/main/java/com/openisle/repository/PaperSubmissionDraftRepository.java`
- Create: `backend/src/main/java/com/openisle/repository/PaperSubmissionFileRepository.java`
- Create: `backend/src/main/java/com/openisle/repository/PaperFileRepository.java`
- Create: `backend/src/main/java/com/openisle/repository/PaperAuthorAffiliationRepository.java`
- Create: `backend/src/main/java/com/openisle/repository/PaperFundingRecordRepository.java`
- Test: `backend/src/test/java/com/openisle/repository/PaperSubmissionPersistenceTest.java`

**Step 1: Write the failing persistence test**

Use `@DataJpaTest` to save one user-owned draft and one finalized paper author with two affiliations. Assert optimistic versioning and ordered relationships:

```java
@DataJpaTest
class PaperSubmissionPersistenceTest {
  @Test
  void persistsDraftVersionAndMultipleAuthorAffiliations() {
    PaperSubmissionDraft draft = new PaperSubmissionDraft();
    draft.setCreatedBy(user);
    draft.setStatus(PaperSubmissionDraftStatus.IN_PROGRESS);
    draft.setFormDataJson("{}");
    draft = draftRepository.saveAndFlush(draft);

    assertEquals(0L, draft.getVersion());
    assertEquals(2, affiliationRepository.findByPaperAuthorIdOrderByDisplayOrderAsc(author.getId()).size());
  }
}
```

**Step 2: Run the test to verify it fails**

Run: `cd backend && mvn -Dtest=PaperSubmissionPersistenceTest test`

Expected: FAIL because the entities and repositories do not exist.

**Step 3: Add enums and entity relationships**

Use these stable enum values:

```java
public enum PaperSubmissionDraftStatus { IN_PROGRESS, SUBMITTED, ABANDONED }

public enum PaperFileRole {
  MANUSCRIPT, COVER_LETTER, TOC_GRAPHIC, SUPPORTING_INFORMATION,
  REVIEW_ONLY, PDF_VERSION, LATEX_SOURCE, DATASET, CODE, OTHER
}

public enum PaperFileVisibility { PUBLIC, PRIVATE }
public enum PaperUploadStatus { PENDING, UPLOADED, FAILED }
```

The draft entity must contain `createdBy`, `manuscriptType`, `formDataJson` as `LONGTEXT`, `currentSection`, `status`, `submittedPaper`, `idempotencyKey`, `@Version long version`, and timestamps.

The author-affiliation entity must contain `paperAuthor`, `institution`, snapshot fields (`organizationName`, `department`, `addressLine1`, `addressLine2`, `country`, `region`, `city`, `postalCode`), `primaryAffiliation`, and `displayOrder`.

Retain `PaperAuthor.institution` as a compatibility pointer to the primary affiliation. Add `givenName`, `middleName`, `familyName`, and `authorRole`. Retain the existing `displayName` field.

Add these fields to `PaperProfile`:

```java
private String preprintStatement;
private String aiUseDisclosure;
private String privateComments;
private boolean allAuthorsConsent;
private boolean originalityConfirmed;
private boolean rightsConfirmed;
```

**Step 4: Write the SQL migration**

Create tables for drafts, draft files, final files, author affiliations, and funding records. Add compatible nullable columns to `paper_authors` and declaration columns to `paper_profiles`. Include indexes for owner/status, draft/file order, paper/file role, paper/author order, and paper/funding order. Add foreign keys with `ON DELETE CASCADE` for owned child rows and `SET NULL` only where audit history must survive.

Do not drop the legacy `institution_id`, `manuscript_files`, or `supplementary_files` columns in this migration.

**Step 5: Run the persistence test**

Run: `cd backend && mvn -Dtest=PaperSubmissionPersistenceTest test`

Expected: PASS.

**Step 6: Commit**

```bash
git add backend/src/main/resources/db/migration/V14__add_est_submission_workflow.sql backend/src/main/java/com/openisle/model backend/src/main/java/com/openisle/repository backend/src/test/java/com/openisle/repository/PaperSubmissionPersistenceTest.java
git commit -m "feat: add paper submission schema"
```

### Task 3: Define Typed Draft Contracts and Validation

**Files:**
- Modify: `backend/src/main/java/com/openisle/dto/PaperSubmitRequest.java`
- Modify: `backend/src/main/java/com/openisle/dto/PaperAuthorRequest.java`
- Modify: `backend/src/main/java/com/openisle/dto/PaperFileRecordDto.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperAffiliationRequest.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperFundingRequest.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionDraftDto.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionDraftPatchRequest.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionFileDto.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionFilePresignRequest.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionFilePresignResponse.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionFileUpdateRequest.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionIssueDto.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionValidationDto.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionSubmitRequest.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperSubmissionResultDto.java`
- Create: `backend/src/main/java/com/openisle/service/PaperSubmissionValidator.java`
- Test: `backend/src/test/java/com/openisle/service/PaperSubmissionValidatorTest.java`

**Step 1: Write failing validation tests**

Cover at least these cases:

```java
@Test void requiresExactlyOneCorrespondingAuthor() { ... }
@Test void requiresExactlyOnePrimaryAffiliationPerAuthor() { ... }
@Test void requiresDocxCoverLetterAndTocGraphic() { ... }
@Test void requiresDescriptionForPublicSupportingInformation() { ... }
@Test void acceptsOneKeywordAndNoFundingDeclaration() { ... }
@Test void rejectsASecondCorrespondingAuthor() { ... }
```

Assert stable section keys such as `file-upload`, `manuscript-information`, `author-information`, `funding-information`, and `details-comments`.

**Step 2: Run the tests to verify they fail**

Run: `cd backend && mvn -Dtest=PaperSubmissionValidatorTest test`

Expected: FAIL because the validator and DTOs do not exist.

**Step 3: Extend the request model compatibly**

Keep existing fields and add structured fields. `PaperAuthorRequest` should use:

```java
private String givenName;
private String middleName;
private String familyName;
private String authorRole;
private List<PaperAffiliationRequest> affiliations;
```

`PaperSubmitRequest` should add:

```java
private List<PaperFundingRequest> funding;
private Boolean noFundingReceived;
private String preprintStatement;
private String aiUseDisclosure;
private Boolean allAuthorsConsent;
private Boolean originalityConfirmed;
private Boolean rightsConfirmed;
private String privateComments;
```

The draft patch contains `version`, `currentSection`, and the complete typed `PaperSubmitRequest formData`. Partial drafts are allowed; only validation/submission applies final rules.

**Step 4: Implement one authoritative validator**

Return all issues instead of throwing on the first field:

```java
public PaperSubmissionValidationDto validate(
  PaperSubmitRequest form,
  List<PaperSubmissionFile> files,
  boolean requireFinalConfirmations
) {
  List<PaperSubmissionIssueDto> issues = new ArrayList<>();
  // Add deterministic issues in visible section order.
  return new PaperSubmissionValidationDto(issues.isEmpty(), issues);
}
```

Enforce Research Article/Review, title, abstract, subject, at least one keyword, at least one author, exactly one corresponding author, required identity/affiliation fields, co-first continuity, funding-or-no-funding, required declarations, required files, file role/visibility rules, and final review confirmations.

**Step 5: Run the tests**

Run: `cd backend && mvn -Dtest=PaperSubmissionValidatorTest test`

Expected: PASS.

**Step 6: Commit**

```bash
git add backend/src/main/java/com/openisle/dto backend/src/main/java/com/openisle/service/PaperSubmissionValidator.java backend/src/test/java/com/openisle/service/PaperSubmissionValidatorTest.java
git commit -m "feat: validate structured paper submissions"
```

### Task 4: Implement Owner-Scoped Draft CRUD and Optimistic Autosave

**Files:**
- Create: `backend/src/main/java/com/openisle/exception/DraftVersionConflictException.java`
- Modify: `backend/src/main/java/com/openisle/controller/GlobalExceptionHandler.java`
- Create: `backend/src/main/java/com/openisle/service/PaperSubmissionDraftService.java`
- Create: `backend/src/main/java/com/openisle/controller/PaperSubmissionDraftController.java`
- Test: `backend/src/test/java/com/openisle/service/PaperSubmissionDraftServiceTest.java`
- Test: `backend/src/test/java/com/openisle/controller/PaperSubmissionDraftControllerTest.java`

**Step 1: Write failing ownership and version tests**

Cover create, latest active draft, owner read, non-owner denial, patch, discard, and stale version conflict:

```java
assertThrows(DraftVersionConflictException.class,
  () -> service.updateDraft("alice", draftId, stalePatch));
```

Controller tests must assert `409 Conflict` returns:

```json
{
  "error": "Draft was updated in another session",
  "currentVersion": 3
}
```

**Step 2: Run the tests to verify they fail**

Run: `cd backend && mvn -Dtest=PaperSubmissionDraftServiceTest,PaperSubmissionDraftControllerTest test`

Expected: FAIL because the service/controller do not exist.

**Step 3: Implement the draft service**

Expose:

```java
createDraft(username)
getCurrentDraft(username)
getDraft(username, draftId)
updateDraft(username, draftId, patch)
discardDraft(username, draftId)
validateDraft(username, draftId)
```

Serialize form data with the injected Spring `ObjectMapper`, not a new static mapper. On create, store an empty form with `paperType = "Research Article"`. Never create a `Post` or `PaperProfile` here.

**Step 4: Implement REST endpoints**

```text
POST   /api/paper-submission-drafts
GET    /api/paper-submission-drafts/current
GET    /api/paper-submission-drafts/{draftId}
PATCH  /api/paper-submission-drafts/{draftId}
DELETE /api/paper-submission-drafts/{draftId}
POST   /api/paper-submission-drafts/{draftId}/validate
```

Default Spring Security authentication is sufficient because these paths are not in the public allowlist. Add `@Tag`, `@Operation`, and explicit 401/403/409 response documentation.

**Step 5: Run the tests**

Run: `cd backend && mvn -Dtest=PaperSubmissionDraftServiceTest,PaperSubmissionDraftControllerTest test`

Expected: PASS.

**Step 6: Commit**

```bash
git add backend/src/main/java/com/openisle/exception/DraftVersionConflictException.java backend/src/main/java/com/openisle/controller/GlobalExceptionHandler.java backend/src/main/java/com/openisle/service/PaperSubmissionDraftService.java backend/src/main/java/com/openisle/controller/PaperSubmissionDraftController.java backend/src/test/java/com/openisle/service/PaperSubmissionDraftServiceTest.java backend/src/test/java/com/openisle/controller/PaperSubmissionDraftControllerTest.java
git commit -m "feat: add autosaved paper submission drafts"
```

### Task 5: Add Draft-Scoped Upload Roles and Signed File Access

**Files:**
- Create: `backend/src/main/java/com/openisle/service/PaperFilePolicy.java`
- Create: `backend/src/main/java/com/openisle/service/PresignedFileStorageService.java`
- Create: `backend/src/main/java/com/openisle/service/PaperSubmissionFileService.java`
- Modify: `backend/src/main/java/com/openisle/service/ImageUploader.java`
- Modify: `backend/src/main/java/com/openisle/service/CosImageUploader.java`
- Modify: `backend/src/main/java/com/openisle/service/LocalPresignedUploadService.java`
- Modify: `backend/src/main/java/com/openisle/controller/UploadController.java`
- Modify: `backend/src/main/java/com/openisle/controller/PaperSubmissionDraftController.java`
- Test: `backend/src/test/java/com/openisle/service/PaperFilePolicyTest.java`
- Test: `backend/src/test/java/com/openisle/service/PaperSubmissionFileServiceTest.java`
- Test: `backend/src/test/java/com/openisle/service/LocalPresignedUploadServiceTest.java`

**Step 1: Write failing file policy tests**

Assert:

- manuscript accepts one `.docx` only;
- cover letter accepts `.doc`, `.docx`, `.pdf`, `.rtf`, `.txt` and is always private;
- TOC graphic accepts safe raster web images and is public;
- PDF Version accepts `.pdf`;
- Review Only is always private;
- public Supporting Information requires a description before validation;
- oversized or disallowed extensions are rejected before presigning.

**Step 2: Run the tests to verify they fail**

Run: `cd backend && mvn -Dtest=PaperFilePolicyTest,PaperSubmissionFileServiceTest,LocalPresignedUploadServiceTest test`

Expected: FAIL for missing policy and file service behavior.

**Step 3: Centralize role policy**

Derive storage purpose, allowed extension, maximum size, and forced visibility from `PaperFileRole`; never trust a client-provided storage purpose. Use stable limits such as 50 MB manuscript, 20 MB cover letter, 10 MB TOC graphic, and 100 MB optional files.

**Step 4: Extend the existing upload infrastructure**

`PresignedFileStorageService` must delegate to the existing `ImageUploader`/COS path and fall back to `LocalPresignedUploadService`. Add short-lived signed download support:

```java
String presignDownload(String key, String filename, boolean inline);
```

For COS, generate a GET presigned URL. For local development, create a one-time expiring token and serve it from `GET /api/upload/local/download/{token}`. Do not expose raw private storage URLs in draft or paper DTOs.

**Step 5: Implement file endpoints**

```text
POST   /api/paper-submission-drafts/{draftId}/files/presign
PATCH  /api/paper-submission-drafts/{draftId}/files/{fileId}
DELETE /api/paper-submission-drafts/{draftId}/files/{fileId}
GET    /api/paper-submission-drafts/{draftId}/files/{fileId}/content
```

The presign call creates a `PENDING` row and returns `fileId`, `uploadUrl`, and required upload headers. The PATCH marks the file `UPLOADED` and updates role, description, display name, visibility, and order. Every operation verifies draft ownership.

**Step 6: Run the tests**

Run: `cd backend && mvn -Dtest=PaperFilePolicyTest,PaperSubmissionFileServiceTest,LocalPresignedUploadServiceTest test`

Expected: PASS.

**Step 7: Commit**

```bash
git add backend/src/main/java/com/openisle/service/PaperFilePolicy.java backend/src/main/java/com/openisle/service/PresignedFileStorageService.java backend/src/main/java/com/openisle/service/PaperSubmissionFileService.java backend/src/main/java/com/openisle/service/ImageUploader.java backend/src/main/java/com/openisle/service/CosImageUploader.java backend/src/main/java/com/openisle/service/LocalPresignedUploadService.java backend/src/main/java/com/openisle/controller/UploadController.java backend/src/main/java/com/openisle/controller/PaperSubmissionDraftController.java backend/src/test/java/com/openisle/service
git commit -m "feat: add secure submission file uploads"
```

### Task 6: Finalize Drafts Through the Existing Paper Community Core

**Files:**
- Modify: `backend/src/main/java/com/openisle/service/PaperService.java`
- Modify: `backend/src/main/java/com/openisle/service/PaperSubmissionDraftService.java`
- Modify: `backend/src/main/java/com/openisle/controller/PaperSubmissionDraftController.java`
- Modify: `backend/src/main/java/com/openisle/repository/PaperSubmissionDraftRepository.java`
- Modify: `backend/src/main/java/com/openisle/repository/InstitutionRepository.java`
- Modify: `backend/src/main/java/com/openisle/repository/PaperAuthorRepository.java`
- Test: `backend/src/test/java/com/openisle/service/PaperServiceTest.java`
- Test: `backend/src/test/java/com/openisle/service/PaperSubmissionFinalizationTest.java`

**Step 1: Write failing finalization tests**

Cover:

```text
valid draft -> one Post(PAPER) -> one PaperProfile -> ordered authors
-> multiple affiliations -> funding rows -> normalized files -> AI screening
```

Also assert:

- exactly one corresponding author;
- `PaperProfile.primaryInstitution` comes from the first author's primary affiliation;
- `Post.content` uses the abstract when no parsed manuscript body exists;
- expert matching still runs for every author;
- submitting the same draft twice returns the same paper id;
- concurrent submit locks the draft and creates only one paper;
- failed screening leaves the finalized paper in `SCREENING` rather than creating a duplicate.

**Step 2: Run the tests to verify they fail**

Run: `cd backend && mvn -Dtest=PaperSubmissionFinalizationTest,PaperServiceTest test`

Expected: FAIL because finalization does not consume the structured draft model.

**Step 3: Extend `PaperService.submitPaper` without breaking legacy callers**

Use structured request data when present and fall back to legacy `displayName`/`institutionName` values. During finalization:

1. Create `Post` with `PostType.PAPER` and abstract-backed content.
2. Create `PaperProfile` in `SCREENING`.
3. Save ordered authors and compute `displayName` from given/middle/family names.
4. Save all affiliation snapshots and set the legacy institution pointer to the primary affiliation.
5. Create or match `ExpertProfile` as the current code does.
6. Save funding rows and generate the compatibility `fundingStatement`.
7. Copy uploaded draft file metadata into `PaperFile` rows; keep legacy file JSON populated during the transition.
8. Save declarations, with private comments never mapped to public DTOs.
9. Run existing AI screening and preserve current publication behavior.

**Step 4: Add idempotent draft submission**

Use a repository method with `PESSIMISTIC_WRITE` for submit. If status is already `SUBMITTED`, return the existing paper result. Otherwise validate, call `PaperService.submitPaper`, store `submittedPaper`, `idempotencyKey`, and `SUBMITTED` in the same transaction.

Expose:

```text
POST /api/paper-submission-drafts/{draftId}/submit
```

Return `paperId`, `postId`, `publicationStatus`, and `screeningStatus`.

**Step 5: Run the tests**

Run: `cd backend && mvn -Dtest=PaperSubmissionFinalizationTest,PaperServiceTest test`

Expected: PASS.

**Step 6: Commit**

```bash
git add backend/src/main/java/com/openisle/service/PaperService.java backend/src/main/java/com/openisle/service/PaperSubmissionDraftService.java backend/src/main/java/com/openisle/controller/PaperSubmissionDraftController.java backend/src/main/java/com/openisle/repository backend/src/test/java/com/openisle/service/PaperSubmissionFinalizationTest.java backend/src/test/java/com/openisle/service/PaperServiceTest.java
git commit -m "feat: finalize submission drafts atomically"
```

### Task 7: Expose Structured Public Paper Metadata and Protected File Content

**Files:**
- Modify: `backend/src/main/java/com/openisle/dto/PaperAuthorDto.java`
- Modify: `backend/src/main/java/com/openisle/dto/PaperDetailDto.java`
- Modify: `backend/src/main/java/com/openisle/dto/PaperFileRecordDto.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperAffiliationDto.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperFundingDto.java`
- Create: `backend/src/main/java/com/openisle/service/PaperFileAccessService.java`
- Modify: `backend/src/main/java/com/openisle/service/PaperService.java`
- Modify: `backend/src/main/java/com/openisle/controller/PaperController.java`
- Test: `backend/src/test/java/com/openisle/service/PaperFileAccessServiceTest.java`
- Test: `backend/src/test/java/com/openisle/service/PaperServiceTest.java`

**Step 1: Write failing visibility tests**

Assert a guest can see only public files and public declarations for a `PUBLISHED` paper. Assert cover letter, review-only file, private comments, non-corresponding author emails, and address lines never appear in the public DTO. Assert draft owner/admin can access private file content only through the permission-checked endpoint.

**Step 2: Run the tests to verify they fail**

Run: `cd backend && mvn -Dtest=PaperFileAccessServiceTest,PaperServiceTest test`

Expected: FAIL because public mapping still returns opaque legacy file records and single affiliations.

**Step 3: Extend public DTO mapping**

Return ordered author affiliations, funding rows, preprint statement, AI use disclosure, final file metadata, TOC graphic identification, and SI metrics. `PaperFileRecordDto` should expose `id`, display name, role, description, MIME type, size, visibility only when authorized, previewable flag, view count, and download count. Do not expose storage keys.

Only the corresponding author email is public. Keep the legacy fields as fallback for old records without normalized rows.

**Step 4: Add content access endpoint**

```text
GET /api/papers/{paperId}/files/{fileId}/content?mode=preview|download
```

For public files, allow guests only when the paper is `PUBLISHED`. For private files, require submitter/linked author/admin permission. Increment view/download counters with repository update queries, then redirect to a short-lived signed storage URL.

**Step 5: Run the tests**

Run: `cd backend && mvn -Dtest=PaperFileAccessServiceTest,PaperServiceTest test`

Expected: PASS.

**Step 6: Commit**

```bash
git add backend/src/main/java/com/openisle/dto backend/src/main/java/com/openisle/service/PaperFileAccessService.java backend/src/main/java/com/openisle/service/PaperService.java backend/src/main/java/com/openisle/controller/PaperController.java backend/src/test/java/com/openisle/service/PaperFileAccessServiceTest.java backend/src/test/java/com/openisle/service/PaperServiceTest.java
git commit -m "feat: expose structured paper records"
```

### Task 8: Add Frontend Test Infrastructure and Submission Constants

**Files:**
- Modify: `frontend_nuxt/package.json`
- Modify: `frontend_nuxt/package-lock.json`
- Create: `frontend_nuxt/vitest.config.js`
- Create: `frontend_nuxt/playwright.config.js`
- Create: `frontend_nuxt/tests/setup.js`
- Create: `frontend_nuxt/config/paperSubmissionConfig.js`

**Step 1: Add test scripts and dependencies**

Add:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "latest",
    "@vue/test-utils": "latest",
    "happy-dom": "latest",
    "vitest": "latest"
  }
}
```

Add `pdfjs-dist` to dependencies. Run `npm install` so the lockfile is authoritative.

**Step 2: Add stable submission constants**

Export section ids, manuscript types, file roles, CRediT roles, allowed extensions, and save-status labels from `paperSubmissionConfig.js`. Keep all displayed labels in English and API values identical to backend enums.

**Step 3: Verify the test runner starts**

Run: `cd frontend_nuxt && npm test -- --passWithNoTests`

Expected: PASS with no tests collected.

**Step 4: Commit**

```bash
git add frontend_nuxt/package.json frontend_nuxt/package-lock.json frontend_nuxt/vitest.config.js frontend_nuxt/playwright.config.js frontend_nuxt/tests/setup.js frontend_nuxt/config/paperSubmissionConfig.js
git commit -m "test: add submission frontend test setup"
```

### Task 9: Implement the Draft API Composable and Scrollspy State

**Files:**
- Modify: `frontend_nuxt/composables/paperApi.js`
- Create: `frontend_nuxt/composables/usePaperSubmissionDraft.js`
- Create: `frontend_nuxt/composables/useSubmissionScrollspy.js`
- Test: `frontend_nuxt/tests/composables/usePaperSubmissionDraft.test.js`
- Test: `frontend_nuxt/tests/composables/useSubmissionScrollspy.test.js`

**Step 1: Write failing composable tests**

Use mocked API methods and fake timers to assert:

- opening without a draft id restores the current active draft or creates one;
- a deep form change saves once after 800 ms;
- save state moves `Saving...` -> `All changes saved`;
- a 409 leaves local edits intact and shows `Changes not saved` plus conflict state;
- file uploads do not trigger a duplicate form save;
- section completion/error state is derived from backend validation issues;
- the scrollspy uses one stable active section and supports smooth click navigation.

**Step 2: Run the tests to verify they fail**

Run: `cd frontend_nuxt && npm test -- tests/composables/usePaperSubmissionDraft.test.js tests/composables/useSubmissionScrollspy.test.js`

Expected: FAIL because the composables do not exist.

**Step 3: Extend `usePaperApi`**

Add methods for every draft CRUD, validate, submit, and file endpoint. Continue using `authHeaders()` and the existing runtime API base URL.

**Step 4: Implement autosave**

The composable owns `draft`, `form`, `files`, `saveState`, `uploadState`, `validation`, `conflict`, and methods for load/create/save/flush/discard/upload/update/remove/validate/submit. Register `beforeunload` only on the client when edits are unsaved or uploads are active. Stop watchers on component unmount.

**Step 5: Implement scrollspy**

Use `IntersectionObserver` with a stable top root margin beneath the app header. Respect `prefers-reduced-motion` when clicking a section node.

**Step 6: Run the tests**

Run: `cd frontend_nuxt && npm test -- tests/composables/usePaperSubmissionDraft.test.js tests/composables/useSubmissionScrollspy.test.js`

Expected: PASS.

**Step 7: Commit**

```bash
git add frontend_nuxt/composables/paperApi.js frontend_nuxt/composables/usePaperSubmissionDraft.js frontend_nuxt/composables/useSubmissionScrollspy.js frontend_nuxt/tests/composables
git commit -m "feat: add paper submission autosave state"
```

### Task 10: Build Reusable Submission Controls

**Files:**
- Create: `frontend_nuxt/components/PaperSubmissionScrollspy.vue`
- Create: `frontend_nuxt/components/PaperSubmissionSaveStatus.vue`
- Create: `frontend_nuxt/components/PaperSubmissionFileUploader.vue`
- Create: `frontend_nuxt/components/PaperAuthorEditor.vue`
- Create: `frontend_nuxt/components/PaperAffiliationDialog.vue`
- Create: `frontend_nuxt/components/PaperFundingEditor.vue`
- Create: `frontend_nuxt/assets/paper-submission.css`
- Test: `frontend_nuxt/tests/components/PaperSubmissionFileUploader.test.js`
- Test: `frontend_nuxt/tests/components/PaperAuthorEditor.test.js`
- Test: `frontend_nuxt/tests/components/PaperSubmissionScrollspy.test.js`

**Step 1: Write failing component tests**

Cover:

- scrollspy completed/active/error labels and click events;
- required file slots and independent retry state;
- one corresponding author at a time;
- `Add Me as Author` pre-fills current user email/name but remains editable;
- add/remove/reorder authors;
- each author can add multiple affiliations and exactly one primary affiliation;
- long author names and institutions do not clip action buttons.

**Step 2: Run the tests to verify they fail**

Run: `cd frontend_nuxt && npm test -- tests/components/PaperSubmissionFileUploader.test.js tests/components/PaperAuthorEditor.test.js tests/components/PaperSubmissionScrollspy.test.js`

Expected: FAIL because the components do not exist.

**Step 3: Implement the file control**

Use three visible required upload rows (Manuscript File, Cover Letter, TOC Graphic) and one Other Files row. After optional upload, require designation, display name, description where applicable, visibility, and retry/remove controls. Use icon buttons from `@icon-park/vue-next` with `title`/accessible labels.

**Step 4: Implement author and affiliation controls**

Match the confirmed EST behavior: compact ordered author rows, expandable editor, `Author` and `Corresponding Author` check controls, required email/given/family names, optional middle name/ORCID/co-first/CRediT, and an affiliation dialog with organization/country/city required. Selecting a new corresponding author clears the old one immediately.

**Step 5: Implement visual rules**

Use a quiet light-gray workspace, white sections, visible borders, no nested cards, radius no greater than 8 px, stable action-column widths, 44 px minimum interactive targets on mobile, visible focus rings, and a mobile sticky progress control that does not cover fields or the final action bar.

**Step 6: Run the tests**

Run: `cd frontend_nuxt && npm test -- tests/components/PaperSubmissionFileUploader.test.js tests/components/PaperAuthorEditor.test.js tests/components/PaperSubmissionScrollspy.test.js`

Expected: PASS.

**Step 7: Commit**

```bash
git add frontend_nuxt/components/PaperSubmissionScrollspy.vue frontend_nuxt/components/PaperSubmissionSaveStatus.vue frontend_nuxt/components/PaperSubmissionFileUploader.vue frontend_nuxt/components/PaperAuthorEditor.vue frontend_nuxt/components/PaperAffiliationDialog.vue frontend_nuxt/components/PaperFundingEditor.vue frontend_nuxt/assets/paper-submission.css frontend_nuxt/tests/components
git commit -m "feat: add EST-style submission controls"
```

### Task 11: Replace the Wizard with the Continuous Submission Workspace

**Files:**
- Replace: `frontend_nuxt/pages/papers/submit.vue`
- Modify: `frontend_nuxt/assets/paper-submission.css`
- Test: `frontend_nuxt/tests/pages/paper-submit.test.js`
- Test: `frontend_nuxt/tests/e2e/paper-submission-workspace.spec.js`

**Step 1: Write the failing page test**

Assert all six sections render together in this order:

```text
Manuscript Type
File Upload
Manuscript Information
Author Information
Funding Information
Details & Comments
```

Assert there is no Reviewer Suggestions, Editor Preferences, Special Issue Selection, or Manuscript Text field. Assert the primary action is `Continue to Review`.

**Step 2: Run the test to verify it fails**

Run: `cd frontend_nuxt && npm test -- tests/pages/paper-submit.test.js`

Expected: FAIL because the current route is a six-step OJS-style wizard.

**Step 3: Implement the continuous page**

Keep `definePageMeta({ middleware: 'auth-client' })`. Load or create a draft, update the URL with `?draft=<id>`, and connect every control to the draft composable. Include live abstract word count, keyword chips with minimum one and 3-5 recommendation, subject-area select/custom option, funding/no-funding switch, all declarations, private comments, save status, conflict banner, and sticky section navigation.

Do not add visible product-tour text or implementation explanations. Field guidance should be brief and task-specific.

**Step 4: Implement `Continue to Review` behavior**

Flush autosave, call server validation, show all errors in the right rail, scroll to the first invalid section, focus the first invalid field, or navigate to `/papers/submit/{draftId}/review` when valid.

**Step 5: Add Playwright workspace coverage**

Mock authenticated API responses and verify at 1440x1000, 1024x768, and 390x844:

- no horizontal overflow;
- sticky navigation does not overlap the form;
- long names remain readable;
- upload rows keep stable height;
- scroll updates the active node;
- refresh restores draft data.

**Step 6: Run tests and build**

Run: `cd frontend_nuxt && npm test -- tests/pages/paper-submit.test.js`

Run: `cd frontend_nuxt && npm run build`

Expected: PASS and successful Nuxt build.

**Step 7: Commit**

```bash
git add frontend_nuxt/pages/papers/submit.vue frontend_nuxt/assets/paper-submission.css frontend_nuxt/tests/pages/paper-submit.test.js frontend_nuxt/tests/e2e/paper-submission-workspace.spec.js
git commit -m "feat: replace paper submission wizard"
```

### Task 12: Add the Author Review and Confirm Submission Page

**Files:**
- Create: `frontend_nuxt/pages/papers/submit/[draftId]/review.vue`
- Create: `frontend_nuxt/components/PaperSubmissionReviewSection.vue`
- Modify: `frontend_nuxt/assets/paper-submission.css`
- Test: `frontend_nuxt/tests/pages/paper-submission-review.test.js`
- Modify: `frontend_nuxt/tests/e2e/paper-submission-workspace.spec.js`

**Step 1: Write the failing review-page test**

Assert the page renders files, metadata, ordered authors and numbered affiliations, funding, declarations, private comments, validation summary, section-specific Edit links, and disabled final submission until all final confirmations are checked.

**Step 2: Run the test to verify it fails**

Run: `cd frontend_nuxt && npm test -- tests/pages/paper-submission-review.test.js`

Expected: FAIL because the review route does not exist.

**Step 3: Implement read-only review**

Load the owner draft by route id. Re-run server validation. Edit links return to `/papers/submit?draft=<id>#<section-id>`. Use the same section order and sticky navigation as the form, but render semantic definition lists and tables rather than disabled inputs.

**Step 4: Implement final confirmation**

Require confirmations that metadata matches the manuscript, all authors agreed, corresponding-author information is correct, and public files/declarations may be displayed. Generate one idempotency key per draft in session state and call submit once.

If the result is `PUBLISHED`, navigate to `/papers/{paperId}`. Otherwise keep the user on the review page and show a submitted screening-status panel with the returned status; do not navigate to a public detail route that would return 404.

**Step 5: Complete the E2E flow**

Test form -> review -> Edit exact section -> review -> confirm -> published detail. Also test double-click submit sends one request and a server validation error returns to the correct section.

**Step 6: Run tests and build**

Run: `cd frontend_nuxt && npm test -- tests/pages/paper-submission-review.test.js`

Run: `cd frontend_nuxt && npm run build`

Expected: PASS and successful build.

**Step 7: Commit**

```bash
git add frontend_nuxt/pages/papers/submit frontend_nuxt/components/PaperSubmissionReviewSection.vue frontend_nuxt/assets/paper-submission.css frontend_nuxt/tests/pages/paper-submission-review.test.js frontend_nuxt/tests/e2e/paper-submission-workspace.spec.js
git commit -m "feat: add author submission review"
```

### Task 13: Rebuild the Public Paper Record and SI PDF Viewer

**Files:**
- Modify: `frontend_nuxt/pages/papers/[id]/index.vue`
- Create: `frontend_nuxt/components/PaperArticleHeader.vue`
- Create: `frontend_nuxt/components/PaperArticleMetadata.vue`
- Create: `frontend_nuxt/components/SupportingInformationViewer.vue`
- Create: `frontend_nuxt/assets/paper-article.css`
- Test: `frontend_nuxt/tests/components/SupportingInformationViewer.test.js`
- Test: `frontend_nuxt/tests/pages/paper-detail.test.js`
- Create: `frontend_nuxt/tests/e2e/paper-detail-record.spec.js`

**Step 1: Write failing detail and viewer tests**

Assert the public hierarchy is:

```text
breadcrumb -> subject/date/type -> title -> authors -> numbered affiliations
-> corresponding author -> TOC graphic -> abstract -> keywords -> manuscript download
-> funding/data/conflict/ethics/preprint/AI disclosure -> supporting information
-> reader evaluation -> reader discussion -> related papers
```

Assert private files and comments are absent. For a PDF SI file, assert page navigation, zoom, fullscreen, and download controls. For non-PDF SI, assert download only.

**Step 2: Run tests to verify they fail**

Run: `cd frontend_nuxt && npm test -- tests/pages/paper-detail.test.js tests/components/SupportingInformationViewer.test.js`

Expected: FAIL because the current page shows a generic manuscript block and no PDF.js viewer.

**Step 3: Recompose the detail page**

Keep the existing comment, reaction, subscription, notification, moderation, and rating logic. Move those community features after the formal scholarly record. Remove the fake/full manuscript text presentation; show a formal DOCX download and optional PDF Version download instead. Do not display fabricated citation, impact-factor, or Altmetric values.

Use the normalized author/affiliation/funding/file DTOs with legacy fallbacks for old papers. Use the public corresponding email only. Use a restrained sticky right rail for OpenIsle id, publication date, views, downloads, rating count, and discussion count.

**Step 4: Implement PDF.js SI preview**

Load `pdfjs-dist` only on the client. Render one active public SI PDF to canvas, switch between multiple SI files, lazy-load on mobile, and clean up render tasks/object state on unmount. The viewer fetches `/api/papers/{paperId}/files/{fileId}/content?mode=preview`; download uses `mode=download`.

Document that production COS must permit the frontend origin for signed PDF GET requests. Show a clear downloadable fallback when PDF loading fails.

**Step 5: Add responsive E2E checks**

At desktop and mobile widths, verify TOC graphic aspect ratio, no overlapping right rail, nonblank PDF canvas pixels, stable viewer controls, long title wrapping, and community controls still functioning.

**Step 6: Run tests and build**

Run: `cd frontend_nuxt && npm test -- tests/pages/paper-detail.test.js tests/components/SupportingInformationViewer.test.js`

Run: `cd frontend_nuxt && npm run build`

Expected: PASS and successful build.

**Step 7: Commit**

```bash
git add frontend_nuxt/pages/papers/[id]/index.vue frontend_nuxt/components/PaperArticleHeader.vue frontend_nuxt/components/PaperArticleMetadata.vue frontend_nuxt/components/SupportingInformationViewer.vue frontend_nuxt/assets/paper-article.css frontend_nuxt/tests
git commit -m "feat: add formal paper record and SI preview"
```

### Task 14: Document, Verify, and Demonstrate the Complete Workflow

**Files:**
- Create: `docs/paper-submission-api.md`
- Modify: `docs/paper-platform-technical-plan.md`
- Modify: `docs/paper-platform-business-rules.md`
- Modify: `docs/plans/2026-07-12-est-style-paper-submission-design.md`
- Review only: `mcp/src/openisle_mcp/schemas.py`
- Review only: `mcp/src/openisle_mcp/server.py`

**Step 1: Document the final API and privacy matrix**

Include endpoint requests/responses, autosave version conflicts, validation issue format, file role/visibility rules, finalization transaction, idempotency behavior, public/private field matrix, and local/COS storage requirements. Explicitly record that no MCP tool was added because drafts are browser-interactive owner state, so MCP callers are unaffected.

**Step 2: Run focused backend tests**

Run: `cd backend && mvn -Dtest=PaperSubmissionPersistenceTest,PaperSubmissionValidatorTest,PaperSubmissionDraftServiceTest,PaperSubmissionDraftControllerTest,PaperFilePolicyTest,PaperSubmissionFileServiceTest,PaperSubmissionFinalizationTest,PaperFileAccessServiceTest,PaperServiceTest test`

Expected: all targeted tests PASS.

**Step 3: Run full backend verification**

Run: `cd backend && mvn test`

Expected: BUILD SUCCESS.

**Step 4: Run frontend unit and build verification**

Run: `cd frontend_nuxt && npm test`

Run: `cd frontend_nuxt && npm run build`

Expected: all tests PASS and Nuxt build succeeds.

**Step 5: Run end-to-end verification**

Start the existing backend and frontend development services, then run:

`cd frontend_nuxt && npm run test:e2e`

Expected: the submission workspace, review/finalization, public detail, and SI viewer specs PASS at desktop and mobile viewports.

Manually verify:

```text
sign in -> open /papers/submit -> autosave -> refresh restore
-> upload DOCX + cover letter + TOC graphic + public SI PDF
-> add two authors and multiple affiliations -> review -> edit exact section
-> confirm once -> AI screening -> published paper
-> SI preview -> download -> rate -> comment -> receive existing notification
```

Also verify a guest cannot retrieve cover letter/review-only/private file content even with a known file id.

**Step 6: Review migration and API output**

Run the application against a clean MySQL database with migrations enabled. Confirm `V14` applies once and `ddl-auto=validate` reports no drift once the existing migration-formalization work is complete. Inspect `/api/v3/api-docs` for all draft/file endpoints and regenerate the docs site if that workflow is currently active.

**Step 7: Commit documentation and final verification changes**

```bash
git add docs/paper-submission-api.md docs/paper-platform-technical-plan.md docs/paper-platform-business-rules.md docs/plans/2026-07-12-est-style-paper-submission-design.md
git commit -m "docs: document paper submission workflow"
```

## Acceptance Checklist

- No incomplete `Post` or `PaperProfile` is created before author confirmation.
- Draft autosave survives refresh and reports conflicts instead of overwriting another tab.
- One DOCX manuscript, one cover letter, and one TOC graphic are required.
- Exactly one corresponding author is enforced by frontend and backend.
- Every author has at least one affiliation and exactly one primary affiliation.
- Cover letters, review-only files, private comments, and private contact/address data never leak publicly.
- Final submission is atomic and idempotent, then follows existing AI screening/publication behavior.
- The public page presents structured HTML metadata, not a fake parsed manuscript body.
- Public SI PDFs preview online with PDF.js; unsupported SI remains downloadable.
- Existing ratings, comments, reactions, subscriptions, notifications, moderation, feed, and rankings continue working.
- Desktop and mobile layouts have no clipped controls, overlapping sticky regions, or horizontal overflow.
