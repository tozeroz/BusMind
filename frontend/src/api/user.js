import request, { AUTH_TOKEN_KEY } from './request'

export const registerUser = (data) => request.post('/users/register', data)

export const loginUser = (data) => request.post('/users/login', data)

export const getCurrentUser = () => request.get('/users/me')

export const updateCurrentUser = (data) => request.patch('/users/me', data)

export const getUserQueryHistory = (params) =>
  request.get('/users/me/query-history', { params })

export const getUserFavorites = (params) =>
  request.get('/users/me/favorites', { params })

export const addUserFavorite = (data) =>
  request.post('/users/me/favorites', data)

export const deleteUserFavorite = (favoriteId) =>
  request.delete(`/users/me/favorites/${favoriteId}`)

export const saveAuthToken = (token, storage = localStorage) => {
  storage.setItem(AUTH_TOKEN_KEY, token)
}

export const clearAuthToken = () => {
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem('access_token')
  sessionStorage.removeItem(AUTH_TOKEN_KEY)
  sessionStorage.removeItem('access_token')
}
