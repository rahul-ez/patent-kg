import client from './client'

export interface User { user_id: string; email: string; display_name: string }
export interface AuthSession { user: User; csrf_token: string; expires_at: string }
export const currentAccount = async () => (await client.get<AuthSession>('/auth/me')).data
export const signIn = async (email: string, password: string) => (await client.post<AuthSession>('/auth/login', { email, password })).data
export const signUp = async (email: string, password: string, display_name: string) => (await client.post<AuthSession>('/auth/signup', { email, password, display_name })).data
export const signOut = async () => { await client.post('/auth/logout') }
