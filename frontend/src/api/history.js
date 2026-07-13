/**
 * 文件：src/api/history.js
 * 用途：定义某项后端能力对应的前端 API 访问边界。
 * 存放内容：接口请求函数、请求参数以及响应边界处理代码。
 * 实现功能：为页面和业务组合式函数提供统一、可复用的 HTTP 调用入口。
 */
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


export const getPassengerLoadHistory = (params) =>
  request.get('/history/passenger-load', { params })

export const getPredictionHistory = (params) =>
  request.get('/history/predictions', { params })
