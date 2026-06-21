import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 180_000, // 3 min — pipeline can take time on first model load
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail ?? err.message ?? 'Unknown error'
    return Promise.reject(new Error(String(msg)))
  }
)

export default client
