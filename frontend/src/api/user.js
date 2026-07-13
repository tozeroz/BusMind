/**
 * 文件：src/api/user.js
 * 用途：定义某项后端能力对应的前端 API 访问边界。
 * 存放内容：接口请求函数、请求参数以及响应边界处理代码。
 * 实现功能：为页面和业务组合式函数提供统一、可复用的 HTTP 调用入口。
 */
import request, { AUTH_TOKEN_KEY } from './request'

export const AUTH_USER_KEY = 'busmind_current_user'

export const registerUser = (data) => request.post('/users/register', data)
export const sendRegisterEmailCode = (data) => request.post('/users/register/email-code', data)
export const loginUser = (data) => request.post('/users/login', data)
export const getCurrentUser = () => request.get('/users/me')
export const triggerArrivalRefresh = () => request.post('/users/me/refresh-arrivals')
export const updateCurrentUser = (data) => request.patch('/users/me', data)
export const getUserQueryHistory = (params) => request.get('/users/me/query-history', { params })
export const getUserFavorites = (params) => request.get('/users/me/favorites', { params })
export const addUserFavorite = (data) => request.post('/users/me/favorites', data)
export const deleteUserFavorite = (favoriteId) => request.delete(`/users/me/favorites/${favoriteId}`)

export const saveAuthToken = (token, storage = localStorage) => {
  storage.setItem(AUTH_TOKEN_KEY, token)
}

export const saveCurrentUser = (user, storage = localStorage) => {
  if (user && typeof user === 'object') storage.setItem(AUTH_USER_KEY, JSON.stringify(user))
}

export const saveAuthSession = ({ accessToken, user, remember = false }) => {
  const storage = remember ? localStorage : sessionStorage
  clearAuthToken()
  saveAuthToken(accessToken, storage)
  saveCurrentUser(user, storage)
}

export const getAuthToken = () =>
  sessionStorage.getItem(AUTH_TOKEN_KEY)
  || sessionStorage.getItem('access_token')
  || ''

export const getStoredUser = () => {
  const raw = localStorage.getItem(AUTH_USER_KEY) || sessionStorage.getItem(AUTH_USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export const clearAuthToken = () => {
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem('access_token')
  localStorage.removeItem(AUTH_USER_KEY)
  sessionStorage.removeItem(AUTH_TOKEN_KEY)
  sessionStorage.removeItem('access_token')
  sessionStorage.removeItem(AUTH_USER_KEY)
}
