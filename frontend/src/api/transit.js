import request from './request'

export const getLines = (params) => request.get('/lines', { params })

export const getBusLines = getLines

export const getLineDetail = (lineId) => request.get(`/lines/${lineId}`)

export const getBusLineDetail = getLineDetail

export const createLine = (data) => request.post('/lines', data)

export const updateLine = (lineId, data) => request.patch(`/lines/${lineId}`, data)

export const deleteLine = (lineId) => request.delete(`/lines/${lineId}`)

export const getLineStations = (lineId) => request.get(`/lines/${lineId}/stations`)

export const getBusLineStations = getLineStations

export const addStationToLine = (lineId, data) =>
  request.post(`/lines/${lineId}/stations`, data)

export const updateLineStation = (lineStationId, data) =>
  request.patch(`/lines/stations/${lineStationId}`, data)

export const removeStationFromLine = (lineStationId) =>
  request.delete(`/lines/stations/${lineStationId}`)

export const getStations = (params) => request.get('/stations', { params })

export const getBusStations = getStations

export const getStationDetail = (stationId) => request.get(`/stations/${stationId}`)

export const getBusStationDetail = getStationDetail

export const createStation = (data) => request.post('/stations', data)

export const updateStation = (stationId, data) => request.patch(`/stations/${stationId}`, data)

export const deleteStation = (stationId) => request.delete(`/stations/${stationId}`)

export const getStationLines = (stationId) => request.get(`/stations/${stationId}/lines`)

export const searchNearbyStations = (data) => request.post('/stations/nearby', data)

export const getAllStationCoordinates = () => request.get('/stations/coordinates/all')
