# Paper Workflow Hardening Design

## Goal

Make the author workflow predictable from authentication through submission, screening, revision, and paper detail. The work covers four connected concerns:

1. Stable authentication that does not discard a valid session because of stale requests or transient network errors.
2. Manageable original and revision drafts with clear identity, metadata, rename, discard, and stale-draft organization.
3. One understandable revision lineage instead of multiple paper rows that appear unrelated.
4. Repeatable regression coverage and a restrained academic publishing interface across the affected pages.

Desktop Chrome is the primary interactive acceptance target. Mobile must remain usable but is not the release blocker for this phase.

## Product Principles

- A private draft is not a finalized paper.
- Original-submission drafts and revision drafts remain separate workflows.
- A revision is a version of one submission lineage, not a new independent submission in the author workspace.
- Only the latest version of a lineage can create or resume a revision.
- Meaningful drafts are never deleted automatically.
- Authentication failures and connectivity failures are different states.
- Imported document content is an editable starting point. Parse errors must not destroy the uploaded source or block author correction.
- UI copy remains English and describes user actions rather than internal implementation.

## 1. Authentication Stability

### Current Failure Mode

`app.vue` starts an asynchronous token check during application mount. Login stores a new token and then loads the current user. A token check that started with an older token can finish later and call `clearToken()` without verifying which token is now current. `checkToken()` also clears the session after a network exception. These behaviors can explain both first-login failure and unexpected redirects to Login.

### Session Model

Create one client-side authentication session module responsible for token persistence, current-user hydration, validation, and logout.

- Every validation request captures the token it validates.
- A failed validation may clear the session only when the captured token still equals the current stored token.
- An explicit authentication response (`401` with the invalid-token contract) may invalidate that matching token.
- Timeout, connection refusal, DNS failure, and other transport errors set a recoverable connection state and never clear a token.
- Concurrent hydration and validation calls for the same token share one in-flight promise.
- Storing a new token increments the session generation so older requests cannot mutate the new session.
- Login navigation happens only after the new token is stored and the current user is hydrated, or after an explicit actionable profile-load failure is shown.
- Protected-route middleware preserves the requested internal redirect and does not depend on a temporarily unhydrated `authState`.

### Login UI

- Use a semantic form with username and password labels.
- Support Enter submission and prevent duplicate requests.
- Keep server validation errors near the form.
- Preserve the requested destination after successful login.
- Replace the decorative greeting layout with a restrained account-access panel consistent with the paper platform.

## 2. Draft Management

### Draft Identity

Add an optional user-editable `displayName` to `PaperSubmissionDraft`. It identifies the workspace and is independent from the formal manuscript title.

Fallback display order:

1. `displayName`
2. manuscript title
3. primary manuscript filename
4. `Untitled submission`

### Draft Summary Contract

Active-draft summaries expose:

- ID and kind.
- Display name and manuscript title.
- Primary manuscript original filename.
- Uploaded file count.
- Article parse status.
- Last-edited timestamp.
- Revision source identity when applicable.
- A derived stale flag based on 30 days without an update.

The list response continues to omit empty original drafts. Revision drafts remain meaningful immediately because they are prefilled.

### Draft Actions

- Rename updates only `displayName`; it does not change the manuscript title.
- Continue opens the exact owner-scoped draft ID.
- Delete uses the existing `IN_PROGRESS -> ABANDONED` transition and requires confirmation.
- Delete never changes a finalized source paper.
- Active meaningful drafts are not deleted automatically.
- Drafts older than 30 days appear under a collapsed `Older drafts` group with an explicit cleanup prompt.
- A bounded maintenance job may remove unreferenced files belonging to already abandoned drafts after a documented retention period.

### Author UI

`My Submissions` receives a dedicated Draft Workspace section with compact record rows rather than large cards. Each row includes distinguishing metadata and `Continue`, `Rename`, and `Delete` actions. The global Submit chooser uses the same summary presentation so users can recognize the same draft in both places.

## 3. Revision Lineage

### Lineage Model

Continue storing each finalized revision as its own `PaperProfile`, linked by `revisionOfPaper`. The backend, not the frontend, resolves the chain and returns a lineage-oriented DTO.

The lineage response contains:

- Root paper ID.
- Latest paper ID and latest version number.
- Effective author-workspace status from the latest version.
- Ordered versions with stored publication and screening states.
- The active revision draft for the latest eligible version, if present.
- The only currently valid revision action.

The service must handle historical chains such as paper 6 -> paper 7 -> paper 8, not only direct children.

### Author Workspace

`My Submissions` shows one row/card per lineage. The primary action and status come from the latest version. Expanding `Version History` shows the original and every revision with dates, screening results, and detail links.

Historical versions are read-only and show `Superseded by Revision N` when a newer version exists. They never display a revision action.

### Status Flow

