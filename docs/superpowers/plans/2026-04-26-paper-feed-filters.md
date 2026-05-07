# Paper Feed Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add subject filtering, minimum score filtering, and latest/score sorting to the public paper feed.

**Architecture:** The backend extends the paper feed API with query parameters and a small filter-options endpoint. The frontend adds a compact academic filter bar, syncs filter state to the URL, and reloads the feed from backend-filtered results.

**Tech Stack:** Spring Boot, JPA repositories, Nuxt 3, Vue Composition API, existing paper DTOs/services.

---

### Task 1: Add paper feed filter coverage in tests

**Files:**
- Modify: `backend/src/test/java/com/openisle/service/PaperServiceTest.java`

- [ ] Add a failing unit test for subject filter, minimum score filter, and score sorting in `PaperService`.

### Task 2: Extend backend feed and filter endpoints

**Files:**
- Modify: `backend/src/main/java/com/openisle/repository/PaperProfileRepository.java`
- Modify: `backend/src/main/java/com/openisle/service/PaperService.java`
- Modify: `backend/src/main/java/com/openisle/controller/PaperController.java`
- Create: `backend/src/main/java/com/openisle/dto/PaperFilterOptionsDto.java`

- [ ] Extend `GET /api/papers` with `subject`, `minScore`, and `sort`.
- [ ] Add `GET /api/papers/filters` for available subject areas.
- [ ] Keep implementation simple: repository handles published/subject fetch, service handles score filtering and score/latest ordering.

### Task 3: Add frontend filter bar and URL sync

**Files:**
- Modify: `frontend_nuxt/composables/paperApi.js`
- Modify: `frontend_nuxt/pages/papers/index.vue`
- Modify: `frontend_nuxt/assets/paper-platform.css`

- [ ] Add subject select, minimum score select, and sort select to `/papers`.
- [ ] Sync filter state to URL query parameters.
- [ ] Reload feed when filters change.

### Task 4: Verify build and tests

**Files:**
- Test only.

- [ ] Run backend paper tests.
- [ ] Run frontend build.
- [ ] Restart frontend container.
