# Complete Literature Workspace Design

## Objective

Reproduce every business function present in the first teammate's literature system inside the OpenIsle user interface. OpenIsle remains the single public application for navigation, authentication, authorization, scoring, and auditing. The existing Python literature service remains the internal engine for collection, PDF retrieval and parsing, LLM extraction, search, and graph computation.

Functional parity is required; visual parity is not. All new pages use the current UN-inspired institutional interface.

## Architecture

1. The Nuxt frontend renders every public and administrative literature workflow.
2. The Spring Boot backend exposes an allow-listed proxy, applies OpenIsle roles, and audits administrative mutations.
3. The Python service retains its algorithms, processing jobs, search engine, and SQLite corpus.
4. OpenIsle MySQL retains users, ratings, rankings, review tasks, and audit records.
5. Long-running operations return task identifiers and are polled until completion or failure.

The Python service is not exposed directly to browsers. Secrets are never returned to the frontend; settings expose configured/unconfigured state only.

## Functional parity inventory

### Discovery and corpus

- Dashboard and corpus statistics
- Paper browsing and advanced metadata filters
- Keyword, vector, and hybrid search
- Separate paper, knowledge-card, method, and data-point results
- Paper metadata, abstract, sections, figures, citations, authors, knowledge, methods, and data points
- Similar-paper recommendations
- Authors, author papers, collaboration networks, and institution networks
- Knowledge graph, graph diagnostics, timeline, and metric comparison

### Processing administration

- Online metadata collection from every source supported by the engine
- Open-PDF retrieval, parsing, and LLM extraction
- Complete pipeline and individually executable stages
- Single-paper synchronization
- Search-index rebuild
- Live task progress, job history, filtering, pagination, details, archive, and retry
- Completeness totals and stage-level outcomes

### Quality and governance

- Quality statistics and low-quality record filters
- Missing-field and extraction-error breakdowns
- Prompt-version comparison
- One-paper re-extraction
- Duplicate-author comparison and merge
- Service diagnostics for the engine, LLM, embeddings, sources, PDF retrieval, index, and graph
- Workflow settings through typed forms instead of raw JSON

### OpenIsle-only integration

- Registered-user PDF download
- Human ratings, review tasks, and paper/author rankings
- Administrative role checks and mutation audit trail
- Submission PDF parsing may reuse the engine but submission records never enter the collected-literature corpus

## Information architecture

The literature area is divided into public research pages and administrator pages:

- `/literature`: corpus browser
- `/literature/explore`: search, graph, timeline, metrics, authors, and institutions
- `/literature/[id]`: complete paper record
- `/literature/workflow`: administrator overview
- `/literature/workflow/process`: collection and processing
- `/literature/workflow/jobs`: task history
- `/literature/workflow/quality`: quality management
- `/literature/workflow/authors`: author governance
- `/literature/workflow/diagnostics`: service diagnostics
- `/literature/workflow/settings`: workflow settings

Shared administration navigation keeps these pages discoverable. Ordinary users can browse public research pages but cannot see or invoke mutation controls.

## Interaction and errors

- Every engine operation uses a labelled form with validation; administrators never enter raw JSON.
- Long tasks show stage, percentage, counts, warnings, and the failing record where available.
- Partial completion is distinct from success and failure.
- Unavailable services name the failing dependency and preserve retryable work.
- Records without an open PDF remain searchable as metadata-only records and are marked accordingly.
- Settings save only supported keys and display masked configuration state.

## Verification

1. Maintain a source-to-OpenIsle parity matrix covering every original route and control.
2. Run Python tests, Spring Boot tests, and the Nuxt production build.
3. Start the complete Docker composition and verify health checks and persistent volumes.
4. In Chrome, collect several open papers and verify metadata, PDF, parsing, extraction, search, graph, quality, retry, ratings, and rankings.
5. Verify ordinary-user and administrator permission boundaries separately.

## Delivery order

1. Parity matrix and shared administration shell.
2. Missing proxy/API adaptations.
3. Dashboard, discovery, paper, author, and graph parity.
4. Processing and job management parity.
5. Quality, author governance, diagnostics, and settings parity.
6. Automated verification, Docker regression, and Chrome acceptance test.

