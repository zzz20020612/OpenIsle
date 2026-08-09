# Literature System Minimal Integration

## Goal

Expose the existing literature knowledge system inside OpenIsle as a public, read-only knowledge library without coupling it to the submission lifecycle or copying its database into OpenIsle.

## Data flow

```text
Browser -> OpenIsle /api/literature/** -> Literature System HTTP API -> Literature SQLite database
```

The browser never calls the literature service directly. OpenIsle only proxies an explicit allowlist of read operations and translates connection failures into a stable `503` response. Submission, screening, and paper publication continue to work when the literature service is offline.

## MVP surface

- Public literature list with text search and sorting.
- Public literature detail with metadata and abstract.
- Extracted knowledge card, methods, and data points.
- A navigation entry named `Knowledge Base`.
- Clear empty, loading, and unavailable states.

## API boundary

OpenIsle exposes:

- `GET /api/literature/health`
- `GET /api/literature/papers`
- `GET /api/literature/papers/{id}`
- `GET /api/literature/papers/{id}/knowledge`
- `GET /api/literature/papers/{id}/methods`
- `GET /api/literature/papers/{id}/data-points`

The upstream base URL is configured by `LITERATURE_API_BASE_URL` and defaults to `http://localhost:8088`.

## Explicit exclusions

- No synchronization into `PaperProfile` or submission records.
- No upstream collection, parsing, rebuilding, merging, or extraction commands.
- No manual rating/ranking integration in this increment.
- No PDF download proxy until the literature package provides a stable PDF identifier and access contract.

`quality_score` from the knowledge system is extraction quality, not a scholarly rating.
