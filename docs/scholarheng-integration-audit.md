# Existing-literature and Scholar衡 integration audit

## Accepted test scope

The integrated test corpus is the first teammate's online-collected existing literature. OpenIsle submission
drafts and submitted manuscripts remain a separate domain and are deliberately excluded from this evaluation
test. A local-PDF import screen is not required for the accepted workflow.

## Data ownership and identity

- Existing literature metadata, downloaded open PDFs, parsed full text, sections, knowledge cards, methods and
  data points are stored by `literature-system` in the `literature-data` Docker volume. The runtime database is
  `/app/data/literature.db` and PDFs are under `/app/data/pdfs`.
- OpenIsle users, literature ratings and score snapshots are stored in the OpenIsle MySQL volume.
- `papers.id` from the literature database is the stable cross-system identity. It is stored as
  `literature_ratings.literature_paper_id` and `literature_score_snapshots.literature_paper_id`.
- Before accepting a rating, OpenIsle calls the literature service to verify that this paper ID exists.
- Ranking rows use the same ID to retrieve current title, author and journal metadata and link back to
  `/literature/{paperId}`. No duplicate paper record is created in MySQL.

## Completed functional chain

1. Search online metadata through Crossref, arXiv, PMC, OpenAlex, Semantic Scholar or PubMed. An `all_open`
   option runs all open sources; WoS and Scopus remain available when their own API keys are configured.
2. Deduplicate and upsert metadata. Previously collected matches continue into downstream stages instead of
   incorrectly ending the one-click task with zero new rows.
3. Locate and download an available open PDF, then parse full text, sections, figures and references.
4. Extract a knowledge card, methods and data points with the configured DeepSeek-compatible LLM. Optional
   embeddings are skipped transparently when no embedding key is configured.
5. Display the same paper and extracted artifacts through the OpenIsle literature detail page.
6. Let a registered OpenIsle user submit one updateable, written, read-confirmed six-dimensional evaluation.
7. Recalculate Scholar衡 score status and expose formal paper/author rankings.

## Implemented Scholar衡 core rules

- Six dimensions use a 0-5 scale: originality 25%, rigor 20%, evidence 20%, significance 15%,
  reproducibility 10%, and clarity 10%.
- A written assessment of 20-500 characters and reading confirmation are mandatory.
- Public evaluator names are pseudonymized; the evaluator can still retrieve their own rating.
- Bayesian shrinkage uses prior mean 3.5, and score snapshots record the rule version.
- Fewer than five ratings are `INITIAL` and do not expose a single aggregate score.
- A paper becomes formally rankable only with at least 10 ratings, effective sample size at least 8, at least
  three institution proxies and no institution contributing more than 40% of ratings. Other evaluated papers
  remain `PROVISIONAL`.

## Runtime evidence (2026-08-21)

- A real arXiv query collected literature paper `13` online.
- Its open PDF was downloaded and parsed into 4 pages, 14,628 full-text characters and 8 sections.
- DeepSeek extraction produced a knowledge card, a methods record and numerical data points.
- OpenIsle `user1` logged in, read paper `13` through the OpenIsle bridge and saved rating `2` against
  `literaturePaperId=13` under rule `SCHOLARHENG-1.0`.
- The paper reports processing status `extracted`; with one evaluator its correct score status is `INITIAL`.

## Separate submission domain

OpenIsle submission metadata lives in MySQL (`paper_submission_*`, `paper_profiles` and related tables), while
uploaded manuscript files are stored under the configured OpenIsle upload directory. Submission-paper ratings
remain separate and are not part of this existing-literature test or ranking.

## Optional or later governance work

The source prototype's reviewer task matching, reviewer credit/qualification, appeals, conflict-of-interest
governance, and cross-field/time normalization are not required for this first end-to-end test. They need
additional product rules and verified institution/account data. Semantic/vector search additionally requires an
embedding key; keyword search and the complete accepted workflow do not.
