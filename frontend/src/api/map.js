/**
 * 文件：src/api/map.js
 * 用途：定义某项后端能力对应的前端 API 访问边界。
 * 存放内容：接口请求函数、请求参数以及响应边界处理代码。
 * 实现功能：为页面和业务组合式函数提供统一、可复用的 HTTP 调用入口。
 */
import request from './request'

const shouldUseFallback = (error) =>
  !error?.response || error.response.status >= 500

export async function getMapStations(params) {
  try {
    return await request.get('/map/stations', { params, timeout: 12000 })
  } catch (error) {
    if (!shouldUseFallback(error)) throw error
    return request.get('/locations/map/stations', { params, timeout: 30000 })
  }
}

export const getRoadSegments = (params) =>
  request.get('/map/road-segments', { params, timeout: 60000 })

export const getCachedBusArrival = (params) =>
  request.get('/map/bus-arrival', { params, timeout: 12000 })

export const getTrafficHeatmap = (params) =>
  request.get('/map/traffic-heatmap', { params, timeout: 60000 })

export async function getMapLines(params = {}) {
  try {
    return await request.get('/map/lines', { params, timeout: 12000 })
  } catch (error) {
    if (!shouldUseFallback(error)) throw error
    return request.get('/lines', {
      params: { page: 1, limit: 100, ...params },
      timeout: 30000
    })
  }
}
