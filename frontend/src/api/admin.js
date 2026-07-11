import request from './request'

export const refreshAdminLtaBusArrival = (data) =>
  request.post('/admin/lta/bus-arrival/refresh', data)

export const refreshAdminLtaTrafficSpeedBands = (data) =>
  request.post('/admin/lta/traffic-speed-bands/refresh', data)
