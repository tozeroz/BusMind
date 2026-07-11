import axios from 'axios'

export const AUTH_TOKEN_KEY = 'busmind_access_token'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 8000
})

service.interceptors.request.use((config) => {
  const token =
    localStorage.getItem(AUTH_TOKEN_KEY) ||
    localStorage.getItem('access_token') ||
    sessionStorage.getItem(AUTH_TOKEN_KEY) ||
    sessionStorage.getItem('access_token')

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

service.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.warn('接口暂未连接或请求失败，当前页面使用本地模拟数据。', error?.message)
    return Promise.reject(error)
  }
)

export default service
