# Paper Platform Business Rules

## 1. Purpose

This document defines the core business rules for the paper platform from submission to publication, rating, scoring, and rankings.

The goal is to keep every public-facing API, admin workflow, and ranking calculation aligned with the same rules. Paper visibility, rating eligibility, and ranking eligibility must not be implemented separately in different services without a shared policy.

## 2. Core Objects

### 2.1 Post

`Post` remains the OpenIsle community content object.

It stores:

- Full paper text or readable body content.
- Comments and discussion.
- Community interactions.
- Category and tag relationships.

`Post` should not become the paper business table.

### 2.2 PaperProfile

`PaperProfile` is the main paper business object.

It stores:

- Title.
- Abstract.
- Keywords.
- References extracted from manuscripts or added later.
- Subject area.
- Paper type.
- Manuscript file metadata.
- Supplementary file metadata.
- Funding statement.
- Conflict of interest statement.
- Data availability statement.
- Ethics statement.
- Publication status.
- Screening status.
- Primary institution derived from author affiliations.
- Creator.
- Published timestamp.

`PaperProfile` has a one-to-one relationship with `Post`.

### 2.3 PaperAuthor

`PaperAuthor` stores the author list for a paper.

It stores:

- Display name.
- Email.
- Institution.
- Country or region.
- Author order.
- Corresponding author flag.
- Co-first author flag.
- Optional linked platform user.

The linked platform user is important for later rules such as blocking co-author self-rating.

`PaperAuthor` should model common paper authorship, not a full contribution taxonomy in the MVP. The normal case is ordered authors plus one or more corresponding authors. The only special authorship case supported in the core submission flow is co-first authorship.

Co-first authors must start from the first author and be continuous. For example, author 1 and author 2 can both be co-first authors. Author 1 and author 3 cannot be co-first authors if author 2 is not also marked co-first.

### 2.4 Institution

`Institution` stores organization identities used by paper metadata and institution rankings.

It stores:

- Name.
- Country.
- Type.
- Website.
- Verification status.

Institution names must eventually support aliasing and merging, because rankings are unreliable if `MIT`, `Massachusetts Institute of Technology`, and `M.I.T.` are treated as different institutions.

### 2.5 AiScreeningResult

`AiScreeningResult` stores the result of the initial AI screening step.

It stores:

- Screening status.
- Risk level.
- Detected subject area.
- Detected paper type.
- Summary.
- Issues JSON.
- Raw response JSON.
- Screened timestamp.

AI screening is an admission and risk-control step. It is not a scholarly quality rating.

### 2.6 PaperRating

`PaperRating` stores one reader's rating for one paper.

It stores:

- Rater.
- Overall score.
- Innovation score.
- Method score.
- Impact score.
- Comment.
- Created and updated timestamps.

There must be only one active rating per user per paper.

### 2.7 PaperScoreSnapshot

`PaperScoreSnapshot` stores the aggregated score for list and ranking queries.

It stores:

- Rating count.
- Average overall score.
- Average innovation score.
- Average method score.
- Average impact score.
- Composite score.

List pages and ranking pages should read from the snapshot instead of recalculating every rating on each request.

## 3. User Roles

### 3.1 Guest

A guest is not logged in.

Allowed:

- View public `PUBLISHED` papers.
- View public rankings.

Not allowed:

- Submit papers.
- Rate papers.
- Access unpublished paper details.

### 3.2 Author

An author is a user who submits a paper or is linked as a co-author.

Allowed:

- Submit papers.
- View their own draft, screening, rejected, withdrawn, or revision-needed papers.
- Edit papers when the paper is still editable.
- Withdraw their own paper when withdrawal is allowed.

Not allowed:

- Rate their own paper.
- Rate a paper where they are a linked co-author.
- Override AI or moderation decisions.

### 3.3 Qualified Reader

A qualified reader is a logged-in user who meets the platform's review qualification rules.

MVP rule:

- Any logged-in non-author user can rate a `PUBLISHED` paper.

Future rule:

- The user must have an approved `ReaderQualification` record, such as master degree or above, institutional email, expert verification, or other platform-defined credential.

### 3.4 Admin / Moderator

An admin or moderator manages platform safety and data quality.

Allowed:

