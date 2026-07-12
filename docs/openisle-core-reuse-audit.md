# OpenIsle Core Reuse Audit for the Paper Platform

## Purpose

The paper platform must be built as an extension of OpenIsle, not as a parallel product inside the same repository.

The development rule from this point forward is:

> Reuse OpenIsle core behavior first. Add paper-specific tables and services only where the original platform does not already provide the capability.

## Reuse Map

| Paper platform need | OpenIsle core capability | Decision |
| --- | --- | --- |
| Public content body | `Post.title`, `Post.content`, `Post.author`, `Post.status` | Reuse. A paper is a specialized post with `PostType.PAPER`. |
| Discussion | `Comment`, `CommentService`, `CommentController`, comment timeline UI | Reuse. Paper detail should eventually embed the existing comment flow instead of creating a separate discussion system. |
| Likes and reactions | `Reaction`, `ReactionService`, `ReactionsGroup.vue` | Reuse for lightweight social feedback. Keep paper rating separate because ratings are formal score inputs. |
| Notifications | `NotificationService`, `NotificationType`, message page | Reuse for paper submission, screening result, comments, mentions, and admin actions. |
| Categories and tags | `Category`, `Tag`, post filtering | Reuse for paper subject discovery where possible. Paper-specific `subjectArea` can remain metadata, but public browsing should align with category/tag mechanics over time. |
| Admin post moderation | `AdminPostController`, post status `PENDING/PUBLISHED/REJECTED` | Reuse for generic content moderation. Add paper admin endpoints only for paper-specific screening, ratings, withdrawal, and retraction. |
| Uploads | `UploadController`, `ImageUploader`, presigned upload support | Reuse as the starting point. Extend upload policy to support manuscript files instead of creating a separate file pipeline. |
| Search | `SearchService` and existing post search fallback | Reuse for title/body/comment search. Add paper metadata search only for fields not covered by `Post`. |
| User identity | `User`, `Role`, auth, profile pages | Reuse. Paper author records should link to `User` when possible. Expert profiles extend user identity but do not replace it. |

## Paper-Specific Extension Boundary

The persistence and reuse boundary is explicit:

- `Post` owns finalized community behavior: comments, reactions, subscriptions, notifications, and moderation.
- `PaperProfile` owns formal finalized paper metadata and publication state.
- `PaperSubmissionDraft` owns incomplete private form state only and never substitutes for either finalized object.

Partial saves and autosaves must not create `Post` or `PaperProfile` rows.

The following objects are still justified as paper-specific extensions:

- `PaperSubmissionDraft`: owner-scoped partial form state and draft file references before final submission.
- `PaperProfile`: formal finalized paper metadata, lifecycle status, screening status, declarations, references, and publication state.
- `PaperAuthor`: ordered author snapshot, author role, exactly-one corresponding author rule, and equal contribution flag.
- `PaperAuthorAffiliation`: multiple affiliation links per author with exactly one primary affiliation.
- `PaperFundingRecord`: structured finalized funding data.
- `PaperFile`: finalized role-based file records with enforced public/private visibility.
- `Institution`: normalized institution identity and ranking support.
- `ExpertProfile`: long-term researcher/expert identity derived from authors and later ORCID binding.
- `AiScreeningResult`: AI admission and risk-control result.
- `PaperRating`: formal reader rating record.
- `PaperScoreSnapshot`: calculated score for feeds and rankings.

These objects should link back to OpenIsle core objects, especially `Post` and `User`.

Normalized `PaperFile` rows are the authority for finalized file metadata, visibility, and access. Any legacy file summaries retained on `PaperProfile` are compatibility projections only.

## Submitter And Paper Author Rule

OpenIsle has one native content author:

```text
posts.author_id -> users.id
```

For papers, this user is the submitting account. The submitting account owns the underlying post and therefore receives normal OpenIsle interaction notifications such as comments, replies, reactions, subscriptions, mentions, and admin post actions.

The scholarly author list is separate:

```text
paper_authors.paper_id -> paper_profiles.id
paper_authors.user_id -> users.id nullable
```

`PaperAuthor` records drive the academic paper display, author order, equal contribution, corresponding author labels, author rankings, institution rankings, and expert database construction.

MVP rule:

