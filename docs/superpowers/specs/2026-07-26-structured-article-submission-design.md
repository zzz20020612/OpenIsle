# Structured Article Submission Design

## 1. Goal

Extend the existing EST-inspired submission workflow with a separate structured article editor. Authors continue to upload the authoritative DOCX manuscript, while also preparing the online article as sections and typed content blocks. The finalized paper detail page renders a complete scholarly HTML article instead of treating the manuscript as a download-only file.

The first end-to-end acceptance case is the real manuscript in `D:\论文\paper01\paper_cnn1d`.

## 2. Scope

This feature includes:

- A dedicated article editor launched from the existing submission page.
- Structured sections and blocks for paragraphs, subheadings, figures, equations, and tables.
- Draft autosave and owner-only access consistent with the existing submission draft.
- A faithful author preview of the final public article layout.
- A readiness gate before the submission can proceed to final review.
- Finalization of structured draft content into an immutable published article snapshot.
- Full scholarly HTML rendering on the paper detail page.
- A real submitted and published example built from `paper01`.

This feature does not include:

- General-purpose collaborative editing.
- Automatic high-fidelity DOCX parsing in the first release.
- Automatic conversion of DOCX OMML equations.
- A peer-review or editor-assignment workflow.
- Versioned post-publication manuscript revisions.

## 3. Author Workflow

The existing submission form remains the primary workflow. A new `Article Content` section appears after `Manuscript Information`.

The section shows:

- An `Open Article Editor` command.
- Section, figure, table, and equation counts.
- Last saved time.
- `Not started`, `In progress`, or `Ready` status.

The complete flow is:

1. Select manuscript type.
2. Upload the required DOCX manuscript and cover letter.
3. Enter manuscript metadata.
4. Enter authors and affiliations.
5. Open the structured article editor.
6. Build sections and content blocks.
7. Preview the article in its final publication layout.
8. Mark the structured content as ready.
9. Complete funding and declarations.
10. Review the complete submission.
11. Submit, screen, and publish.

Changing structured content after it has been marked ready returns it to `In progress`. Final validation requires structured content to be ready.

## 4. Routes

```text
/papers/submit?draft={draftId}
/papers/submit/{draftId}/content
/papers/submit/{draftId}/content/preview
/papers/submit/{draftId}/review
/papers/{paperId}
```

All draft article routes require authentication and ownership of the submission draft.

## 5. Editor Experience

The editor uses a quiet three-pane knowledge-workspace layout:

- Left: ordered article outline.
- Center: blocks for the selected section.
- Right: properties for the selected block and article status.

The outline supports sections up to three levels deep, ordering, renaming, and deletion. A deletion that contains content requires confirmation.

The center pane supports these commands:

- Add paragraph.
- Add subheading.
- Add figure.
- Add equation.
- Add table.
- Move block up or down.
- Remove block.

The editor is an operational research tool, not a decorative card layout. Controls use icons where familiar symbols exist and include tooltips.

## 6. Content Model

### 6.1 Draft Article

`PaperDraftArticle` belongs one-to-one to `PaperSubmissionDraft` and stores:

- Status: `NOT_STARTED`, `IN_PROGRESS`, or `READY`.
- Version for optimistic concurrency.
- Last ready timestamp.
- Created and updated timestamps.

### 6.2 Draft Sections

`PaperDraftSection` stores:

- Draft article.
- Stable client key.
- Parent section when nested.
- Heading.
- Level from 1 to 3.
- Display order.

### 6.3 Draft Content Blocks

`PaperDraftContentBlock` stores:

- Section.
- Block type.
- Display order.
- Type-specific JSON payload.
- Created and updated timestamps.

Supported block types:

- `PARAGRAPH`
- `SUBHEADING`
- `FIGURE`
- `EQUATION`
- `TABLE`

Payload contracts:

```json
{
  "type": "PARAGRAPH",
  "text": "Markdown-compatible paragraph text with $inline math$."
}
```

```json
{
  "type": "FIGURE",
  "fileId": 41,
  "label": "fig-model-architecture",
  "caption": "Schematic diagram of the model architecture.",
  "altText": "Diagram of a one-dimensional CNN with Softmax normalization."
}
```

```json
{
  "type": "EQUATION",
  "latex": "X_{ij}=\\frac{V_{ij}}{\\sum_{i,j}V_{ij}}",
  "label": "eq-normalization",
  "numbered": true
}
```

```json
{
  "type": "TABLE",
  "label": "table-model-performance",
  "caption": "Model performance by pollutant.",
  "columns": ["Pollutant", "R2", "RMSE"],
  "rows": [["COD", "0.98", "0.020"]],
  "notes": "Values refer to the independent test set."
}
```

### 6.4 Final Article Snapshot

Final submission creates `PaperArticle`, `PaperSection`, and `PaperContentBlock` records linked to `PaperProfile`. These are copied from the validated draft inside the existing final-submission transaction.

