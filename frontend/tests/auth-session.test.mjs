import test from 'node:test'
import assert from 'node:assert/strict'
import { csrfToken, sessionEpoch, replaceSession, expireSession, handleExpiry, safeReturnPath } from '../src/auth/session.ts'

test('session boundaries invalidate previous request epochs', () => {
  replaceSession('csrf-value')
  const before = sessionEpoch()
  assert.equal(csrfToken(), 'csrf-value')
  replaceSession(null)
  assert.notEqual(sessionEpoch(), before)
  assert.equal(csrfToken(), null)
})

test('expiry clears memory and informs the auth provider', () => {
  let expired = false
  const stop = handleExpiry(() => { expired = true })
  replaceSession('csrf')
  expireSession()
  assert.equal(expired, true)
  assert.equal(csrfToken(), null)
  stop()
})

test('post-login return paths cannot redirect outside the workspace', () => {
  assert.equal(safeReturnPath('/analyze'), '/analyze')
  assert.equal(safeReturnPath('/results/patents'), '/results/patents')
  for (const unsafe of ['//evil.example', 'https://evil.example', '/login', '/signup', '/\\evil', null, {}, '/results/../../evil']) assert.equal(safeReturnPath(unsafe), '/results/cases')
})
