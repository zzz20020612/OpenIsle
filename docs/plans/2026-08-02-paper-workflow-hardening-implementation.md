# Paper Workflow Hardening Implementation Plan

## Delivery Rules

- Work in the order below because authentication stability is required for reliable browser regression.
- Keep API additions backward compatible while existing consumers migrate.
- Add tests before or with each behavior change.
- Commit each stage separately and stage only task-owned files.
- Preserve unrelated working-tree changes.
- Product UI remains English; implementation communication remains Chinese.

## Stage 1: Stabilize Authentication

### 1.1 Extract testable session concurrency rules

Files:

- Add `frontend_nuxt/utils/authSessionCore.js`.
- Add `frontend_nuxt/test/authSessionCore.test.mjs`.

Work:

1. Implement a session generation counter and captured-token comparison helper.
2. Implement an in-flight request registry keyed by token and operation.
3. Classify authentication rejection separately from transport failure.
4. Test that an old-token response cannot clear a newer token.
5. Test that a network exception retains the current token.
6. Test that a matching explicit invalid-token response clears once.
7. Test that concurrent checks for the same token share one request.

Verification:

```powershell
cd frontend_nuxt
node --test test/authSessionCore.test.mjs
```

### 1.2 Centralize session establishment and validation

Files:

- Modify `frontend_nuxt/utils/auth.js`.
- Modify `frontend_nuxt/plugins/auth-fetch.client.ts`.
- Modify `frontend_nuxt/app.vue`.
- Modify `frontend_nuxt/middleware/auth.client.js` only if redirect handling needs adjustment.

Work:

1. Replace unconditional `clearToken()` paths with captured-token invalidation.
2. Do not clear on transport errors.
3. Deduplicate `loadCurrentUser()` and `checkToken()` by current token.
4. Make `setToken()` establish the new session generation before hydration.
5. Return structured results (`authenticated`, `invalid`, `unavailable`) to callers.
6. Keep the fetch interceptor as a narrow explicit-401 safety net using the same comparison rule.
7. Ensure app startup cannot race against a later successful login.

### 1.3 Rebuild login interaction

Files:

- Modify `frontend_nuxt/pages/login.vue`.
- Reuse shared styles in `frontend_nuxt/assets/paper-platform.css` where appropriate.

Work:

1. Use a semantic form and submit button.
2. Add visible field labels, `autocomplete`, Enter handling, and duplicate-submit protection.
3. Hydrate the current user before redirecting.
4. Preserve safe internal redirect paths.
5. Show inline credential, account-state, and connection errors.
6. Replace the decorative greeting with a compact academic account panel.

Verification:

```powershell
cd frontend_nuxt
npm run test:reader
npm run build
```

Chrome acceptance:

- First login succeeds.
- A stale startup check cannot undo the login.
- Refresh keeps the session.
- A temporary backend failure does not return the user to Login.
- An actually invalid token returns to Login with the intended destination preserved.

## Stage 2: Add Draft Management Contracts

### 2.1 Persist a draft display name

Files:

- Add the next available Flyway migration after reconciling the existing V17 work, expected `backend/src/main/resources/db/migration/V18__add_paper_draft_display_name.sql`.
- Modify `backend/src/main/java/com/openisle/model/PaperSubmissionDraft.java`.
- Modify `backend/src/main/java/com/openisle/dto/PaperSubmissionDraftDto.java`.
- Add `backend/src/main/java/com/openisle/dto/PaperSubmissionDraftRenameRequest.java`.

Work:

1. Add nullable `display_name` with a bounded length.
2. Keep manuscript title in form JSON; do not copy rename changes into formal metadata.
3. Add validation and trimming for user-provided display names.

### 2.2 Enrich draft summaries and rename endpoint

Files:

- Modify `backend/src/main/java/com/openisle/controller/PaperSubmissionDraftController.java`.
- Modify `backend/src/main/java/com/openisle/service/PaperSubmissionDraftService.java`.
- Modify `backend/src/main/java/com/openisle/repository/PaperSubmissionFileRepository.java` if an aggregate query is needed.
- Modify `backend/src/test/java/com/openisle/service/PaperSubmissionDraftServiceTest.java`.
- Add or extend a controller test for the owner-scoped rename endpoint.

API:

```text
PATCH /api/paper-submission-drafts/{draftId}/name
{ "displayName": "Lake pollution manuscript" }
```

Draft DTO additions:

```text
displayName
manuscriptTitle
primaryManuscriptFileName
fileCount
articleStatus
stale
```

