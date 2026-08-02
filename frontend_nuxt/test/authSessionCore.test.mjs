import test from 'node:test'
import assert from 'node:assert/strict'
import {
  createSingleFlight,
  shouldInvalidateToken,
} from '../utils/authSessionCore.js'

test('a stale token response cannot invalidate a newer login', () => {
  assert.equal(shouldInvalidateToken({
    requestToken: 'old-token',
    currentToken: 'new-token',
    status: 401,
    error: 'Invalid or expired token',
  }), false)
})

test('an explicit invalid response can invalidate the token it checked', () => {
  assert.equal(shouldInvalidateToken({
    requestToken: 'current-token',
    currentToken: 'current-token',
    status: 401,
    error: 'Invalid or expired token',
  }), true)
})

test('transport and server failures never invalidate a token', () => {
  assert.equal(shouldInvalidateToken({
    requestToken: 'current-token',
    currentToken: 'current-token',
    status: 0,
    error: 'Network request failed',
  }), false)
  assert.equal(shouldInvalidateToken({
    requestToken: 'current-token',
    currentToken: 'current-token',
    status: 503,
    error: 'Service unavailable',
  }), false)
})

test('concurrent checks for the same token share one request', async () => {
  const singleFlight = createSingleFlight()
  let calls = 0
  let resolveRequest
  const operation = () => {
    calls += 1
    return new Promise((resolve) => { resolveRequest = resolve })
  }

  const first = singleFlight('check:token', operation)
  const second = singleFlight('check:token', operation)
  await Promise.resolve()

  assert.equal(first, second)
  assert.equal(calls, 1)

  resolveRequest('ok')
  assert.equal(await first, 'ok')
  assert.equal(await second, 'ok')
})

