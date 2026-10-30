import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider'

export default function RequireAuth() {
  const { user, status, error, retry } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <main className="route-loading" role="status">Checking your sign-in…</main>
  if (status === 'error') return <main className="auth-unavailable" role="alert"><h1>Account service unavailable</h1><p>{error}</p><button className="btn-primary" onClick={retry}>Try again</button></main>
  if (!user) return <Navigate to="/login" state={{ from: location.pathname + location.search }} replace />
  return <Outlet />
}
