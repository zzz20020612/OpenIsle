# Scholar衡 Source Integration Audit

## Source

- Package: `ScholarHeng-source-code-2026-08-09.zip`
- Size: 6,536,282 bytes
- SHA-256: `F0A9BBB531403EA66CB071FB20E666B56B4C3CE8201D1654625BAB55A013C9A5`
- Reviewed: 2026-08-09

The package is a React 19 / Next-compatible Vinext interaction prototype. Its README explicitly states that
paper data, reviewer identity, ratings, credit, appeals, and rankings are frontend demo data with no persistent
database or formal user system. The included Drizzle schema is empty.

## Product Capabilities Reviewed

- PDF reading workspace.
- AI originality evidence panel.
- Six-dimensional human evaluation.
- Written reader assessment and consensus display.
- Reviewer task/history/credit/appeals concepts.
- Field- and period-filtered scholar leaderboard.
- Confidence, sample-size, and governance explanations.

## Integrated Production Slice

The first real integration keeps the smallest complete and auditable slice:

- Six 1-5 dimensions: originality, rigor, evidence, significance, reproducibility, and clarity.
- Mandatory reading confirmation and 20-500 character assessment.
- One persistent rating per OpenIsle user and literature paper, with update behavior.
- Synchronous score snapshot recalculation.
- Public evaluation list and aggregate score on the literature detail page.
- Evaluated-paper and scholar rankings derived from real literature metadata.
- OpenIsle registration/JWT as the only user identity system.
- Existing literature service as the only source of imported paper metadata and extracted knowledge.

The prototype source itself is not copied into the Git history because its bundled demonstration PDF is marked
for controlled internal use. The original package remains the team-controlled source artifact; this repository
contains the integrated implementation and this reproducible source fingerprint.

## Deferred Prototype Concepts

The following screens are retained as product references, not presented as working production features:

- Reviewer task matching.
- Reviewer credit and qualification scoring.
- Consensus-deviation penalties.
- Appeal voting and governance workflow.
- Field normalization, time-window trends, and confidence shrinkage.
- AI originality matching against the full corpus.

These require verified author/account linkage, conflict-of-interest rules, moderation roles, audit logs, and
statistically defined ranking formulas before implementation.
