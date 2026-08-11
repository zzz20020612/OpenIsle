# Literature Full Integration and PDF Submission Design

## Goal

Complete the functional integration of the existing Literature System into OpenIsle before visual redesign,
while adding PDF as an authoritative manuscript format in the existing author submission workflow.

The Scholar衡 evaluation work is explicitly out of scope for this increment. The existing OpenIsle LLM
configuration remains the knowledge-extraction provider. Embedding functionality is implemented and exposed,
but remains disabled until `EMBEDDING_API_KEY` is supplied.

## Product Boundary

OpenIsle remains authoritative for:

- Registration, JWT authentication, roles, and admin authorization.
- Public navigation and user-facing literature pages.
- Submission drafts, files, structured article editing, final submission, and screening.
- Audit records for literature-administration actions initiated by OpenIsle users.

The Literature System remains authoritative for:

- Existing-literature metadata and processing status.
- Open-PDF acquisition and local PDF storage.
- PDF parsing, sections, figures, references, and citation data.
- LLM knowledge cards, methods, data points, and extraction quality.
- FTS5, sqlite-vec, hybrid retrieval, graphs, author resolution, and workflow jobs.

No literature metadata, PDF, full text, embedding, or graph data is copied into OpenIsle MySQL.

## Integration Architecture

```text
Browser
  -> OpenIsle Nuxt pages
  -> OpenIsle Spring Boot /api/literature/**
       -> public allowlisted reads
       -> ADMIN-only workflow operations + audit
  -> Literature System service
       -> SQLite + FTS5 + sqlite-vec
       -> PDF storage
       -> collection / parsing / extraction jobs
```

The Literature System port is not a trusted public API. Mutating and sensitive workflow endpoints require an
internal service token. Browser clients reach those operations only through authenticated OpenIsle admin APIs.

## Complete Literature Capability Map

### Public registered product surface

- Corpus list with paging, field filters, facets, and sorting.
- Keyword, vector, and hybrid search with explicit unavailable states when embeddings are not configured.
- Search tabs for papers, knowledge cards, methods, and data points.
- Literature detail with metadata, abstract, knowledge, methods, data points, authors, citations, similar papers,
  parsing provenance, and processing status.
- Author list, author detail, author papers, and collaboration network.
- Institution collaboration network.
- Corpus relationship graph and diagnostics.
- Timeline and cross-paper metric comparison.
- Controlled PDF inline viewing for public/open files.
- PDF download only for authenticated OpenIsle users.

Public pages use stable OpenIsle endpoints. They do not call port `8088` directly.

### Admin workflow surface

- Corpus and processing statistics.
- Metadata collection.
- PDF download and parsing.
- Knowledge extraction.
- Full pipeline execution.
- Job list, job statistics, progress, retry, and archive.
- Search-index rebuild and single-paper synchronization.
- Workflow settings and connection tests.
- Extraction-quality statistics, low-quality records, prompt comparison, and re-extraction.
- Author merge.
- Visibility control for public corpus records.

Every mutating admin action records username, operation, target, sanitized request parameters, outcome,
upstream status, request ID, client IP, and Beijing-local timestamps. API keys and secrets are never audited.

## Literature Processing and Visibility

Processing and public visibility are separate concerns.

Processing states:

```text
COLLECTED -> PDF_READY -> PARSED -> EXTRACTED
                         \-> FAILED
```

Visibility states:

```text
PRIVATE | PUBLIC | HIDDEN
```

- Newly collected records default to `PRIVATE`.
- A successful full pipeline may promote a record to `PUBLIC` only when required metadata and at least one
  useful extracted knowledge artifact exist.
- Admins may publish, hide, or return a record to private processing state.
- Public list/search/detail endpoints return only `PUBLIC` non-placeholder records.
- Admin endpoints can inspect every state.
- Existing valid extracted demo records are backfilled to `PUBLIC`; incomplete records remain `PRIVATE`.

Job timestamps are serialized with an explicit timezone and displayed in `Asia/Shanghai`. Intermediate parser
attempts are grouped under their parent workflow execution so a recovered fallback is not presented as a final
failure.

## Embedding and Retrieval

The existing implementation remains authoritative:

- `Qwen/Qwen3-Embedding-4B` through an OpenAI-compatible embeddings API.
- Embeddings stored in `paper_embeddings` and queried through `sqlite-vec`.
- Chunk types: abstract, section, claim, method, and data point.
- FTS5 keyword search, pure vector search, and weighted hybrid search.

