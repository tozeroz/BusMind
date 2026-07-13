/**
 * 文件：src/api/request.js
 * 用途：定义某项后端能力对应的前端 API 访问边界。
 * 存放内容：接口请求函数、请求参数以及响应边界处理代码。
 * 实现功能：为页面和业务组合式函数提供统一、可复用的 HTTP 调用入口。
 */
import axios from 'axios'
import { getApiErrorMessage } from './response'

export const AUTH_TOKEN_KEY = 'busmind_access_token'

const env = import.meta.env || {}

const defaultApiBaseUrl = env.DEV ? 'http://127.0.0.1:8001/api/v1' : '/api/v1'

const service = axios.create({
  baseURL: env.VITE_API_BASE_URL || defaultApiBaseUrl,
  timeout: Number(env.VITE_API_TIMEOUT || 20000)
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
