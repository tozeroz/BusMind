import request from './request'

export const searchLocations = (params) => request.get('/locations/search', { params })

export const getNearbyLocations = (params) => request.get('/locations/nearby', { params })

export const getLocationMapStations = () => request.get('/locations/map/stations')

export const getLocationDetail = (locationId) => request.get(`/locations/${locationId}`)
