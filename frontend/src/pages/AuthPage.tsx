import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import { useAuth } from '../auth/AuthProvider'
import { safeReturnPath } from '../auth/session'
import { signIn, signUp } from '../api/auth'

export default function AuthPage({ signup = false }: { signup?: boolean }) {
  const auth = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const from = safeReturnPath(location.state?.from)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (auth.user && auth.status === 'ready') return <Navigate to={from} replace />

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (pending) return
    setPending(true)
    setError(null)
    try {
      const value = signup ? await signUp(email.trim(), password, name.trim()) : await signIn(email.trim(), password)
      setPassword('')
      auth.accept(value)
      navigate(from, { replace: true })
    } catch (err) {
      setPassword('')
      setError(err instanceof Error ? err.message : 'Could not sign in. Try again.')
    } finally { setPending(false) }
  }

  return <div className="standalone-page">
    <a href="#main-content" className="skip-link">Skip to content</a>
    <AppHeader />
    <main id="main-content" className="auth-main">
      <section className="auth-intro">
        <h1>{signup ? 'Make room for your research.' : 'Return to your research.'}</h1>
        <p>Keep invention descriptions, prior-art comparisons, and revised analyses together in your own workspace.</p>
        <div className="auth-note"><h2>Your work stays yours</h2><p>Saved cases and analysis results are available only to the account that owns them. The patent reference collection remains shared.</p></div>
      </section>
      <section className="auth-form-panel" aria-labelledby="auth-title">
        <h2 id="auth-title">{signup ? 'Create an account' : 'Sign in'}</h2>
        <p>{signup ? 'Use a unique passphrase to protect your invention research.' : 'Enter your email and password to open your saved cases.'}</p>
        <form onSubmit={submit} className="auth-form">
          {signup && <div><label htmlFor="account-name">Name</label><input id="account-name" autoComplete="name" value={name} onChange={e => setName(e.target.value)} required maxLength={120} disabled={pending} /></div>}
          <div><label htmlFor="account-email">Email</label><input id="account-email" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required maxLength={320} disabled={pending} /></div>
          <div><label htmlFor="account-password">Password</label><input id="account-password" type="password" autoComplete={signup ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} required minLength={signup ? 15 : 1} maxLength={128} disabled={pending} aria-describedby={signup ? 'password-help' : undefined} />
            {signup && <p id="password-help" className="field-help">Use 15–128 characters. A memorable passphrase works well.</p>}</div>
          {error && <div className="error-notice" role="alert">{error}</div>}
          <button className="btn-primary" type="submit" disabled={pending || auth.status === 'loading'}>{pending ? (signup ? 'Creating account…' : 'Signing in…') : (signup ? 'Create account' : 'Sign in')}</button>
        </form>
        <p className="auth-switch">{signup ? 'Already have an account?' : 'New to the workspace?'}{' '}<Link to={signup ? '/login' : '/signup'} state={{ from }} className="text-link">{signup ? 'Sign in' : 'Create an account'}</Link></p>
        <p className="advisory-note">Looking for an older case? Ask the project administrator to link it to your account.</p>
      </section>
    </main>
  </div>
}
