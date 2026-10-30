import { useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PatentDocIcon } from '../assets/PatentIcons'
import { useAuth } from '../auth/AuthProvider'

export default function AppHeader({ children }: { children?: ReactNode }) {
  const { user, status, logout } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const endSession = async () => {
    setPending(true); setError(null)
    try { await logout(); navigate('/login', { replace: true }) } catch (err) { setError(err instanceof Error ? err.message : 'Could not sign out.') }
    finally { setPending(false) }
  }
  return (
    <header className={'app-header' + (user ? ' signed-in' : '')}>
      <Link to="/" className="app-brand" aria-label="Patent Intelligence home">
        <span className="brand-mark"><PatentDocIcon size={21} animate={false} /></span>
        <span>Patent Intelligence</span>
      </Link>
      <nav className="header-actions" aria-label="Workspace">
        {user ? <>
          {children ?? <Link to="/results/cases" className="text-link">Saved cases</Link>}
          <span className="account-name" title={user.email}>{user.display_name}</span>
          <button className="text-button" onClick={() => void endSession()} disabled={pending}>{pending ? 'Signing out…' : 'Sign out'}</button>
          {error && <span role="alert" className="account-error">{error}</span>}
        </> : status !== 'loading' ? <Link to="/login" className="text-link">Sign in</Link> : <span role="status">Checking sign-in…</span>}
      </nav>
    </header>
  )
}
