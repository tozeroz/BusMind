import request from './request'

export const refreshAdminLtaBusArrival = (data) =>
  request.post('/admin/lta/bus-arrival/refresh', data)
