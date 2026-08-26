# Complete Literature Workspace Implementation Plan

## Phase 1: Inventory and contracts

- Enumerate every route and control in `literature_system/frontend/static/js/api.js` and `app.js`.
- Map each function to its Python endpoint, Spring proxy allow-list entry, Nuxt route, and verification case.
- Identify response shapes and preserve compatibility with empty and partial records.

## Phase 2: Shared workspace

- Add reusable literature administration navigation, status summaries, task progress, error notices, pagination, and typed form components.
- Replace the existing raw-JSON advanced operation control.
- Preserve the current institutional visual language and responsive behavior.

## Phase 3: Public research parity

- Complete all search modes and result categories.
- Complete paper sections, figures, citations, authors, and similar-paper views.
- Add author, collaboration, institution, timeline, metric, and graph diagnostic views.

## Phase 4: Processing parity

- Add typed collection, complete-pipeline, parse, extract, sync, and rebuild forms.
- Add detailed job filters, pagination, results, archive, retry, and live progress.
- Add completeness and stage statistics.

## Phase 5: Quality and governance parity

- Add quality dashboard, low-quality records, error breakdowns, prompt comparison, and re-extraction.
- Add duplicate-author inspection and merge.
- Add service diagnostics and typed workflow settings.

## Phase 6: Verification

- Add or update frontend and backend tests for routing, permissions, proxy allow-lists, and response handling.
- Run `python -m pytest`, `mvn test`, and `npm run build` in their relevant modules.
- Run the Docker stack and exercise the complete open-literature pipeline in Chrome with administrator and ordinary-user accounts.
- Update the parity matrix with pass/fail evidence and document remaining upstream limitations separately from integration defects.

