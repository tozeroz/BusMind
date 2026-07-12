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