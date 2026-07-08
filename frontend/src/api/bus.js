import request from './request'

export const getEta = (params) => request.get('/eta', { params })

export const predictPassengerLoad = (data) => request.post('/passenger-load-prediction', data)

export const estimateWalkingTime = (data) => request.post('/walking-time-estimation', data)

export const evaluateTravelExperience = (data) =>
  request.post('/travel-experience/evaluate', data)

export const recommendRoutes = (data) => request.post('/recommend-routes', data)
