/**
 * 文件：src/api/index.js
 * 用途：定义某项后端能力对应的前端 API 访问边界。
 * 存放内容：接口请求函数、请求参数以及响应边界处理代码。
 * 实现功能：为页面和业务组合式函数提供统一、可复用的 HTTP 调用入口。
 */
export * from './ai'
export * from './admin'
export * from './history'
export * from './intelligence'
export { buildRecommendRoutesPayload, getRouteRecommendations } from './recommendation'
export { RECOMMENDATION_PREFERENCES, RECOMMEND_TYPES } from './recommendation'
export * from './location'
export * from './map'
export * from './simulation'
export * from './transit'
export * from './user'
export * from './vehicle'
export * from './compatibility'
export * from './health'
export * from './response'