Work:

1. Enforce draft ownership and `IN_PROGRESS` status for rename.
2. Derive fallback display data without changing finalized-paper data.
3. Derive stale using 30 days at response time.
4. Preserve current meaningful-draft filtering and revision separation.
5. Keep discard as the existing soft transition.

Backend verification:

```powershell
cd backend
mvn -Dtest=PaperSubmissionDraftServiceTest test
mvn test
```

### 2.3 Build draft management UI

Files:

- Modify `frontend_nuxt/composables/paperApi.js`.
- Modify `frontend_nuxt/pages/papers/submissions.vue`.
- Modify `frontend_nuxt/pages/papers/submit/index.vue`.
- Add focused presentation helpers under `frontend_nuxt/utils/` with Node tests if grouping logic is nontrivial.

Work:

1. Use one fallback naming function across My Submissions and the Submit chooser.
2. Show manuscript filename, file count, parse state, and full last-edited date.
3. Add inline rename with save/cancel/error states.
4. Add a project-styled discard confirmation instead of `window.confirm` for managed lists.
5. Group drafts older than 30 days under collapsed `Older drafts`.
6. Keep `Continue`, `Start New Submission`, and exact-draft navigation unchanged.
7. Verify rename and discard do not affect finalized papers or revision drafts outside the chosen row.

## Stage 3: Make Revision Lineage Authoritative

### 3.1 Add lineage DTOs and chain resolution

Files:

- Add `backend/src/main/java/com/openisle/dto/PaperLineageDto.java`.
- Add `backend/src/main/java/com/openisle/dto/PaperVersionSummaryDto.java`.
- Modify `backend/src/main/java/com/openisle/repository/PaperProfileRepository.java`.
- Modify `backend/src/main/java/com/openisle/service/PaperService.java`.
- Modify `backend/src/main/java/com/openisle/controller/PaperController.java`.
- Extend `backend/src/test/java/com/openisle/service/PaperServiceTest.java`.

API direction:

- Change `GET /api/papers/mine` to return lineage records, or add a backward-compatible `/api/papers/mine/lineages` endpoint and migrate the frontend before retiring the flat representation.

Work:

1. Resolve the root by walking `revisionOfPaper` ancestors.
2. Resolve all descendants in revision-number order.
3. Detect malformed cycles defensively and fail with an actionable server error.
4. Choose current status and primary action only from the latest version.
5. Attach the active revision draft only to that latest version.
6. Return historical stored statuses for audit display without making them actionable.

Tests:

- paper 6 -> 7 -> 8 groups into one lineage.
- paper 8 is latest and revision 3 when the source numbers are 1 and 2.
- direct-child-only queries cannot incorrectly label paper 7 as globally latest.
- malformed lineages do not loop.
- visibility remains version-specific.

### 3.2 Enforce latest-only revision creation

Files:

- Modify `backend/src/main/java/com/openisle/service/PaperSubmissionDraftService.java`.
- Modify `backend/src/main/java/com/openisle/repository/PaperProfileRepository.java`.
- Extend `backend/src/test/java/com/openisle/service/PaperSubmissionDraftServiceTest.java`.

Work:

1. Reject revision creation from any version with a descendant.
2. Resume one existing in-progress revision draft for the latest source.
3. Prefill metadata, authors, files, and article from that exact latest source.
4. On finalization, set the new revision number from the latest source and link it directly.
5. Preserve finalization idempotency.

### 3.3 Replace flat revision UI with version history

Files:

- Modify `frontend_nuxt/composables/paperApi.js`.
- Rewrite the paper-record portion of `frontend_nuxt/pages/papers/submissions.vue`.
- Modify `frontend_nuxt/pages/papers/[id]/index.vue`.
- Add a reusable version-history component if both pages need the same presentation.

Work:

1. Show one submission record per lineage.
2. Show latest status and only the valid latest action.
3. Expand `Version History` for original and revisions.
4. Label old versions as superseded and keep them read-only.
5. Add `View Latest Version` from historical detail.
6. Keep author/admin private visibility and public-version rules unchanged.

## Stage 4: Harden Import and Article Editing

### 4.1 Make import results explicit

Files:

- Modify `frontend_nuxt/composables/usePaperArticleDraft.js`.
- Modify the DOCX import utility used by `frontend_nuxt/pages/papers/submit/[draftId]/content/index.vue`.
- Modify the editor and preview pages.
- Extend `frontend_nuxt/test/paperArticleReader.test.mjs` and `paperMath.test.mjs`.
- Add deterministic DOCX fixtures under `frontend_nuxt/test/fixtures/`.