- Keep submitter notification and interaction behavior on `Post.author`.
- Display scholarly authors from `PaperAuthor`, not from `Post.author`.
- Link `PaperAuthor.user_id` when a contributor email matches a registered user.
- Do not block submission just because the submitter is not yet matched to one listed author. This can be tightened later when ORCID/account binding is implemented.
- Require every finalized author to have email, given name, family name, author role, at least one affiliation, and exactly one primary affiliation.
- Require exactly one corresponding author for the finalized paper.

Future rule:

- Support explicit submitter roles such as `Submitting author`, `Corresponding author`, `Author assistant`, and `Admin import`.
- Use ORCID login/binding to verify author identity instead of relying only on contributor email.

## Notification Reuse Rule

OpenIsle already has a complete notification preference system:

- `NotificationType` defines notification categories.
- `NotificationService` creates notification records.
- `User.disabledNotificationTypes` stores in-app notification preferences.
- `User.disabledEmailNotificationTypes` stores email notification preferences.
- The message page already renders notification settings.

Paper development must not create a separate paper notification setting table or a separate paper notification center.

Paper events should map to existing notification infrastructure:

| Paper event | Preferred reuse path |
| --- | --- |
| Paper submitted and waiting for platform review | Use `POST_REVIEW_REQUEST` on the underlying `PostType.PAPER` post. |
| Paper screening approved or rejected | Use `POST_REVIEWED` first; add a paper-specific `NotificationType` only if the existing wording cannot represent screening status. |
| Paper receives a public comment | Use existing comment notification flow through `CommentService` and `POST_UPDATED` / `COMMENT_REPLY`. |
| Paper author is mentioned | Use existing `MENTION` notification flow. |
| Reader likes or reacts to a paper post | Use existing `REACTION` notification flow. |
| Reader rates a paper | Prefer a new paper-specific notification only if product requires notifying authors about formal ratings. Otherwise avoid notification noise in the MVP. |
| Paper is withdrawn, retracted, or deleted by admin | Reuse `POST_DELETED` where possible; add paper-specific status text in the notification content if needed. |

If a new paper notification type is truly needed, it must still be added to the existing `NotificationType` enum and existing preference UI, not implemented through a parallel paper-only notification system.

## Immediate Corrections

1. Partial paper submissions must remain in `PaperSubmissionDraft`; only final submission creates a `Post` with `PostType.PAPER` and a `PaperProfile`.
2. Paper pages should progressively reuse existing `Post` detail capabilities: comments, reactions, subscriptions, admin actions, and notification behavior.
3. Manuscript upload should reuse `/api/upload` or its presigned upload path after the upload policy is extended beyond images.
4. Admin paper management should be added as a paper layer on top of existing admin post moderation, not as an unrelated backend.
5. Frontend paper UI can keep its academic style, but reusable primitives such as comment editor, reaction group, dropdowns, and auth state should come from OpenIsle components.
6. Paper notification behavior must use the existing OpenIsle notification preference system. Do not create paper-only notification settings.
7. Finalization implementation must remain idempotent and atomic across `Post`, paper metadata, authors, affiliations, funding, authoritative `PaperFile` rows, and screening state.
8. Submission validation, public-contact confirmation, affiliation visibility, required file roles, and other detailed business rules must follow [paper-platform-business-rules.md](./paper-platform-business-rules.md) as the source of truth instead of being duplicated here.
9. Compatibility summaries on `PaperProfile` must not become an alternate visibility or access-control path around authoritative `PaperFile` records.

## Browser Draft And MCP Boundary

The browser draft endpoints are intentionally not exposed as MCP tools. Draft creation, autosave, recovery, validation, and draft-file management are interactive owner-scoped workflows, and exposing them through MCP would expand the private partial-state surface without a finalized paper contract.

Finalized paper APIs remain the future MCP integration boundary. Any future MCP tools should operate on formally finalized paper resources and preserve the same validation, idempotency, transaction, and privacy rules.

## Current Deviation To Watch

The current MVP paper pages use custom paper feed/detail/rating UI. This is acceptable for paper-specific presentation, but risky if it duplicates:

- Comment rendering.
- Reaction controls.
- Admin moderation actions.
- Upload handling.
- Notification flows.

Future work should connect those areas back to OpenIsle core before adding more paper-specific surface area.
