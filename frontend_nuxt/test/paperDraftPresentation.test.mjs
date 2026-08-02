import assert from 'node:assert/strict'
import test from 'node:test'
import {
  draftDisplayTitle,
  draftSourceLabel,
  partitionDraftsByAge,
} from '../utils/paperDraftPresentation.js'

test('draft title follows the explicit, metadata, and filename fallback order', () => {
  const draft = {
    displayName: '  Working name  ',
    manuscriptTitle: 'Paper title',
    primaryManuscriptFileName: 'paper.docx',
  }
  assert.equal(draftDisplayTitle(draft), 'Working name')
  assert.equal(draftDisplayTitle({ ...draft, displayName: ' ' }), 'Paper title')
  assert.equal(draftDisplayTitle({ primaryManuscriptFileName: 'paper.docx' }), 'paper.docx')
  assert.equal(draftDisplayTitle({}), 'Untitled submission')
})

test('revision source is identified separately from ordinary draft files', () => {
  assert.equal(
    draftSourceLabel({ revisionSourcePaperId: 6, revisionSourcePaperTitle: 'Original paper' }),
    'Revision of Original paper',
  )
  assert.equal(draftSourceLabel({ fileCount: 2 }), '2 uploaded files')
})

test('older drafts are partitioned without being deleted', () => {
  const result = partitionDraftsByAge([{ id: 1, stale: false }, { id: 2, stale: true }])
  assert.deepEqual(result.recent.map(({ id }) => id), [1])
  assert.deepEqual(result.older.map(({ id }) => id), [2])
})