Work:

1. Preserve the uploaded source file regardless of parse outcome.
2. Represent processing, ready, warning, and failure states explicitly.
3. Surface parser warnings without blocking author correction.
4. Add retry parsing, replace file, and continue manual editing actions.
5. Confirm imported edits survive save, preview, exit, and reopen.
6. Keep formula conversion limitations visible as warnings when exact reconstruction is impossible.

### 4.2 Align editor and preview UI

Files:

- Modify `frontend_nuxt/pages/papers/submit/[draftId]/content/index.vue`.
- Modify `frontend_nuxt/pages/papers/submit/[draftId]/content/preview.vue`.
- Modify relevant `frontend_nuxt/components/paper-article/*` components.

Work:

1. Use a quiet three-region editorial workspace with consistent controls.
2. Replace generic command-button styling with the shared paper control hierarchy.
3. Make parse warnings, validation errors, and save status visually distinct.
4. Keep the full preview visually close to the published detail renderer.

## Stage 5: Submission and Screening Recovery

### 5.1 Verify finalization idempotency and rollback

Files:

- Extend `backend/src/test/java/com/openisle/repository/PaperSubmissionPersistenceTest.java`.
- Extend `backend/src/test/java/com/openisle/service/PaperSubmissionDraftServiceTest.java`.
- Modify finalization code only where tests expose a contract failure.

Coverage:

- repeated idempotency key returns the same paper;
- response loss followed by retry does not duplicate paper, authors, files, or funding;
- persistence failure leaves the draft editable;
- submitted drafts cannot be edited or submitted again under another key.

### 5.2 Harden screening failure and retry

Files:

- Modify only as required: `backend/src/main/java/com/openisle/service/AiScreeningProcessor.java`.
- Modify only as required: `backend/src/main/java/com/openisle/service/PaperAdminService.java`.
- Extend `AiScreeningProcessorTest.java` and `PaperAdminServiceTest.java`.
- Modify `frontend_nuxt/pages/admin/papers.vue` and author/detail status presentation.

Coverage:

- pass publishes;
- changes requested creates no automatic draft but enables the latest revision action;
- infrastructure failure remains screening and can be retried;
- policy rejection remains private;
- retries update the same screening workflow instead of duplicating papers.

## Stage 6: Cross-Page Visual Consolidation

Files:

- Modify `frontend_nuxt/assets/paper-platform.css`.
- Modify Login, My Submissions, submission editor, article editor, review, preview, admin screening, and paper detail pages only where needed.

Work:

1. Define shared academic page shell, record row, form control, action, status, dialog, and empty/error state styles.
2. Remove gradients, decorative glow, excessive radius, oversized cards, redundant all-caps labels, and generic promotional language.
3. Keep typography, spacing, border, and accent hierarchy consistent.
4. Ensure focus states and non-color status cues remain visible.
5. Verify desktop widths first and preserve basic mobile usability.

## Stage 7: Full Acceptance Matrix

Automated commands:

```powershell
cd backend
mvn test

cd ..\frontend_nuxt
npm run test:reader
npm run build
```

If the Windows `.output` lock recurs, run the production build in an isolated output directory or Linux container and record the exact command and result; do not treat successful client/SSR compilation followed by an output cleanup error as a complete build.

Desktop Chrome with `user1` / `123456`:

1. Login first attempt, refresh, redirect return, explicit invalid token, and temporary backend failure.
2. Empty new submission does not persist.
3. Create two meaningful drafts; distinguish, rename, reopen, and delete one.
4. Upload the DOCX fixture; observe parse state; edit imported content; preview; exit; resume.
5. Complete review and submit; retry the same final request without duplication.
6. Verify screening and author-facing state.
7. Open paper detail and verify structured content.
8. Request revision, verify prefill, submit revision, request another revision, and verify one lineage with ordered history.
9. Verify historical detail routes to the latest version and cannot create a parallel revision.
10. Confirm no unexpected login redirects, data loss, duplicate records, or console errors.

## Commit Sequence

1. `bugfix: stabilize client authentication session`
2. `feat: add paper draft management metadata`
3. `feat: add paper draft management workspace`
4. `bugfix: resolve complete paper revision lineages`
5. `feat: present paper version history`
6. `bugfix: harden manuscript import recovery`
7. `bugfix: harden submission and screening recovery`
8. `feat: refine academic paper workflow interface`
9. `test: cover paper workflow end to end`
