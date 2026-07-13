/**
 * 文件：src/api/simulation.js
 * 用途：定义某项后端能力对应的前端 API 访问边界。
 * 存放内容：接口请求函数、请求参数以及响应边界处理代码。
 * 实现功能：为页面和业务组合式函数提供统一、可复用的 HTTP 调用入口。
 */
/**
 * @deprecated 此文件为旧仿真刷新接口封装，已废弃。
 *
 * 正式 admin 刷新方法请使用 `@/api/admin`：
 *   - refreshAdminLtaBusArrival      → POST /admin/lta/bus-arrival/refresh
 *   - refreshAdminLtaTrafficSpeedBands → POST /admin/lta/traffic-speed-bands/refresh
 *
 * 本文件保留仅用于历史兼容，新代码禁止调用。
 * 后续大版本将直接删除本文件。
 */

import request from './request'

/** @deprecated 使用 `refreshAdminLtaBusArrival` 代替 */
export const updateVehicleStatus = (vehicleId, data) =>
  request.patch(`/simulation/vehicle-status/${vehicleId}`, data)

/** @deprecated 使用 `refreshAdminLtaBusArrival` 代替 */
export const updatePredictionResult = (data) =>
  request.post('/simulation/prediction-results', data)

/** @deprecated 使用 `refreshAdminLtaBusArrival` 代替 */
export const refreshLtaBusArrival = (data) =>
  request.post('/simulation/lta-bus-arrival/refresh', data)