- View all papers.
- Process AI screening exceptions.
- Mark papers as `REJECTED`, `NEEDS_REVISION`, `WITHDRAWN`, or `RETRACTED`.
- Restore papers when policy allows.
- Manage institution normalization and verification.

### 3.5 Expert

An expert is a future specialized reviewer profile.

Future use:

- Expert database.
- Expert-weighted ratings.
- Expert comments.
- Expert recommendation and enterprise services.

Expert rules are not part of the current MVP implementation.

## 4. Paper Status Model

`PaperPublicationStatus` is the main lifecycle status.

### 4.1 DRAFT

The paper is still a private draft.

Rules:

- Visible only to the creator and admins.
- Not visible in the public feed.
- Not visible in rankings.
- Cannot be rated.
- Can be edited by the creator.

### 4.2 SCREENING

The paper has been submitted and is waiting for AI screening or manual review.

Rules:

- Visible only to the creator, linked authors, and admins.
- Not visible in the public feed.
- Not visible in rankings.
- Cannot be rated.
- Can move to `PUBLISHED`, `NEEDS_REVISION`, or `REJECTED`.

### 4.3 PUBLISHED

The paper has passed screening and is public.

Rules:

- Visible to everyone.
- Visible in the public feed.
- Eligible for ratings by qualified non-author readers.
- Eligible for paper, author, and institution rankings after it has at least one valid rating.
- Can later move to `WITHDRAWN` or `RETRACTED`.

### 4.4 NEEDS_REVISION

The paper requires author changes before publication or republication.

MVP rules:

- Visible only to the creator, linked authors, and admins.
- Not visible in the public feed.
- Not visible in rankings.
- Cannot receive new ratings.

Future versioning rule:

- If a previous version was already published, the platform may keep the last published version public while the new revision is private.

### 4.5 REJECTED

The paper failed admission or policy checks.

Rules:

- Visible only to the creator, linked authors, and admins.
- Not visible in the public feed.
- Not visible in rankings.
- Cannot be rated.
- Can be appealed or resubmitted only if the platform later supports that workflow.

### 4.6 WITHDRAWN

The author withdrew the paper.

Rules:

- Not visible in the public feed.
- Not visible in rankings.
- Cannot receive new ratings.
- Existing ratings are retained for audit history but excluded from active rankings.
- The public detail page should eventually show a withdrawal notice if the paper had already been public.

### 4.7 RETRACTED

The platform forcibly removed the paper after publication.

Rules:

- Not visible in the public feed.
- Not visible in active rankings.
- Cannot receive new ratings.
- Existing ratings are retained for audit history but excluded from active rankings.
- The public detail page should eventually show a retraction notice.
- Only admins can mark a paper as retracted.

## 5. Screening Rules

AI screening runs after submission.

### 5.1 Screening Outcomes

Recommended outcomes:

- `PASSED`
- `NEEDS_REVIEW`
- `REJECTED_BY_POLICY`
- `FAILED`

Current MVP can map these outcomes to existing statuses:

- `PASSED` -> `PaperPublicationStatus.PUBLISHED`
- `NEEDS_REVIEW` -> `PaperPublicationStatus.SCREENING`
- `REJECTED_BY_POLICY` -> `PaperPublicationStatus.REJECTED`
- `FAILED` -> `PaperPublicationStatus.SCREENING`

### 5.2 Screening Failure Handling

If the AI service is unavailable:

- Keep the paper in `SCREENING`.
- Store an `AiScreeningResult` or future `AiScreeningLog`.
- Show the item in the admin queue.
- Do not publish automatically.

### 5.3 Screening Boundary

AI screening is not a quality score.

It should check:

- Basic completeness.
- Policy risk.
- Obvious spam or non-paper content.
- Subject area detection.
- Paper type detection.
- Possible integrity flags.

It should not determine final paper ranking or scholarly value.

## 6. Visibility Rules

Visibility must be centralized in a shared policy layer.

Recommended service:

`PaperAccessPolicy`

Recommended methods:

- `canViewPaper(user, paper)`
- `canViewPrivatePaper(user, paper)`
- `canAppearInFeed(paper)`
- `canEnterRanking(paper)`
- `canRatePaper(user, paper)`
- `canEditPaper(user, paper)`
- `canModeratePaper(user, paper)`

### 6.1 Public Feed Eligibility

A paper can appear in the public paper feed only when:

- `publicationStatus == PUBLISHED`

Excluded statuses:

- `DRAFT`
- `SCREENING`
- `NEEDS_REVISION`
- `REJECTED`
- `WITHDRAWN`
- `RETRACTED`

### 6.2 Public Detail Eligibility

Guests and normal readers can view a paper detail page only when:

- `publicationStatus == PUBLISHED`

Authors and admins can view non-public papers if they have permission.

MVP implementation may initially keep public detail restricted to `PUBLISHED` only, and add author/admin private detail later.

### 6.3 Ranking Eligibility

A paper can enter rankings only when:

- `publicationStatus == PUBLISHED`
- `ratingCount > 0`

Withdrawn and retracted papers must not appear in active rankings.

## 7. Rating Rules

### 7.1 Who Can Rate

A user can rate a paper only when:

- The user is logged in.
- The paper is `PUBLISHED`.
- The user is not the paper creator.
- The user is not a linked co-author.
- The user meets reader qualification rules.

MVP reader qualification:

- Any logged-in non-author user.

Future reader qualification:

- Approved `ReaderQualification`.

### 7.2 Who Cannot Rate

The following users cannot rate a paper:

- Guests.
- Paper creator.
- Linked co-authors.
- Users blocked or suspended by moderation.
- Users who do not meet qualification requirements.

### 7.3 Rating Dimensions

Current MVP dimensions:

- `overallScore`
- `innovationScore`
- `methodScore`
- `impactScore`
- `comment`

All numeric scores must be between 1 and 5.

### 7.4 One User, One Rating

Each user can have only one active rating per paper.

If the same user rates again:

- Update the existing rating.
- Do not create a second rating row.
- Recalculate the score snapshot.

### 7.5 Rating Visibility

MVP:

- Aggregated score is public.
- Individual rating comments can be shown later if moderation rules are ready.

Future:

- Rating comments may require abuse reporting and moderation.

## 8. Score Snapshot Rules

`PaperScoreSnapshot` must be updated whenever a valid rating is created or updated.

MVP update strategy:

- Recalculate synchronously in `PaperRatingService` after saving the rating.

Future update strategy:

- Publish an event after rating changes.
- Recalculate asynchronously.
- Use scheduled repair jobs for consistency.

### 8.1 Composite Score

MVP formula:

```text
compositeScore = average(overallScore, innovationScore, methodScore, impactScore)
```

Future formula may include:

- Reader qualification weight.
- Expert weight.
- Rating age.
- Abuse resistance.
- Minimum rating count threshold.

## 9. Ranking Rules

### 9.1 Paper Ranking

Paper rankings use `PaperScoreSnapshot`.

Eligibility:

- Paper is `PUBLISHED`.
- Rating count is greater than 0.

Sort order:

1. Composite score descending.
2. Rating count descending.
3. Published time descending.

### 9.2 Author Ranking

Author rankings are derived from published paper performance.

Eligibility:

- Include only `PUBLISHED` papers.
- Include only papers with at least one valid rating.
- Exclude withdrawn and retracted papers.

MVP calculation:

```text
authorScore = average(compositeScore of eligible papers)
```

Tie breakers:

1. Total rating count.
2. Paper count.
3. Author name.

### 9.3 Institution Ranking

Institution rankings are derived from published paper performance by affiliated authors.

Eligibility:

- Include only `PUBLISHED` papers.
- Include only papers with at least one valid rating.
- Exclude withdrawn and retracted papers.

MVP calculation:

```text
institutionScore = average(compositeScore of eligible papers)
```

Important future requirement:

- Add institution alias and merge logic before treating rankings as reliable.

### 9.4 Topic Ranking

Topic ranking is planned but not required for the current MVP.

Future signals:

- Average score by subject area.
- Number of published papers.
- Growth rate.
- Reader engagement.

## 10. Submission Flow

### 10.1 Draft Creation

The author creates a draft.

Required fields before final submission:

- Title.
- Abstract.
- Keywords.
- Subject area.
- Paper type.
- Full text or manuscript file metadata.
- At least one author.
- At least one corresponding author with email.
- Author affiliation and country or region when available.
- Declaration statements when applicable.

References are not required as a separate manual entry during MVP submission. The manuscript file remains the source of truth for references, and future extraction can parse references from the uploaded file or full text.