This increment adds:

- Safe configuration reporting that reveals provider/model/readiness but never a key.
- Admin reindex and single-paper embedding operations.
- Clear `EMBEDDING_NOT_CONFIGURED` responses while the key is absent.
- No silent fake vectors and no fallback to the text-generation model.

## PDF Access

The Literature System exposes PDF metadata and streams only files located inside its configured PDF directory.
OpenIsle proxies the stream and applies access policy:

- Metadata, knowledge, and PDF availability are public for `PUBLIC` records.
- Inline PDF viewing is allowed for public/open PDFs.
- Download requires an authenticated OpenIsle user.
- Private, hidden, missing, non-open, and path-traversal targets are rejected.
- Response headers use sanitized filenames and correct content types.

## PDF Manuscript Submission

The existing draft and article-editor model is retained.

Accepted authoritative manuscript formats become:

- DOCX
- PDF

Exactly one `MANUSCRIPT` file remains required. DOCX and PDF are alternatives, not two required files.

### PDF import flow

```text
Author uploads PDF manuscript
  -> existing draft-scoped file upload and validation
  -> author opens Article Content
  -> PDF importer extracts page text and layout cues
  -> headings and paragraphs become editable article sections/blocks
  -> title/abstract candidates are offered without overwriting confirmed metadata
  -> author edits and previews the structured article
  -> final review validates article readiness
  -> original PDF remains the authoritative archived manuscript file
```

PDF parsing is deterministic and local. The LLM is not allowed to silently rewrite the manuscript. For digital
PDFs, PDF.js extracts text and page structure in the browser. If extraction yields insufficient text, the file is
classified as scanned/image-only. The existing article remains unchanged and the author receives a recoverable
message to upload a text-searchable PDF or DOCX. OCR is not claimed without a configured OCR-capable parser.

PDF import initially preserves paragraphs and inferred headings. Figures, formulas, and complex tables may be
represented imperfectly; the author editor and preview are the correction boundary. Parsing errors never delete
the uploaded manuscript or overwrite a previously saved structured article.

## API Direction

Public endpoints remain under `/api/literature/**`. New read families include:

- `/search`, `/search/vector`, `/search/hybrid`
- `/papers/{id}/similar`, `/citations`, `/authors`, `/pdf`, `/pdf/download`
- `/knowledge`, `/methods`, `/data-points`, `/timeline`, `/metrics/compare`
- `/authors`, `/authors/{id}`, `/authors/{id}/papers`, `/authors/{id}/network`
- `/institutions/network`, `/graph`, `/graph/diagnostics`

Admin endpoints remain under `/api/literature/admin/**` and require `ADMIN` authority. The controller uses an
explicit upstream allowlist rather than an unrestricted open proxy.

## Failure Handling

- Literature service unavailable: stable `503` without affecting submission or screening.
- Upstream invalid response: stable `502` with request ID.
- Embedding key missing: `503 EMBEDDING_NOT_CONFIGURED`; keyword search remains available.
- No PDF: metadata remains readable; view/download controls are unavailable.
- PDF parse insufficient: keep existing article unchanged and explain how the author can recover.
- Admin job failure: audit outcome and expose retry; never report an intermediate failure as final success.

## Verification

- Literature Python unit tests for visibility, PDF path safety, auth-token enforcement, embedding readiness, and
  processing status transitions.
- Spring controller/service tests for public allowlists, ADMIN-only operations, audit redaction, PDF view/download,
  and upstream failures.
- Nuxt reader tests for PDF article conversion and failure recovery.
- Backend targeted tests plus full `mvn test` baseline report.
- Frontend `npm run build` and reader tests.
- Docker health checks.
- Chrome acceptance for admin workflow, public search/detail/PDF, registered download, DOCX regression, and PDF
  manuscript import/edit/preview/final submission.

## Delivery Sequence

1. Secure and audit workflow operations.
2. Add processing/visibility states and public publishing boundary.
3. Expose complete public and admin API families.
4. Add PDF view/download policy.
5. Add public advanced-search, graph, author, institution, and detail capabilities.
6. Add embedding readiness and rebuild controls; leave only the external key pending.
7. Add PDF manuscript upload and structured article import.
8. Run tests and Chrome end-to-end acceptance.

