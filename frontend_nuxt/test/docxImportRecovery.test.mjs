import assert from 'node:assert/strict'
import test from 'node:test'
import { cleanupImportedDraftFiles } from '../utils/docxImportRecovery.js'

test('failed DOCX import removes newly uploaded figures once', async () => {
  const removed = []
  const failed = await cleanupImportedDraftFiles([11, 12, 11], async (id) => { removed.push(id) })
  assert.deepEqual(removed, [11, 12])
  assert.deepEqual(failed, [])
})

test('cleanup reports figure files that still need manual removal', async () => {
  const failed = await cleanupImportedDraftFiles([11, 12], async (id) => {
    if (id === 12) throw new Error('network unavailable')
  })
  assert.deepEqual(failed, [12])
})
