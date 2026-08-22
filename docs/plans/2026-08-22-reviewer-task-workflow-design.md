# Reviewer task workflow design

## Scope

The first Scholar衡 governance increment implements three connected capabilities for existing literature:

1. authenticated users can discover and claim review tasks generated from complete literature records;
2. every claim requires a conflict-of-interest declaration and conflicted users are blocked;
3. submitting the existing six-dimensional rating completes the claimed task and updates reviewer points, level, credit, and eligibility.

Appeals, verified institutional identity, normalized cross-field rankings, and AI originality comparison remain later increments because they require governance staffing, external verification, substantially larger samples, or a vector-comparison pipeline.

## Domain model

`LiteratureReviewTask` represents one reviewer-paper assignment. It stores the literature paper identity and display metadata, assignee, status, claimed/due/completed timestamps, conflict declaration, and awarded points. A unique constraint prevents the same user from claiming the same paper twice.

`LiteratureReviewerProfile` stores one aggregate profile per user: points, completed/accepted/on-time counts, credit score, public level, and eligibility. New reviewers start at credit 75 (level B). A completed on-time task awards 20 points; a late task awards 10. Levels use the Scholar衡 credit bands (A >= 85, B >= 70, C >= 60, D below 60). V1 keeps the initial credit stable while exposing the data model needed for later full credit-formula calculation.

## Flow

The available-task endpoint reads complete literature records from the integrated literature service and excludes papers already rated or claimed by the current user. The claim request contains mandatory booleans for authorship, same institution, recent collaboration, advisor/student relationship, and other direct conflict. Any positive answer creates no task and returns a business error. A clean declaration atomically creates an accepted task with a seven-day deadline.

The existing literature rating transaction looks for an accepted task for that user and paper. When present, it marks it completed and updates the reviewer profile in the same transaction. Direct ratings remain supported so the already working rating flow stays backward compatible.

## UI

`/papers/review-tasks` provides Available, In progress, and Completed tabs plus a reviewer summary card. Claim opens an accessible conflict declaration modal. In-progress tasks link to the existing literature detail and rating form. The primary navigation gains a Review Tasks entry.

## Verification

Backend service tests cover clean claims, conflict blocking, duplicate prevention, completion, points, and profile aggregation. The frontend must pass the Nuxt production build. Final acceptance uses `user1` in Chrome to claim an available paper, submit a rating, observe task completion and points, and confirm the existing ranking/detail pages remain functional.
