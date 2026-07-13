/**
 * 文件：src/api/vehicle.js
 * 用途：定义某项后端能力对应的前端 API 访问边界。
 * 存放内容：接口请求函数、请求参数以及响应边界处理代码。
 * 实现功能：为页面和业务组合式函数提供统一、可复用的 HTTP 调用入口。
 */
import request from './request'

export const getVehicles = (params) => request.get('/vehicles', { params })

export const getVehicleDetail = (vehicleId) => request.get(`/vehicles/${vehicleId}`)

export const createVehicle = (data) => request.post('/vehicles', data)

export const updateVehicle = (vehicleId, data) => request.patch(`/vehicles/${vehicleId}`, data)

export const deleteVehicle = (vehicleId) => request.delete(`/vehicles/${vehicleId}`)

export const getVehiclesByLine = (lineId) => request.get(`/vehicles/line/${lineId}`)

export const getRealtimeVehicles = (params) => request.get('/vehicles/realtime', { params })