Authors do not enter a separate paper-level primary institution during submission. The system derives `PaperProfile.primaryInstitution` from the author list:

1. Use the first author's institution.
2. If the first author has no institution, use the first corresponding author's institution.
3. If neither is available, leave the primary institution empty.

### 10.2 Final Submission

When the author submits:

1. Create `Post`.
2. Create `PaperProfile`.
3. Create `PaperAuthor` rows.
4. Create or reuse `Institution` rows.
5. Derive `PaperProfile.primaryInstitution` from the submitted author affiliations.
6. Set `publicationStatus = SCREENING`.
7. Set `screeningStatus = SCREENING`.
8. Run AI screening.
9. Store `AiScreeningResult`.
10. If passed, set `publicationStatus = PUBLISHED`.
11. If published, set `publishedAt`.

### 10.3 Post and PaperProfile Relationship

Creation must be atomic.

If `Post` creation succeeds but `PaperProfile` creation fails, the transaction should roll back.

If `PaperProfile` creation succeeds but AI screening fails, the paper should remain in `SCREENING`.

## 11. Moderation Rules

### 11.1 Admin Queue

Admin should eventually have a paper management queue with:

- Screening failures.
- Papers requiring review.
- Reported papers.
- Withdrawn papers.
- Retracted papers.

### 11.2 Withdrawal

Authors can request withdrawal.

MVP option:

- Allow creator to mark `PUBLISHED -> WITHDRAWN`.

Future option:

- Require admin approval for published-paper withdrawal.

### 11.3 Retraction

Only admins can mark:

- `PUBLISHED -> RETRACTED`

Retraction must create an audit log entry.

### 11.4 Status Change Log

Future model:

`PaperStatusChangeLog`

Recommended fields:

- Paper.
- Previous status.
- New status.
- Changed by.
- Reason.
- Created timestamp.

## 12. Reader Qualification Rules

MVP:

- Any logged-in non-author user can rate.

Future:

Create `ReaderQualification`.

Recommended fields:

- User.
- Highest degree.
- Institution.
- Institutional email.
- Research field.
- Verification status.
- Verification evidence metadata.
- Approved by.
- Approved at.

Future rating policy:

- Only approved qualified readers can rate.
- Experts may have a separate rating layer or higher weight.

## 13. Missing Future Models

The current MVP has the basic paper and rating models. The following models are recommended for a more complete system:

- `ReaderQualification`
- `PaperModerationLog`
- `PaperStatusChangeLog`
- `AiScreeningLog`
- `PaperVersion`
- `InstitutionAlias`
- `ExpertProfile`
- `KnowledgeEntry`
- `RecommendationEvent`

These should not all be implemented at once. They should be added when the corresponding feature is being built.

## 14. Current MVP Implementation Scope

The current MVP should support:

- Submit paper.
- Run mock AI screening.
- Publish automatically when screening passes.
- Public paper feed.
- Paper detail page.
- Rating by logged-in non-author users.
- Score snapshot recalculation.
- Paper ranking.
- Author ranking.
- Institution ranking.
- Subject and score filters.

The current MVP should explicitly prevent:

- Authors rating their own papers.
- Unpublished papers entering public feed.
- Unpublished papers entering rankings.
- Unpublished papers receiving ratings.

## 15. Immediate Implementation Plan

The next implementation step should introduce a shared access policy.

### 15.1 Add PaperAccessPolicy

Methods:

- `canAppearInFeed(PaperProfile paper)`
- `canEnterRanking(PaperProfile paper)`
- `canRatePaper(User user, PaperProfile paper)`
- `isPaperAuthor(User user, PaperProfile paper)`

### 15.2 Apply Policy

Apply the policy to:

- `PaperService.listPublishedPapers`
- `PaperService.getPaper`
- `PaperRatingService.ratePaper`
- `PaperRankingService.listTopPapers`
- `PaperRankingService.listAuthorRankings`
- `PaperRankingService.listInstitutionRankings`

### 15.3 Add Tests

Required tests:

- Draft papers do not appear in feed.
- Screening papers do not appear in feed.
- Published papers appear in feed.
- Unpublished papers cannot be rated.
- Paper creator cannot rate their own paper.
- Linked co-author cannot rate their own paper.
- Rankings include only published papers with ratings.
