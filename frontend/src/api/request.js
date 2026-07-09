import axios from 'axios'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 8000
})

service.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.warn('接口暂未连接或请求失败，当前页面使用本地模拟数据。', error?.message)
    return Promise.reject(error)
  }
)

export default service
