import request from './request'

export const getPassengerFlowTrend = (params) =>
  request.get('/history/passenger-flow', { params })

export const getPassengerFlowPrediction = (params) =>
  request.get('/history/passenger-flow/prediction', { params })

export const getEtaPredictionsByLine = (lineId, params) =>
  request.get(`/history/eta/line/${lineId}`, { params })

export const getEtaPredictionForVehicle = (vehicleId, targetStationId, params) =>
  request.get(`/history/eta/${vehicleId}/${targetStationId}`, { params })

export const getLoadPredictionsByLine = (lineId, params) =>
  request.get(`/history/load/line/${lineId}`, { params })

export const getLoadPrediction = (lineId, params) =>
  request.get(`/history/load/${lineId}`, { params })
