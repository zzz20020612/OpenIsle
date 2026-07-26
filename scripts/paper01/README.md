# paper01 submission fixture

This fixture converts the real DOCX manuscript into the same structured payload used by the submission UI. It does not modify the source paper or delete the submitted demo record after verification.

## Build

```powershell
node scripts/paper01/build-paper01-submission.mjs
```

Optional source and output directories:

```powershell
node scripts/paper01/build-paper01-submission.mjs "D:\论文\paper01\paper_cnn1d" "D:\OpenIsle\scripts\paper01\generated"
```

The command uses Quarto's bundled Pandoc parser so headings, citations, inline math, display equations, figures, and tables come from the uploaded DOCX AST rather than fragile text matching. The QMD file supplies fixture metadata only, standing in for title, author, abstract, and keyword fields entered by the author in the UI.

## File mapping

| Submission role | Source |
| --- | --- |
| Manuscript | `paper_cnn1d_ai.docx` |
| Cover Letter | Generated from manuscript metadata |
| Supporting Information | `si.docx` |
| TOC Graphic | `images/media/abstract.png` |
| Article Figures | Every image referenced by `paper_cnn1d_ai.qmd` |

`articleTemplate` uses a stable `sourceKey` for each figure. The end-to-end importer uploads each file first, replaces `sourceKey` with the returned `fileId`, saves the article, and then marks it ready.

## Submit and retain the real example

With the local stack running:

```powershell
node scripts/paper01/submit-paper01.mjs
```

Resume a retained draft after a network or validation failure:

```powershell
$env:OPENISLE_DRAFT_ID='2'
node scripts/paper01/submit-paper01.mjs
```

The development seed account defaults to `user1` / `123456`. Override it with `OPENISLE_USERNAME`, `OPENISLE_PASSWORD`, or `OPENISLE_TOKEN`.

After successful submission, `generated/submitted-paper.json` records the permanent draft, paper, and post IDs. Re-running the command reports the existing paper instead of deleting it or creating a duplicate. Use `--force` only when a second retained demonstration paper is intentional.
