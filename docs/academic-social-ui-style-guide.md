# Academic Social UI Style Guide

This document defines the visual and product direction for the OpenIsle paper platform pages. The goal is not to copy a single open-source project, but to combine academic credibility, knowledge-workspace clarity, and social evaluation energy.

## 1. Product Mood

The platform should feel like an academic knowledge network, not a journal website and not a generic forum.

Core impression:

- Serious enough for researchers to trust.
- Social enough for readers to rate, discuss, follow, and discover.
- Structured enough to support future paper database, expert database, and knowledge database features.
- Modern enough to feel like a next-generation research product.

Reference direction:

- Learn AFFiNE's knowledge-workspace feeling: pages, blocks, databases, and canvas-like organization.
- Learn Paperlib's paper-library clarity: metadata, tags, filters, rating, smart search, and clean list views.
- Learn OpenPrism's academic AI workspace: multi-panel layout, AI review reports, search panels, and quality checks.
- Use Nuxt/Vue-native patterns for implementation, but keep the final look unique to this platform.

## 2. What To Learn From AFFiNE

AFFiNE's most valuable idea is not a color palette. It is the idea that knowledge is built from reusable objects.

For this platform, a paper should not appear as a plain post. It should appear as a knowledge object with several blocks:

- Paper identity block: title, authors, institutions, subject, type, publication status.
- Evaluation block: community score, rating distribution, AI screening result, review signals.
- Knowledge block: methods, innovation points, contribution points, datasets, questions addressed.
- Social block: comments, reader reviews, bookmarks, follow actions.
- Discovery block: related papers, similar topics, expert connections, institution links.

AFFiNE-inspired design principles:

- Use a workspace layout rather than a flat article layout.
- Use blocks and panels to separate different kinds of information.
- Let users switch between views, such as feed view, ranking view, database view, and knowledge view.
- Keep the interface light, modular, and editable-feeling.
- Avoid heavy journal-style pages with long static text and little interaction.

UI translation for our pages:

- Paper detail page should become a "paper workspace".
- The right side should contain score, AI screening, author/institution, and action panels.
- The main content should be divided into blocks rather than one uninterrupted article body.
- Rankings should feel like a database view with filters and sortable signals.
- Future knowledge database pages should use block cards and relation maps, not only search results.

## 3. What To Learn From Paperlib

Paperlib is useful because it is focused on academic paper management.

Features to learn:

- Clean paper cards with title, authors, year, venue/subject, tags, rating, and notes.
- Metadata-first browsing.
- Smart filters for subjects, tags, authors, and paper status.
- Rating as a visible but controlled signal.
- Paper library density: enough information to compare papers quickly without visual noise.

UI translation for our pages:

- Feed cards should expose metadata clearly before social actions.
- Tags should be compact and searchable.
- Rating should be visible but not playful.
- The list page should support "Latest", "Top Rated", "Trending", and "By Subject".
- Paper cards should work like database records, not like blog cards.

## 4. What To Learn From OpenPrism

OpenPrism is useful because it shows how academic AI can sit inside a serious workspace.

Features to learn:

- Three-panel academic workspace.
- AI assistant / review report panel.
- Paper search and citation information.
- Quality check, consistency check, and missing citation report.
- Clear separation between editing, preview, and AI assistance.

UI translation for our pages:

- AI screening result should be shown as an explainable report, not a black-box label.
- Admin paper management should include an AI screening panel beside the paper metadata.
- Paper detail page can later include "AI Reading Guide" and "Knowledge Extraction" panels.
- The platform should visually communicate that AI assists discovery and evaluation, but does not replace human judgment.

## 5. Visual System

The visual system should be academic, quiet, and high-contrast, with a small amount of modern social-product energy.

Color tokens:

- Background: `#F7F5EF` warm paper, `#F4F7F6` pale research gray.
- Surface: `#FFFFFF` and `rgba(255,255,255,0.92)`.
- Ink: `#172033` deep academic navy.
- Muted text: `#667085`.
- Primary: `#145C5F` academic teal.
- Score positive: `#2F6B4F` research green.
- Ranking accent: `#B88A2B` muted gold.
- Risk accent: `#B54708` restrained amber/brown.
- Border: `rgba(23, 32, 51, 0.12)`.

Typography:

- Paper titles: serif or scholarly display style. Recommended web-safe fallback: `Georgia`, then later replace with `Source Serif 4`.
- UI text: neutral sans. Recommended later: `IBM Plex Sans` or `Source Sans 3`.
- Scores and rankings: compact, bold sans.
- Avoid playful rounded fonts.

Shape and spacing:

