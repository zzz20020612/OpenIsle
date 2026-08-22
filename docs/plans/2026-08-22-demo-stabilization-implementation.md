# Existing-literature demo stabilization implementation plan

## Phase 1: completeness contract

1. Define a machine-readable completeness result in `literature_system/code/search/api.py` containing stage,
   completeness, retryability, reason codes and evidence counts.
2. Derive status from the literature database's metadata, PDF/full-text, sections, knowledge card, methods and
   data-point records without duplicating the corpus.
3. Extend list and detail responses with this result while preserving existing fields.
4. Add focused Python tests for complete, retryable, terminal and incomplete records.

Verification:

```powershell
python -m pytest literature_system/tests -q
```

## Phase 2: stable batch runner and reporting

1. Add a demo runner under `literature_system/scripts/` that accepts topics, sources and a target complete count.
2. Reuse the existing collect/parse/extract functions and task status rather than implementing a second pipeline.
3. Continue collecting candidates until 30 complete papers exist or every configured bounded attempt is exhausted.
4. Retry retryable failures, retain terminal failures, and emit JSON plus Markdown reports.
5. Make the runner resumable and idempotent by querying persisted paper and job state.
6. Add unit tests with mocked upstream services and a temporary SQLite database.

Verification:

```powershell
python -m pytest literature_system/tests -q
python literature_system/scripts/demo_stabilization.py --help
```

## Phase 3: OpenIsle visibility

1. Proxy the expanded literature status through the existing Spring integration unchanged.
2. Update `frontend_nuxt/pages/literature/index.vue` to show complete, processing, retryable, incomplete and terminal
   states and provide an admin-only complete view/filter.
3. Update `frontend_nuxt/pages/literature/[id].vue` to explain missing artifacts and avoid empty panels.
4. Update `frontend_nuxt/pages/literature/workflow.vue` with complete/retryable/terminal totals and failure reasons.
5. Preserve current IDs, routes and public/read versus registered/download behavior.

Verification:

```powershell
cd frontend_nuxt
npm run build
```

## Phase 4: idempotent evaluation seed

1. Add a development-only Spring service/CLI entry point or script that calls the normal literature rating service.
2. Gate execution with an explicit demo environment flag.
3. Create 12 stable demo users across 4 institution domains without changing real accounts.
4. Select 5 complete literature IDs and create 10–12 deterministic, varied ratings for each.
5. Re-running updates existing `(literature_paper_id, rater_id)` rows.
6. Assert all selected papers become `FORMAL` and appear in paper and author rankings.
7. Add Java tests for idempotence, institution distribution and deterministic ranking output.

Verification:

```powershell
cd backend
mvn '-Dtest=LiteratureRatingServiceTest,*Demo*Test' test
```

## Phase 5: real corpus execution

1. Start Docker Desktop and the full development profile.
2. Run the batch runner against multiple open-literature topics.
3. Continue until 30 papers pass the completeness audit.
4. Inspect every failure class, fix product defects and retry recoverable items.
5. Run the rating seed against at least 5 complete papers.
6. Save the generated report under `docs/reports/` without committing secrets or downloaded PDFs.

Verification:

```powershell
docker compose --env-file .env --profile dev -f docker/docker-compose.yaml ps
```

Expected evidence:

- complete papers >= 30;
- visually sampled details >= 10;
- formal papers >= 5;
- paper rankings non-empty;
- author rankings non-empty; and
- every failure has a reason and retryability classification.

## Phase 6: end-to-end and persistence regression

1. Use Chrome to verify login, list, status filters, 10 detail pages, inline PDF, extraction panels, rating update and
   both ranking tabs.
2. Record visible defects and fix them before completion.
3. Restart the Compose stack without deleting volumes.
4. Recheck complete-paper count, extracted content, demo ratings and rankings.
5. Run final Python tests, focused Java tests and the Nuxt production build.
6. Update the demonstration report with final commands, counts and known external-source limitations.

## Completion gate

Do not declare completion unless all acceptance criteria in
`docs/plans/2026-08-22-demo-stabilization-design.md` have direct runtime or test evidence.
