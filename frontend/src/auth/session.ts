// Session cookies stay HttpOnly. Only the CSRF value and a local request epoch
// are kept in memory; neither is written to browser storage.
let csrf: string | null = null
let epoch = 0
let onExpired = () => {}

export const sessionEpoch = () => epoch
export const csrfToken = () => csrf
export function replaceSession(token: string | null) { csrf = token; epoch += 1 }
export function handleExpiry(callback: () => void) { onExpired = callback; return () => { onExpired = () => {} } }
export function expireSession() { replaceSession(null); onExpired() }

export function safeReturnPath(value: unknown): string {
  return typeof value === 'string' && /^\/(analyze|results\/(cases|nlp|patents|graph|gnn|evaluation|improvements))(\?.*)?$/.test(value)
    ? value : '/results/cases'
}
