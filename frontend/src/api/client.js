import axios from 'axios'
import { useAuthStore } from '../stores/auth.js'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000
})

// Inject JWT on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 globally — clear auth state and redirect to login
client.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      auth.clearAuth()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