- Cards: 18-24px radius for main surfaces.
- Small pills: 999px radius.
- Borders should be visible but light.
- Shadows should be soft and low-opacity.
- Prefer generous vertical rhythm over cramped data tables.

Motion:

- Keep motion subtle.
- Use small hover elevation for paper cards.
- Use tab transitions and panel reveal animations only where helpful.
- Avoid entertainment-style animations.

## 6. Page-Level Direction

### 6.1 Paper Feed

Goal: "Academic social discovery feed".

Layout:

- Left/main column: paper cards.
- Right column: top papers, trending subjects, top institutions, platform explanation.
- Top area: concise product hero with search and ranking actions.

Paper card must include:

- Title.
- Abstract preview.
- Authors and primary institution.
- Subject and paper type.
- AI screening status.
- Composite score and rating count.
- Action area: read, rate, save, comment.

Design rule:

- Make paper identity and score visible before community noise.

### 6.2 Paper Detail

Goal: "Paper workspace".

Layout:

- Main column: title, abstract, full text, method/contribution blocks, discussion.
- Right sticky panel: score card, rating form, author/institution, AI screening, related papers.

Required blocks:

- Paper Overview.
- Evaluation Snapshot.
- Reader Ratings.
- AI Screening Report.
- Author and Institution.
- Knowledge Extraction placeholder.

Design rule:

- The page should feel like a paper object with metadata, evaluation, and knowledge connections.

### 6.3 Rankings

Goal: "Research reputation dashboard".

Views:

- Top Papers.
- Top Authors.
- Top Institutions.
- Future: Top Topics, Rising Papers, Most Discussed.

Design rule:

- Rankings should look like serious signals, not popularity contests.
- Include count and sample size near every score.
- Avoid overclaiming rank precision when data is small.

### 6.4 Admin Paper Management

Goal: "Platform operator workspace".

Layout:

- Table/database view for all papers.
- Status filters: Screening, Published, Rejected, Withdrawn, Retracted.
- Detail drawer or side panel for the selected paper.
- AI screening report shown beside manual actions.

Actions:

- Publish.
- Reject.
- Retract.
- Edit metadata.
- Adjust subject/type.
- View ratings and comments.

Design rule:

- Admin pages should be denser than public pages but still clean.
- Use database/workspace patterns inspired by AFFiNE and Nuxt UI, not raw HTML tables.

## 7. Component Rules

### Paper Card

Use for feed and related-paper sections.

Structure:

- Header: subject/type pills.
- Title.
- Abstract preview.
- Metadata row.
- Score row.
- Footer actions.

Avoid:

- Large thumbnails by default.
- Emoji-heavy decoration.
- Low-information social counters.

### Score Badge

Use for paper score and ranking score.

Structure:

- Large numeric score.
- Small label: "Composite Score".
- Rating count beside or below it.

Avoid:

- Star-only rating as the main signal.
- Bright yellow entertainment styling.

### AI Screening Panel

Use on detail and admin pages.

Structure:

- Decision: Passed / Needs Review / Rejected.
- Confidence.
- Subject/type prediction.
- Risk flags.
- Explanation.

Avoid:

- Only showing "AI Passed".
- Hiding reasons behind the AI result.

### Knowledge Block

Use for future knowledge database features.

Structure:

- Question addressed.
- Method.
- Innovation point.
- Contribution.
- Related concepts.

Design rule:

- These blocks should look like AFFiNE-style reusable knowledge objects.

## 8. Implementation Direction For This Repository

Current files to evolve:

- `frontend_nuxt/assets/paper-platform.css`
- `frontend_nuxt/pages/papers/index.vue`
- `frontend_nuxt/pages/papers/[id]/index.vue`
- `frontend_nuxt/pages/papers/rankings.vue`

Recommended next implementation order:

1. Refactor CSS tokens in `paper-platform.css`.
2. Upgrade `/papers` into a metadata-rich feed.
3. Upgrade `/papers/[id]` into a paper workspace with sticky side panels.
4. Upgrade `/papers/rankings` into a dashboard/database view.
5. Add `/admin/papers` after the public pages have a stable visual language.

Do not introduce a large UI framework yet. The current prototype should remain easy to change.

## 9. Sources Studied

- AFFiNE: https://github.com/toeverything/AFFiNE
- AFFiNE component package: https://github.com/toeverything/AFFiNE/tree/canary/packages/frontend/component
- Paperlib: https://github.com/Future-Scholars/paperlib
- OpenPrism: https://github.com/OpenDCAI/OpenPrism
- Nuxt UI: https://github.com/nuxt/ui