```text
Latest version: NEEDS_REVISION
  -> create/resume prefilled revision draft
  -> finalize revision as next version: SCREENING
  -> screening outcome
       PASSED             -> latest version PUBLISHED
       NEEDS_REVISION     -> latest version NEEDS_REVISION; revision enabled
       FAILED/UNAVAILABLE -> latest version remains SCREENING; admin retry enabled
       REJECTED_BY_POLICY -> latest version REJECTED
```

Submitting a revision does not rewrite historical version status. The lineage UI explains that the historical record was superseded, while the latest version controls current actions.

### Detail Navigation

- A historical paper detail offers `View Latest Version` when the viewer may access it.
- Detail pages include a compact version selector for authorized authors and admins.
- Public access remains governed per version by `PaperAccessPolicy`; unpublished versions never become public merely because another version in the lineage was published.

## 4. Import, Editing, Submission, and Screening Recovery

### DOCX Import

- Preserve the uploaded DOCX as the source artifact even if parsing fails.
- Represent parsing as an explicit status: not started, processing, ready, or failed.
- A failed parse displays the reason, `Retry parsing`, `Replace file`, and `Edit manually` paths.
- Parsed content is saved into the private draft and remains author-editable before preview and final submission.
- Formula or structure conversion warnings are advisory when the author can correct the preview; they must not masquerade as a successful exact conversion.

### Final Submission

- Flush draft edits before review and finalization.
- Keep finalization idempotent and return the existing finalized paper for a repeated idempotency key.
- On validation or network failure, retain the editable draft and show a retryable error.
- Never create a second paper because a response was lost after a successful transaction.

### Screening

- Screening service failure leaves the finalized paper in `SCREENING`.
- Store the failed screening attempt and expose an admin retry action.
- Do not publish, reject, or create a revision automatically after an infrastructure failure.
- Author-facing status copy distinguishes `Screening in progress`, `Changes requested`, `Published`, and `Screening could not complete`.

## 5. Visual Direction

The affected pages use one restrained academic editorial system:

- Strong typographic hierarchy with serif display headings and neutral sans-serif controls.
- Compact record rows and tables for operational information.
- Fine borders, white or lightly tinted surfaces, and a limited blue/teal accent.
- Square or subtly rounded controls; no excessive pills, gradients, oversized promotional cards, or ornamental glow.
- Sentence-case labels and direct action copy; avoid generic AI-style slogans and repeated uppercase decoration.
- Status always combines text with color and remains understandable without color.
- Login, My Submissions, draft chooser, submission editor, preview, screening state, and paper detail share spacing, control, and status patterns.

## 6. Error Handling

- Authentication transport failure: retain token, show a recoverable connection state.
- Authentication rejection for a matching current token: clear session once and preserve the internal return path.
- Draft rename failure: keep the previous name and show an inline error.
- Draft discard failure: retain the row and draft contents.
- Parse failure: retain the DOCX and editable workspace.
- Autosave conflict: preserve local values and use the existing conflict recovery flow.
- Revision prefill failure: remain on the latest paper and do not create an empty revision.
- Finalization uncertainty: retry with the same idempotency key.
- Screening infrastructure failure: retain `SCREENING` and expose retry to admins.

## 7. Verification Strategy

### Backend

- Authentication controller and token behavior tests where server contracts are involved.
- Draft rename, summary, stale classification, discard, ownership, and revision isolation tests.
- Revision-chain grouping, latest-version resolution, latest-only revision creation, and status-transition tests.
- Finalization idempotency and transaction rollback tests.
- Screening success, requested-revision, rejected, failure, and retry tests.

### Frontend

- Unit tests for token generation/compare-and-clear behavior and network-error retention.
- Unit tests for draft display fallback, stale grouping, and lineage presentation.
- Existing document reader and math tests remain required.
- Add deterministic DOCX import fixtures for successful parsing, warnings, and failure recovery.

### Desktop Chrome Regression

Use `user1` to verify:

1. First login, Enter login, redirect restoration, refresh, and temporary API failure behavior.
2. Empty submission entry, multiple draft recognition, rename, delete, stale grouping, and exact resume.
3. DOCX upload, parse state, author edit, preview, save, leave, and resume.
4. Review, final submission, response retry, screening outcome, and paper detail.
5. Revision prefill, revision submission, another requested revision, lineage history, and latest-version navigation.
6. No unexpected console errors or authentication redirects during the full flow.

## 8. Delivery Order

1. Stabilize authentication and add regression tests.
2. Add draft summary/rename contracts and author draft-management UI.
3. Add lineage DTO, latest-only revision rules, and version-history UI.
4. Harden import, submission, and screening recovery with automated fixtures.
5. Complete cross-page visual consistency and run the full Chrome acceptance matrix.

Each stage is independently testable and must preserve the paper visibility, rating, ranking, privacy, and revision-draft invariants defined in the platform business rules.
