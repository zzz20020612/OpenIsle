# Paper Draft Lifecycle Implementation Plan

## Backend

1. Add an owner-scoped repository query that returns every active original-submission draft ordered by last update.
2. Add a service method and `GET /api/paper-submission-drafts?kind=ORIGINAL` endpoint for the active draft list.
3. Filter legacy empty original drafts from this list with a shared service predicate; revision drafts remain meaningful because they are prefilled.
4. Preserve exact ID retrieval, source-specific revision resume, optimistic locking, discard, and finalization contracts.
5. Add service tests for multiple original drafts, empty-draft filtering, revision exclusion, and existing revision prefill/resume behavior.

## Frontend Data Layer

1. Add a `listSubmissionDrafts(kind)` API method.
2. Extend the submission composable with a client-only blank-workspace state.
3. Create a backend original draft only on the first form edit, file upload, or attempt to continue to review.
4. Do not treat section navigation as meaningful content before draft creation.
5. Expose `hasRetainableDraft`, `startBlank`, and `ensureDraft` for page-level navigation handling.

## Submission Entry UI

1. Replace the single-current-draft prompt with a list of all meaningful original drafts.
2. Show title and last-edited time for each draft and open the chosen draft by ID.
3. Make `Start New Submission` open a blank local workspace without calling the create API.
4. Keep query-parameter draft links exact so revision and My Submissions links cannot drift to another draft.

## Exit Choice

1. Add a route-leave guard to the submission workspace.
2. For a meaningful editable draft, present `Keep Draft & Exit`, `Discard Draft`, and `Continue Editing`.
3. Flush autosave before keep-and-exit; call the existing discard API before discard-and-exit.
4. Skip the dialog for a blank local workspace and after successful final submission navigation.
5. Retain the existing native `beforeunload` protection for pending network/local work.

## My Submissions

1. Load active drafts alongside finalized papers.
2. Add a `New Submission Drafts` section for meaningful original drafts.
3. Attach revision-draft actions to their source paper instead of mixing them with original drafts.
4. Keep existing finalized-paper status and revision actions unchanged except where an exact draft resume link is available.

## Verification

1. Run focused backend draft service tests.
2. Run relevant frontend tests if present and `npm run build`.
3. Use desktop Chrome with `user1` to verify blank entry/exit, first edit persistence, multiple draft selection, keep/discard, revision prefill/resume, and the submission-to-screening-to-detail path.
4. Stage only task-owned hunks because the worktree contains unrelated user changes.
