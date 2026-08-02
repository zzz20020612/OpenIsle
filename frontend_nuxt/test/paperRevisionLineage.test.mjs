import assert from 'node:assert/strict'
import test from 'node:test'
import { groupPaperRevisionLineages } from '../utils/paperRevisionLineage.js'

test('paper 6 and 7 form one lineage while paper 8 remains independent', () => {
  const result = groupPaperRevisionLineages([
    { id: 8, revisionNumber: 1, revisionOfPaperId: null },
    { id: 7, revisionNumber: 2, revisionOfPaperId: 6 },
    { id: 6, revisionNumber: 1, revisionOfPaperId: null },
  ])

  assert.equal(result.length, 2)
  assert.deepEqual(result.find((lineage) => lineage.rootId === '6').versions.map(({ id }) => id), [6, 7])
  assert.equal(result.find((lineage) => lineage.rootId === '6').latest.id, 7)
  assert.deepEqual(result.find((lineage) => lineage.rootId === '8').versions.map(({ id }) => id), [8])
})

test('backend root ids group a lineage even when an intermediate version is absent', () => {
  const result = groupPaperRevisionLineages([
    { id: 9, revisionRootPaperId: 6, revisionNumber: 3, revisionOfPaperId: 7 },
    { id: 6, revisionRootPaperId: 6, revisionNumber: 1 },
  ])
  assert.equal(result.length, 1)
  assert.equal(result[0].latest.id, 9)
})
