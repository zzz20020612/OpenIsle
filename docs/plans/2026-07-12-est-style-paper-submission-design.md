# EST-Style Paper Submission Design

## 1. Purpose

OpenIsle will replace the current six-step OJS-style paper form with a professional submission workspace whose interaction model closely follows the current ACS/Environmental Science & Technology submission experience.

The design copies the useful workflow and information architecture, not ACS or ES&T branding, logos, protected artwork, editorial review behavior, or journal-specific commercial information.

The public product remains an English academic paper community:

```text
submission draft
  -> author review and confirmation
  -> existing AI screening
  -> public paper record
  -> reader evaluation and discussion
```

## 2. Confirmed Scope

### Included

- Research Article and Review manuscript types.
- One continuous submission page with white content sections.
- A sticky right-side progress navigator that follows scrolling.
- Automatic draft saving and cross-session recovery.
- A separate author review page before final submission.
- Structured manuscript metadata rendered as HTML on the public paper page.
- A required DOCX manuscript source file, without DOCX-to-HTML parsing in this phase.
- Required Cover Letter and TOC Graphic.
- Multiple files with explicit file roles and descriptions.
- Multiple authors.
- Exactly one corresponding author.
- Multiple affiliations per author, with exactly one primary affiliation.
- Structured funding records.
- Online PDF preview for public Supporting Information.
- Existing AI screening, publication, rating, discussion, notification, and ranking behavior after final submission.

### Excluded

- Reviewer Suggestions.
- Editor Preferences.
- Special Issue Selection.
- Traditional editor assignment, peer review, revision, acceptance, and production workflows.
- DOCX, LaTeX, or PDF full-text parsing.
- Automatic HTML full-text generation.
- ACS/ES&T names, logos, covers, colors, impact factors, or other proprietary brand assets.

## 3. Reference Behavior

The design is informed by the official ES&T Author Guidelines and the ACS Publishing Center submission interface as reviewed on 2026-07-12:

- <https://researcher-resources.acs.org/publish/author_guidelines?coden=esthag>

Relevant workflow characteristics include separate manuscript metadata, required submission files, structured authors and institutions, structured funding information, declaration questions, a continuous submission workspace, and author confirmation before final submission.

## 4. Submission Workspace

### 4.1 Page Structure

The submission page is a continuous vertical form rather than a route-per-step wizard.

```text
Manuscript Type
File Upload
Manuscript Information
Author Information
Funding Information
Details & Comments
```

Each section is a white rectangular content panel on a quiet light-gray background. The visual treatment should be dense, formal, and operational, with restrained borders, small corner radii, clear required markers, and standard form controls.

The page uses OpenIsle branding and English UI copy.

### 4.2 Sticky Progress Navigator

The right column contains a vertical progress navigator:

```text
● Manuscript Type
○ File Upload
○ Manuscript Information
○ Author Information
○ Funding Information
○ Details & Comments
```

Behavior:

- The navigator uses a sticky position below the application header.
- `IntersectionObserver` determines the active section while the page scrolls.
- Clicking a node scrolls smoothly to its section.
- Active nodes use the primary accent color.
- Completed nodes display a filled or checked state.
- Invalid nodes display an error state.
- Incomplete nodes remain outlined.
- The active node must not change repeatedly when two section boundaries are both visible; use a stable top-offset rule.
- On mobile, replace the right rail with a compact sticky progress header or progress drawer.

### 4.3 Save State

The workspace always displays one of these states:

- `Saving...`
- `All changes saved`
- `Changes not saved`
- `Uploading file...`

Autosave is debounced approximately 800 milliseconds after the user stops editing. File uploads save independently from form autosave.

## 5. Submission Sections

### 5.1 Manuscript Type

Supported types:

- Research Article
- Review

Selecting a type changes the explanatory guidance but does not introduce a separate editorial workflow.

### 5.2 File Upload

Required files:

- Manuscript File: DOCX required in the current phase.
- Cover Letter: DOC, DOCX, PDF, RTF, or TXT.
- TOC Graphic: supported web image formats with configured size limits.

Other files may be uploaded in multiple formats. Each file must have a designation:

- Supporting Information
- Review Only
- PDF Version
- LaTeX Source
- Dataset
- Code
- Other

Each Other File stores:

- display name;
- original filename;
- MIME type;
- byte size;
- file role;
- public description;
- public/private visibility;
- display order;
- storage key and download URL metadata.

Rules:

- A public Supporting Information file requires a meaningful contents description.
- Cover Letter and Review Only files are private.
- PDF Supporting Information is previewable after publication.
- ZIP, CSV, XLSX, and other unsupported preview types remain downloadable.
- Upload failures are retried per file without clearing the rest of the form.

### 5.3 Manuscript Information

Fields:

- Manuscript Title, required.
- Abstract, required, with live word count.
- Section / Subject Area, required.
- Keywords, at least one required; recommend three to five without enforcing the recommendation.

Special Issue Selection is not included.

### 5.4 Author Information

Paper-level rules:

