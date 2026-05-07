# OJS-Inspired Paper Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the paper submission flow into a more mature OJS-inspired academic submission workflow while keeping OpenIsle as the primary platform.

**Architecture:** The backend remains a Spring Boot paper API that creates a Post plus PaperProfile in one transaction. The frontend remains a Nuxt paper workspace, but the submit page becomes a structured academic submission wizard with declarations, manuscript file records, structured contributors, references, and final review.

**Tech Stack:** Spring Boot, JPA/Hibernate, Nuxt 3, Vue Composition API, existing OpenIsle authentication and post service.

---

### Task 1: Extend Submission Data Model

**Files:**
- Modify: `backend/src/main/java/com/openisle/model/PaperProfile.java`
- Modify: `backend/src/main/java/com/openisle/dto/PaperSubmitRequest.java`
- Modify: `backend/src/main/java/com/openisle/dto/PaperDetailDto.java`
- Modify: `backend/src/main/java/com/openisle/dto/PaperSummaryDto.java`
- Modify: `backend/src/test/java/com/openisle/service/PaperServiceTest.java`

- [ ] Add paper-level fields for funding statement, conflict of interest, data availability, ethics statement, manuscript file records, and supplementary file records.
- [ ] Keep the MVP storage simple: serialize list-like file records as newline-delimited JSON strings in `PaperProfile` text columns.
- [ ] Update DTOs so paper detail returns these fields for the detail page and future admin review.
- [ ] Add/adjust test coverage so submission data round-trips through `PaperService.submitPaper()` and `PaperService.getPaper()`.

### Task 2: Remove Hard Dependency on Community Category and Tag IDs

**Files:**
- Modify: `backend/src/main/java/com/openisle/service/PaperService.java`
- Modify: `backend/src/test/java/com/openisle/service/PaperServiceTest.java`
- Modify: `frontend_nuxt/pages/papers/submit.vue`

- [ ] Add a backend fallback that resolves or creates a default `Papers` category/tag when the request does not provide valid category/tag IDs.
- [ ] Remove hardcoded `categoryId: 1` and `tagIds: [1]` from the frontend payload.
- [ ] Verify paper submission no longer depends on seed data using ID 1.

### Task 3: Upgrade Submit Page Wizard

**Files:**
- Modify: `frontend_nuxt/pages/papers/submit.vue`
- Modify: `frontend_nuxt/assets/paper-platform.css`
- Modify: `frontend_nuxt/composables/paperApi.js`

- [ ] Keep the six-step OJS-inspired wizard: Requirements, Manuscript, Metadata, Contributors, References & Declarations, Review.
- [ ] Replace the file upload placeholder with local file record controls for main manuscript, supplementary files, and datasets.
- [ ] Add declarations fields: funding statement, conflict of interest, data availability, ethics statement.
- [ ] Add step-level validation so Continue does not silently move past incomplete required steps.
- [ ] Preserve the current academic workspace visual direction: restrained typography, thin borders, compact panels, English UI only.

### Task 4: Verify Build and Core Tests

**Files:**
- Test only.

- [ ] Run backend paper tests: `docker compose -f docker/docker-compose.yaml --env-file .env exec springboot mvn '-Dtest=PaperServiceTest,PaperRatingServiceTest,PaperRankingServiceTest' test`.
- [ ] Run frontend build: `docker compose -f docker/docker-compose.yaml --env-file .env exec frontend_dev npm run build`.
- [ ] Restart frontend if needed: `docker compose -f docker/docker-compose.yaml --env-file .env restart frontend_dev`.
- [ ] Manually check `/papers/submit`, `/papers`, and a paper detail page.
