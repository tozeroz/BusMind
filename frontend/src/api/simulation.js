import request from './request'

export const updateVehicleStatus = (vehicleId, data) =>
  request.patch(`/simulation/vehicle-status/${vehicleId}`, data)

export const updatePredictionResult = (data) =>
  request.post('/simulation/prediction-results', data)

export const refreshLtaBusArrival = (data) =>
  request.post('/simulation/lta-bus-arrival/refresh', data)
