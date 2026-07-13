/**
 * 文件：src/api/recommendation.js
 * 用途：定义某项后端能力对应的前端 API 访问边界。
 * 存放内容：接口请求函数、请求参数以及响应边界处理代码。
 * 实现功能：为页面和业务组合式函数提供统一、可复用的 HTTP 调用入口。
 */
import request from './request'
import { unwrapData } from './response'

export const RECOMMENDATION_PREFERENCES = Object.freeze({
  BALANCED: 'balanced',
  FASTEST: 'fastest',
  COMFORT: 'comfort',
  LESS_WALKING: 'less_walking',
  LESS_TRANSFER: 'less_transfer'
})

export const RECOMMEND_TYPES = Object.freeze({
  BEST_EXPERIENCE: 'best_experience',
  FASTEST: 'fastest',
  LEAST_CROWDED: 'least_crowded',
  LEAST_WALKING: 'least_walking',
  LEAST_TRANSFER: 'least_transfer'
})

const PREFERENCE_VALUES = new Set(Object.values(RECOMMENDATION_PREFERENCES))

const positiveInteger = (value, field) => {
  const number = Number(value)
  if (!Number.isInteger(number) || number <= 0) {
    throw new TypeError(`${field} 必须是正整数`)
  }
  return number
}

/**
 * 生成推荐接口请求体。支持站点 ID，或完整的起终点坐标。
 */
export function buildRecommendRoutesPayload(options = {}) {
  const preference = options.preference || RECOMMENDATION_PREFERENCES.BALANCED
  if (!PREFERENCE_VALUES.has(preference)) {
    throw new TypeError(`不支持的路线偏好: ${preference}`)
  }

  const allowTransfer = options.allow_transfer ?? options.allowTransfer ?? true
  const requestedMaxTransfer = options.max_transfer_count ?? options.maxTransferCount ?? 2
  const maxTransferCount = allowTransfer ? Number(requestedMaxTransfer) : 0
  if (!Number.isInteger(maxTransferCount) || maxTransferCount < 0 || maxTransferCount > 5) {
    throw new TypeError('max_transfer_count 必须是 0 到 5 之间的整数')
  }

  const payload = {
    preference,
    allow_transfer: Boolean(allowTransfer),
    max_transfer_count: maxTransferCount
  }

  const startStationId = options.start_station_id ?? options.startStationId
  const endStationId = options.end_station_id ?? options.endStationId
  if (startStationId != null || endStationId != null) {
    payload.start_station_id = positiveInteger(startStationId, 'start_station_id')
    payload.end_station_id = positiveInteger(endStationId, 'end_station_id')
  } else {
    const coordinateFields = [
      ['origin_longitude', options.origin_longitude ?? options.originLongitude],
      ['origin_latitude', options.origin_latitude ?? options.originLatitude],
      ['destination_longitude', options.destination_longitude ?? options.destinationLongitude],
      ['destination_latitude', options.destination_latitude ?? options.destinationLatitude]
    ]
    if (coordinateFields.some(([, value]) => value == null)) {
      throw new TypeError('必须提供起终点站 ID，或完整的起终点坐标')
    }
    coordinateFields.forEach(([field, value]) => {
      const number = Number(value)
      if (!Number.isFinite(number)) throw new TypeError(`${field} 必须是有效数字`)
      payload[field] = number
    })
  }

  const departTime = options.depart_time ?? options.departTime
  const maxWalkMinutes = options.max_walk_minutes ?? options.maxWalkMinutes
  if (departTime) payload.depart_time = departTime instanceof Date ? departTime.toISOString() : departTime
  if (maxWalkMinutes != null) payload.max_walk_minutes = Number(maxWalkMinutes)

  return payload
}

/** 保留统一响应外壳，兼容现有页面：response.data.items。 */
export const recommendRoutes = (options) =>
  request.post('/recommend-routes', buildRecommendRoutesPayload(options))

const routeById = (items, routeId) => items.find((route) => route.route_id === routeId) || null

/**
 * 返回适合组件直接消费的推荐结果，并将五种最优 route_id 解析成路线对象。
 */
export async function getRouteRecommendations(options) {
  const response = await recommendRoutes(options)
  const data = unwrapData(response, {})
  const items = Array.isArray(data.items) ? data.items : []

  return {
    ...data,
    items,
    optimal: {
      bestExperience: routeById(items, data.best_experience_route_id),
      fastest: routeById(items, data.fastest_route_id),
      leastCrowded: routeById(items, data.least_crowded_route_id),
      leastWalking: routeById(items, data.least_walking_route_id),
      leastTransfer: routeById(items, data.least_transfer_route_id)
    }
  }
}
