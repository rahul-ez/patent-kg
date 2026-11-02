import test from 'node:test'
import assert from 'node:assert/strict'
import { apiErrorMessage } from '../src/api/error-message.ts'

test('an unreachable backend explains the gateway failure', () => {
  assert.equal(apiErrorMessage(undefined, 502, 'Request failed with status code 502'),
    'The application server is unavailable. Please try again shortly.')
})

test('server details and field validation remain visible', () => {
  assert.equal(apiErrorMessage('Account storage is unavailable.', 503, 'Error'), 'Account storage is unavailable.')
  assert.equal(apiErrorMessage('Incorrect email or password.', 401, 'Error'), 'Incorrect email or password.')
  assert.equal(apiErrorMessage([{ loc: ['body', 'email'], msg: 'Invalid email' }], 422, 'Error'), 'email: Invalid email')
})

test('other transport errors retain their original explanation', () => {
  assert.equal(apiErrorMessage(undefined, undefined, 'Network Error'), 'Network Error')
  assert.equal(apiErrorMessage(undefined, 504, 'Request timed out'), 'Request timed out')
})
