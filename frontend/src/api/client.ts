import axios, { type InternalAxiosRequestConfig } from 'axios'
import { csrfToken, expireSession, sessionEpoch } from '../auth/session'

type SessionConfig = InternalAxiosRequestConfig & { sessionEpoch?: number }
export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); this.name = 'ApiError' }
}

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'patent-client' },
  withCredentials: true,
  timeout: 180_000, // 3 min — pipeline can take time on first model load
})

client.interceptors.request.use(config => {
  ;(config as SessionConfig).sessionEpoch = sessionEpoch()
  if (!['get', 'head', 'options'].includes(config.method ?? 'get') && csrfToken()) config.headers.set('X-CSRF-Token', csrfToken())
  return config
})

client.interceptors.response.use(
  (res) => {
    if ((res.config as SessionConfig).sessionEpoch !== sessionEpoch()) throw new ApiError('This request belongs to a previous sign-in.')
    return res
  },
  (err) => {
    if (err.config && (err.config as SessionConfig).sessionEpoch !== sessionEpoch()) return Promise.reject(new ApiError('This request belongs to a previous sign-in.'))
    const status = err.response?.status
    if (status === 401 && !['/auth/login', '/auth/signup'].includes(err.config?.url)) expireSession()
    const msg = err.response?.data?.detail ?? err.message ?? 'Unknown error'
    const description = Array.isArray(msg) ? msg.map(item => `${item.loc?.slice(-1)[0] ?? 'Input'}: ${item.msg}`).join(' · ') : String(msg)
    return Promise.reject(new ApiError(description, status))
  }
)

export default client