Published pages never read mutable draft records. The linked `Post` continues to own comments, reactions, subscriptions, notifications, and moderation. The structured article owns scholarly body content.

## 7. Files and Images

The manuscript DOCX remains authoritative source material and is retained as a normalized `PaperFile`.

Figure uploads use draft-scoped file records and the existing private upload infrastructure. A new `FIGURE` file role is introduced. Figure files become public only when the paper is published and the corresponding figure block is finalized.

Accepted figure formats for the first release are PNG, JPEG, and WebP. TIFF files from `paper01` are converted to PNG before upload for browser compatibility. The original DOCX remains available for archival fidelity.

Each figure requires a caption and alt text before the article can be marked ready.

## 8. Mathematics and References

Paragraph blocks support inline LaTeX delimited by `$...$`. Equation blocks store display LaTeX and render through KaTeX in both preview and the public detail page.

Numbered equations receive stable sequential numbers at render time. Labels allow future cross-reference tooling without tying identity to display order.

The first release stores references as an ordered list already supported by `PaperProfile`. The article preview and detail page render that list as a formal References section. Citation-key resolution from BibTeX is outside this first implementation, but the `paper01` import fixture may transform its existing rendered references into the ordered list.

## 9. Preview and Readiness

Preview renders the same shared article components used by the public paper page. It includes:

- Paper title and type.
- Authors and affiliations.
- Abstract and keywords.
- Article outline.
- Structured sections and blocks.
- Figures and captions.
- Equations and numbers.
- Tables and notes.
- References.
- Supporting Information metadata.

`Mark Content as Ready` runs server validation. Validation requires:

- At least one section.
- At least one non-empty paragraph block.
- Valid section hierarchy and ordering.
- Non-empty LaTeX for each equation.
- Caption, alt text, and uploaded file for every figure.
- Caption and at least one cell for every table.
- No pending or failed referenced uploads.

Validation issues identify the section and block so the editor can navigate directly to the problem.

## 10. APIs

```text
GET    /api/paper-submission-drafts/{draftId}/article
PUT    /api/paper-submission-drafts/{draftId}/article
POST   /api/paper-submission-drafts/{draftId}/article/validate
POST   /api/paper-submission-drafts/{draftId}/article/ready
POST   /api/paper-submission-drafts/{draftId}/article/reopen
GET    /api/papers/{paperId}/article
```

The draft update API uses optimistic version checking and returns HTTP 409 for stale versions. The article payload is saved as one aggregate in the first release to keep ordering atomic and simplify autosave.

## 11. Security and Rendering

- Draft article endpoints require the authenticated draft owner.
- Public article endpoints follow `PaperAccessPolicy` visibility rules.
- Markdown is rendered server-side or through a constrained renderer.
- Generated HTML is sanitized with an explicit Jsoup allowlist.
- Raw user HTML, scripts, event handlers, iframes, and arbitrary URLs are rejected.
- KaTeX receives only stored LaTeX text and does not enable unsafe trust options.
- Figure access uses the existing paper file authorization service.

## 12. Error Handling

- Autosave network failures keep local edits dirty and show a retryable message.
- Version conflicts offer reload instead of silently overwriting another session.
- Failed figure uploads remain visible with retry and remove actions.
- Invalid equations show the LaTeX error beside the block without crashing the article preview.
- Final submission remains transactional; a failed article snapshot rolls back the linked `Post` and `PaperProfile` creation.

## 13. Real `paper01` Acceptance Case

The demonstration submission uses:

- `paper_cnn1d_ai.docx` as the manuscript.
- The title, abstract, keywords, authors, affiliations, funding, declarations, and CRediT roles from `paper_cnn1d_ai.qmd`.
- The manuscript's Introduction, Materials and Methods, Results, Discussion, Conclusions, Acknowledgements, and References as sections.
- Figures 1 through 8 from `images/media/image1.jpg` through `image8.jpg`.
- Equations from the manuscript as LaTeX equation blocks.
- `si.docx` as Supporting Information.
- `abstract.png` as the optional TOC graphic.

Acceptance requires completing the workflow through the real UI and producing a published paper detail page that:

- Displays the complete structured article in HTML.
- Places all eight figures in their intended sections with captions.
- Renders equations clearly with stable numbering.
- Shows tables without horizontal page breakage.
- Shows formal authors and affiliations.
- Shows references and Supporting Information.
- Retains DOCX download.
- Supports rating, comments, and following through the linked OpenIsle post.
- Works at desktop and mobile widths without incoherent overlap.

## 14. Verification

Backend verification covers:

- Owner-only draft article access.
- Optimistic locking.
- Readiness validation.
- Figure ownership and upload status.
- Transactional finalization.
- Public visibility policy.

Frontend verification covers:

- Editor autosave and conflict states.
- Section and block ordering.
- Figure, equation, and table editing.
- Preview parity with the public detail renderer.
- Desktop and mobile layout.

The final end-to-end check submits the `paper01` fixture through the running local stack and opens the resulting published detail page.
