import request from './request'

// 兼容接口仅用于旧调用方迁移；新页面继续使用 /lines、/stations、/vehicles、/locations 主路径。
export const getLegacyBusLines = (params) => request.get('/bus-lines', { params })
export const getLegacyBusLineDetail = (lineId) => request.get(`/bus-lines/${lineId}`)
export const getLegacyBusLineStations = (lineId) => request.get(`/bus-lines/${lineId}/stations`)
export const getLegacyBusLineMap = (lineId, params) => request.get(`/bus-lines/${lineId}/map`, { params })
export const getLegacyBusLineGeometry = (lineId, params) => request.get(`/bus-lines/${lineId}/geometry`, { params })

export const getLegacyBusStations = (params) => request.get('/bus-stations', { params })
export const getLegacyBusStationDetail = (stationId) => request.get(`/bus-stations/${stationId}`)
export const getLegacyNearbyBusStations = (params) => request.get('/bus-stations/nearby', { params })

export const getLegacyRealtimeBusVehicles = (params) => request.get('/bus-vehicles/realtime', { params })
export const getLegacyNearbyLocation = (params) => request.get('/location/nearby', { params })
export const getLegacyLocationDetail = (stationId) => request.get(`/location/${stationId}`)
