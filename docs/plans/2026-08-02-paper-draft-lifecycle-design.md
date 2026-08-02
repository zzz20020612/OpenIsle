# Paper Draft Lifecycle Design

## Goal

Make paper drafts predictable by treating original-submission drafts and revision drafts as two separate workflows. Users must always know which draft they are opening and must be able to decide whether an edited draft is retained when they leave the submission workspace.

## Draft Types

### Original-submission draft

An original-submission draft represents a new, independent paper submission.

- It is entered only from the global `Submit` action or from an explicit draft entry in `My Submissions`.
- Opening a blank submission workspace does not persist a draft.
- The backend draft is created on the first meaningful edit or file upload.
- Multiple non-empty original-submission drafts are allowed.
- Original drafts never resume revision work.

### Revision draft

A revision draft represents changes to one finalized paper whose latest version has status `NEEDS_REVISION`.

- It is entered only from `Revise Submission` on the source paper or from that paper's revision-draft entry in `My Submissions`.
- Creation copies the source paper's metadata, authors, affiliations, funding, files, and editable article content.
- It is therefore never an intentionally blank workspace.
- A source paper can have at most one `IN_PROGRESS` revision draft.
- Reopening the revision action resumes that exact draft.
- A global `Submit` action never opens a revision draft.

## Entry Behavior

### Global Submit

1. If there are no non-empty original drafts, open a client-side blank workspace.
2. If there is one non-empty original draft, show its title and last-edited time with these actions:
   - `Continue Draft`
   - `Start New Submission`
3. If there are multiple non-empty original drafts, show a selectable list with title and last-edited time plus `Start New Submission`.
4. `Start New Submission` opens another client-side blank workspace. It does not delete or replace existing drafts.
5. An explicit draft URL opens only the requested owner-scoped draft ID.

### Revise Submission

1. Resolve the latest eligible paper version.
2. If an `IN_PROGRESS` revision draft already exists for it, open that draft.
3. Otherwise create one prefilled revision draft and open it.
4. Old paper versions cannot create parallel revision branches.

## Meaningful Content

A blank workspace is not a persisted draft. A workspace becomes meaningful when the user performs at least one of these actions:

- Changes a user-editable form value from its default.
- Adds, replaces, or removes a submission file.
- Changes imported or parsed article content.

Navigation between form sections alone is not meaningful content and must not create a draft.

Existing empty original drafts should be omitted from active-draft responses. They may be marked `ABANDONED` by a bounded cleanup operation after the emptiness predicate is shared with the service layer.

Revision drafts are meaningful immediately because they are prefilled from a finalized paper.

## Leaving the Workspace

For site-controlled navigation away from a meaningful, editable draft, show a confirmation dialog:

- `Keep Draft & Exit`: flush pending autosave, retain the draft, then navigate.
- `Discard Draft`: mark the draft `ABANDONED`, then navigate.
- `Continue Editing`: close the dialog without navigation.

For a blank client-side original workspace, leave immediately without a prompt or backend draft.

For browser tab close, refresh, or external navigation, browsers do not allow a reliable custom three-action dialog. The application should flush autosave where possible, use the native unsaved-changes warning when work is pending, and default to retaining the draft.

After successful final submission, the draft becomes `SUBMITTED`; leaving does not show a retain/discard prompt.

Discarding a revision draft affects only its private workspace and draft-scoped files. It never deletes or changes the finalized source paper.

## My Submissions

`My Submissions` should distinguish the two draft types:

- A `New Submission Drafts` section lists all meaningful original drafts.
- A revision draft appears with its source paper as `Revision Draft`, not in the original-draft list.
- Every draft entry shows a title (or `Untitled submission`), last-edited time, and an explicit `Continue` action.
- Finalized revisions remain versions of the same submission lineage; old versions are view-only.

## API Direction

The existing owner-scoped draft APIs remain the base. The workflow needs these contract changes:

- List all active, meaningful original drafts instead of exposing only the most recently updated one.
- Keep exact draft-ID retrieval for explicit resume links.
- Keep source-paper-specific revision creation/resume idempotent.
- Support creating an original draft with its first meaningful payload, so a blank page view creates no row.
- Keep discard as `IN_PROGRESS -> ABANDONED`.

Backward-compatible `GET /current?kind=ORIGINAL` may remain temporarily, but new UI must not use it to hide other active original drafts.

## Failure Handling

- If draft creation or autosave fails, keep local form values and block navigation until the user retries or explicitly discards local work.
- If optimistic locking reports a conflict, do not overwrite the server draft; show the existing conflict recovery UI.
- If revision prefill fails, do not open an empty revision workspace. Keep the user on the source paper and show an actionable error.
- If discard fails, keep the user in the editor and preserve the draft.

## Verification

Automated coverage must include:

- Opening and leaving a blank original workspace creates no draft row.
- First meaningful edit creates exactly one original draft.
- Multiple meaningful original drafts are returned and can be opened by ID.
- Global Submit never returns a revision draft.
- Revision creation copies source metadata, files, and article content.
- Reopening revision resumes the existing source-specific draft.
- Discard marks either draft type `ABANDONED` without altering a finalized paper.
- Keep-and-exit flushes pending changes before navigation.
- Successful final submission does not show a leave prompt.

Desktop Chrome regression must cover global Submit, multiple-draft selection, blank exit, keep/discard choices, revision prefill, revision resume, review, final submission, screening, and paper detail. Mobile layout is not a release blocker for this change.
