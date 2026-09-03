# Literature quality gates and resilient extraction

## Scope

This change improves three parts of the existing literature workflow without replacing its collection or PDF parser algorithms:

1. Separate usable knowledge from metadata-only and failed records.
2. Make LLM extraction tolerant of malformed aggregate responses and retry only failed parts.
3. Expose a stable five-level completeness model throughout the API and UI.

## Completeness model

- `L0 metadata`: bibliographic metadata exists, but no verified local PDF is available.
- `L1 pdf_ready`: a verified local PDF exists, but usable parsed full text does not.
- `L2 parsed`: readable full text and at least one non-empty section exist.
- `L3 knowledge`: L2 plus a knowledge card and methods record.
- `L4 evaluable`: L3 plus data-point extraction that either completed or was explicitly skipped as not applicable.

Figures are reported independently. A paper can be L4 without figures because not every paper contains them, but a parsed paper with no extracted visual material must expose that limitation rather than imply complete visual extraction.

## Knowledge-base admission

The default knowledge-base view returns L2-L4 records. It also exposes:

- `pending`: L0-L1, processing, and failed records;
- `all`: every non-placeholder record for administrators;
- exact completeness-level filtering.

No existing paper is deleted. Admission controls presentation and search scope only. Each result exposes its level, label, missing requirements, processing state, and whether visual content was extracted.

## Resilient LLM extraction

The original aggregate extraction remains the first attempt. Its successful response preserves the original algorithm and cost profile.

If aggregate JSON cannot be parsed or validated:

1. Apply bounded deterministic repair for common response wrappers, code fences, trailing text, and truncated closing delimiters.
2. If repair cannot produce a valid object, fall back to the existing independent knowledge-card, methods, and data-point extractors.
3. Persist every successful component immediately.
4. Record component-specific terminal state.
5. Retry only failed or missing components; never discard successful components because a sibling component failed.

An empty data-point list is successful only when extraction completed or the existing pre-check explicitly classifies data extraction as not applicable.

## UI behavior

The knowledge-base list defaults to usable knowledge and offers Usable knowledge, Pending processing, and All records views plus exact L0-L4 filtering. Cards and detail pages explain the current level, missing components, next action, and visual-extraction limitation.

The quality and jobs views retain reprocess/retry actions and show component-specific outcomes.

## Verification

- Unit tests cover all completeness levels and admission scopes.
- Extraction tests cover valid aggregate JSON, repairable JSON, unrecoverable aggregate output with component fallback, partial component failure, and selective retry.
- API tests prove default, pending, all, and exact-level filtering.
- Frontend tests/build prove filters and status rendering.
- Docker and Chrome regression verify a representative metadata-only record, parsed record, partial extraction, and L4 record.
