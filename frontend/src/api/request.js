import axios from 'axios'
import { getApiErrorMessage } from './response'

export const AUTH_TOKEN_KEY = 'busmind_access_token'

const env = import.meta.env || {}

const service = axios.create({
  baseURL: env.VITE_API_BASE_URL || '/api/v1',
  timeout: Number(env.VITE_API_TIMEOUT || 8000)
})

service.interceptors.request.use((config) => {
  const token =
    sessionStorage.getItem(AUTH_TOKEN_KEY) ||
    sessionStorage.getItem('access_token')

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

service.interceptors.response.use(
  (response) => {
    const payload = response.data
    if (payload && typeof payload === 'object' && typeof payload.code === 'number' && payload.code !== 0) {
      const error = new Error(payload.message || `接口返回业务错误 ${payload.code}`)
      error.name = 'ApiBusinessError'
      error.code = payload.code
      error.response = { ...response, data: payload }
      error.apiMessage = payload.message
      return Promise.reject(error)
    }
    return payload
  },
  (error) => {
    if (error?.response?.status === 401) {
      ;['busmind_access_token', 'access_token', 'busmind_current_user'].forEach((key) => {
        localStorage.removeItem(key)
        sessionStorage.removeItem(key)
      })
    }
    error.apiMessage = getApiErrorMessage(error)
    return Promise.reject(error)
  }
)

export default service
