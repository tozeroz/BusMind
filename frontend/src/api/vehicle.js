import request from './request'

export const getVehicles = (params) => request.get('/vehicles', { params })

export const getVehicleDetail = (vehicleId) => request.get(`/vehicles/${vehicleId}`)

export const createVehicle = (data) => request.post('/vehicles', data)

export const updateVehicle = (vehicleId, data) => request.patch(`/vehicles/${vehicleId}`, data)

export const deleteVehicle = (vehicleId) => request.delete(`/vehicles/${vehicleId}`)

export const getVehiclesByLine = (lineId) => request.get(`/vehicles/line/${lineId}`)

export const getRealtimeVehicles = (params) => request.get('/vehicles/realtime', { params })
