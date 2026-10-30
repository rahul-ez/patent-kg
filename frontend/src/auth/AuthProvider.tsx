import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { currentAccount, signOut, type AuthSession, type User } from '../api/auth'
import { usePipelineStore } from '../store/usePipelineStore'
import { ApiError } from '../api/client'
import { handleExpiry, replaceSession } from './session'

interface AuthState {
  user: User | null
  status: 'loading' | 'ready' | 'error'
  error: string | null
  accept: (session: AuthSession) => void
  logout: () => Promise<void>
  retry: () => void
}
const AuthContext = createContext<AuthState | null>(null)
const AUTH_EVENT = 'patent-auth-event'

export function AuthProvider({ children }: { children: ReactNode }) {
  const cache = useQueryClient()
  const [session, setSession] = useState<AuthSession | null>(null)
  const [status, setStatus] = useState<AuthState['status']>('loading')
  const [error, setError] = useState<string | null>(null)
  const request = useRef(0)

  const clear = useCallback(() => {
    request.current += 1
    replaceSession(null)
    cache.clear()
    usePipelineStore.getState().clearUser()
    setSession(null)
    setStatus('ready')
    setError(null)
  }, [cache])

  const adopt = useCallback((value: AuthSession) => {
    request.current += 1
    replaceSession(value.csrf_token)
    cache.clear()
    usePipelineStore.getState().bindUser(value.user.user_id)
    setSession(value)
    setStatus('ready')
    setError(null)
  }, [cache])

  const load = useCallback(async () => {
    const id = ++request.current
    setStatus('loading')
    setError(null)
    try {
      const value = await currentAccount()
      if (id === request.current) adopt(value)
    } catch (err) {
      if (id !== request.current) return
      if (err instanceof ApiError && err.status === 401) clear()
      else { setStatus('error'); setError(err instanceof Error ? err.message : 'Could not check your sign-in.') }
    }
  }, [adopt, clear])

  useEffect(() => {
    const unsubscribe = handleExpiry(clear)
    void load()
    const changed = (event: StorageEvent) => {
      if (event.key !== AUTH_EVENT) return
      clear()
      void load()
    }
    window.addEventListener('storage', changed)
    return () => { request.current += 1; unsubscribe(); window.removeEventListener('storage', changed) }
  }, [clear, load])

  useEffect(() => {
    if (!session) return
    const timer = setTimeout(clear, Math.max(0, new Date(session.expires_at).getTime() - Date.now()))
    return () => clearTimeout(timer)
  }, [session, clear])

  const notify = () => localStorage.setItem(AUTH_EVENT, crypto.randomUUID())
  const accept = (value: AuthSession) => { adopt(value); notify() }
  const logout = async () => { await signOut(); clear(); notify() }
  return <AuthContext.Provider value={{ user: session?.user ?? null, status, error, accept, logout, retry: () => void load() }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('Authentication provider is missing.')
  return auth
}
