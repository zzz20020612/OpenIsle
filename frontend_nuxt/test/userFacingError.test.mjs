import assert from 'node:assert/strict'
import test from 'node:test'
import { toUserFacingError } from '../utils/userFacingError.js'

test('uses readable API errors and ignores boolean error flags', () => {
  assert.equal(toUserFacingError({ data: { error: 'Draft unavailable' } }, 'Fallback'), 'Draft unavailable')
  assert.equal(toUserFacingError({ data: { error: true, message: 'Try again later' } }, 'Fallback'), 'Try again later')
  assert.equal(toUserFacingError({ data: { error: true } }, 'Fallback'), 'Fallback')
})
