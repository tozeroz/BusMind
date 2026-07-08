import request from './request'

export const getLines = () => request.get('/bus/lines')
export const getLineDetail = (lineId) => request.get(`/bus/lines/${lineId}`)
export const getVehicles = (params) => request.get('/bus/vehicles', { params })
export const getPassengerFlow = (params) => request.get('/history/crowd', { params })