- At least one author is required.
- Exactly one corresponding author is required.
- The first author is the default corresponding author for a new draft.
- Selecting another corresponding author automatically clears the previous selection.
- Authors can be added, deleted, expanded, collapsed, and reordered.
- `Add Me as Author` pre-populates the current user's available identity data.
- Email lookup may match an existing OpenIsle user or ExpertProfile without requiring every coauthor to register.

Required author fields:

- Email.
- Given name.
- Family name.
- Author role.
- At least one affiliation.
- Exactly one primary affiliation.

Optional author fields:

- Middle name.
- ORCID.
- Co-first author.
- CRediT contribution roles.

Each author is displayed as an expandable card. The collapsed summary includes author order, full name, corresponding-author state, and affiliation summary.

### 5.5 Affiliations

Each author can add multiple affiliations through an affiliation dialog.

Required fields:

- Organization.
- Country / Region.
- City.

Optional fields:

- Department.
- Address lines.
- State / Province / Region.
- ZIP / Postal Code.

Affiliations can be reordered, edited, deleted, and marked as primary. The same normalized institution may be reused across authors while preserving an author-specific affiliation snapshot.

### 5.6 Funding Information

Funding is structured rather than stored only as free text.

Each record includes:

- Funder.
- Grant ID.

Authors can add multiple funding records or select `No funding was received`.

### 5.7 Details & Comments

Required submission declarations:

- Conflict of Interest.
- Data Availability.
- Ethics Statement or not-applicable reason.
- Preprint / Previous Public Posting.
- AI Tool Use Disclosure.
- All authors have agreed to submission.
- Originality and rights confirmation.

Optional private field:

- Comments to the Platform.

The public paper page may display Funding, Conflict of Interest, Data Availability, Ethics Statement, and AI Use Disclosure. Cover Letter, author contact details, detailed addresses, review-only files, and Comments to the Platform remain private.

## 6. Author Review Page

The primary submission-page action is `Continue to Review`, not final submission.

The separate `Review Your Submission` page renders a read-only HTML summary of:

- manuscript type;
- all files, roles, descriptions, and visibility;
- title, abstract, section, and keywords;
- ordered authors;
- corresponding-author marker;
- numbered affiliations;
- funding records;
- declarations and private comments.

Each section has an `Edit` action that returns to the submission workspace and scrolls to the corresponding section.

The review page has its own sticky navigator and a top-level validation summary such as:

```text
3 issues must be resolved before submission
```

Final confirmations:

- metadata matches the uploaded manuscript;
- all authors have agreed to submission;
- corresponding-author information is correct;
- public files and declarations may be displayed to readers.

Only after all validation succeeds can the author select `Confirm and Submit`.

## 7. Draft and Finalization Architecture

### 7.1 Draft Storage

Partial submissions must not create incomplete Post or PaperProfile records.

Recommended draft model:

```text
paper_submission_drafts
- id
- created_by
- manuscript_type
- form_data_json
- current_section
- status
- version
- created_at
- updated_at
```

Files use a separate draft-scoped table:

```text
paper_submission_files
- id
- draft_id
- file_name
- file_type
- file_size
- file_role
- description
- visibility
- storage_key
- sort_order
```

The JSON draft representation supports frequent partial updates. Final paper records remain normalized.

### 7.2 Finalization Flow

```text
create draft
  -> autosave fields
  -> upload and bind files
  -> server-side review validation
  -> author confirmation
  -> transactional finalization
  -> existing AI screening
  -> existing publication behavior
```

Transactional finalization creates or updates:

- Post with `PostType.PAPER`;
- PaperProfile;
- PaperAuthor records;
- PaperAuthorAffiliation records;
- Institution records or links;
- PaperFundingRecord records;
- final PaperFile records;
- existing screening records.

The draft is then locked and marked submitted. An idempotency key prevents duplicate finalization.

## 8. Required Data Model Changes

### 8.1 Author Affiliations

The current single `PaperAuthor.institution` relationship cannot represent multiple affiliations.

Add:

```text
PaperAuthor 1 -> N PaperAuthorAffiliation N -> 1 Institution
```

`PaperAuthorAffiliation` includes:

- paper author;
- institution;
- department and address snapshot fields;
- country, region, city, and postal code;
- primary flag;
- display order.

### 8.2 Funding Records

Add `PaperFundingRecord` with paper, funder name, grant ID, and display order. A generated funding statement may be retained for display compatibility.

### 8.3 Final File Records

Replace opaque manuscript/supplementary JSON blobs over time with normalized PaperFile records so visibility, preview, metrics, and access rules can be enforced per file.

## 9. Public Paper Detail Page

The public page follows a formal journal-article information hierarchy while retaining OpenIsle branding and community features.

### 9.1 Header

- Breadcrumb based on OpenIsle Papers, subject area, and manuscript type.
- Subject area and publication date.
- Article title.
- Ordered linked authors.
- Affiliation markers and full affiliation list.
- Corresponding-author marker and public corresponding email.
- Keywords and manuscript type.
- Cite, Share, Jump to, Expand, and Follow actions.
- Download Manuscript and Supporting Information actions.

### 9.2 Structured HTML Content

The following are rendered as HTML from submission metadata:

- Abstract.
- TOC Graphic.
- Keywords.
- Author Information.
- Funding Information.
- Data Availability.
- Conflict of Interest.
- Ethics Statement.
- AI Use Disclosure.
- Supporting Information descriptions.

The first phase does not parse or render manuscript full text. The manuscript DOCX and optional PDF version are provided as formal downloads.

### 9.3 Supporting Information Preview

The Supporting Information area contains:

- a public availability statement;
- file descriptions;
- file list and sizes;
- one active preview pane;
- view and download counts.

Use PDF.js for consistent PDF preview controls, including page navigation, zoom, fullscreen, and download. Multiple SI files switch within one preview pane. Unsupported formats remain downloadable.

Desktop may automatically open the first public SI PDF. Mobile loads the preview only after user action.

### 9.4 Right Rail

The sticky right rail may display:

- OpenIsle paper identity;
- platform paper identifier;
- publication date;
- license;
- views;
- downloads;
- rating count;
- discussion count;
- recommended papers.

Do not display fabricated impact factors, Altmetric scores, or citation counts.

### 9.5 Community Area

After the formal scholarly record:

- Reader Evaluation.
- Reader Discussion.
- Related Papers.

The existing Post, Comment, Reaction, Subscription, Notification, and PaperRating capabilities remain the implementation base.

## 10. Validation and Error Handling

Frontend validation provides immediate guidance. Backend validation is authoritative.

Core rules:

- supported manuscript type;
- required DOCX, Cover Letter, and TOC Graphic;
- at least one keyword;
- at least one author;
- exactly one corresponding author;
- required identity fields for every author;
- at least one affiliation and exactly one primary affiliation per author;
- required organization, country, and city for every affiliation;
- funding record or explicit no-funding selection;
- public SI descriptions;
- completed declarations and final confirmations.

Behavior:

- Continue to Review reports all issues and scrolls to the first invalid section.
- Field-level messages explain how to resolve each issue.
- File errors are isolated and retryable.
- Autosave retries transient failures and clearly reports unsaved changes.
- Draft version numbers prevent silent cross-tab overwrites.
- Final submission is idempotent.
- If existing AI screening fails, the finalized paper remains in SCREENING rather than being duplicated.

## 11. Security and Privacy

- Only the draft owner can read or modify a draft.
- Private file roles use private object-storage access.
- Signed URLs are short-lived and permission checked.
- Public SI becomes accessible only after the paper is public.
- HTML metadata and file descriptions are sanitized.
- Deleting a draft removes only files not referenced by a finalized paper.
- Corresponding-author email may be public; other author emails and all detailed addresses remain private.

## 12. Components

Recommended frontend ownership:

- `SubmissionWorkspace`
- `SubmissionScrollspy`
- `ManuscriptTypeSection`
- `SubmissionFileSection`
- `ManuscriptInformationSection`
- `AuthorInformationSection`
- `AuthorCard`
- `AffiliationDialog`
- `FundingInformationSection`
- `SubmissionDeclarationsSection`
- `SubmissionSaveStatus`
- `SubmissionReviewPage`
- `SupportingInformationViewer`
- public article metadata components

Submission state and autosave behavior should live in a dedicated composable rather than inside one large Vue page.

## 13. API Direction

Suggested resource-oriented endpoints:

```text
POST   /api/paper-submission-drafts
GET    /api/paper-submission-drafts/{draftId}
PATCH  /api/paper-submission-drafts/{draftId}
DELETE /api/paper-submission-drafts/{draftId}

POST   /api/paper-submission-drafts/{draftId}/files/presign
PATCH  /api/paper-submission-drafts/{draftId}/files/{fileId}
DELETE /api/paper-submission-drafts/{draftId}/files/{fileId}

POST   /api/paper-submission-drafts/{draftId}/validate
POST   /api/paper-submission-drafts/{draftId}/submit
```

Existing paper APIs continue serving finalized papers.

## 14. Verification Strategy

Backend tests:

- draft ownership and authorization;
- autosave version conflict behavior;
- file-role visibility rules;
- exactly one corresponding author;
- multiple affiliations and one primary affiliation;
- structured funding validation;
- transactional finalization;
- duplicate-submit idempotency;
- private file access denial.

Frontend tests:

- section completion and error states;
- scroll-driven active node changes;
- node click scrolling;
- autosave status and recovery;
- Add Me as Author;
- multiple authors and affiliations;
- corresponding-author reassignment;
- review-page Edit links;
- responsive layout.

End-to-end flow:

```text
sign in
  -> create draft
  -> upload required files
  -> enter metadata
  -> add multiple authors and affiliations
  -> autosave and reload
  -> review submission
  -> resolve validation errors
  -> confirm and submit
  -> AI screening
  -> public paper page
  -> preview SI PDF
```

## 15. Delivery Phases

1. Draft API and autosave foundation.
2. EST-style continuous submission workspace and scrollspy.
3. File roles, Cover Letter, TOC Graphic, and SI descriptions.
4. Multi-author and multi-affiliation data model.
5. Funding and declarations.
6. Author review and finalization transaction.
7. Public journal-style metadata page.
8. Supporting Information PDF viewer and metrics.
9. Full regression and responsive QA.

