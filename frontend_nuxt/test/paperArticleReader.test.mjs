import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeReaderArticle } from '../utils/paperArticleReader.js'

test('removes a DOCX cover section that duplicates the record abstract', () => {
  const article = {
    sections: [
      {
        key: 'cover',
        heading: 'Article',
        blocks: [
          { key: 'label', type: 'PARAGRAPH', text: 'Abstract' },
          { key: 'abstract', type: 'PARAGRAPH', text: 'Same abstract text.' },
        ],
      },
      { key: 'introduction', heading: '1. Introduction', blocks: [] },
    ],
  }

  assert.deepEqual(normalizeReaderArticle(article, 'Same abstract text.').sections, [
    article.sections[1],
  ])
})

test('keeps an ordinary Article section when it is not duplicate metadata', () => {
  const article = {
    sections: [{ key: 'article', heading: 'Article', blocks: [{ type: 'PARAGRAPH', text: 'Body' }] }],
  }

  assert.equal(normalizeReaderArticle(article, 'Different abstract').sections.length, 1)
})
