import request from './request'

export const getMapStations = (params) => request.get('/map/stations', { params })

export const getRoadSegments = () => request.get('/map/road-segments')

export const getMapLines = () => request.get('/map/lines')
