/**
 * 文件：src/utils/eta.js
 * 用途：提供前端共享的无副作用工具函数。
 * 存放内容：格式化、校验或数据转换代码。
 * 实现功能：集中复用纯计算逻辑，不维护响应式状态，也不直接调用接口。
 */
/**
 * ETA 字段适配层
 *
 * 后端正式字段为 `predicted_eta_minutes`，介绍/地图数据中也可能出现 `eta_minutes`。
 * 本文件统一抽取 ETA 分钟数并格式化，避免页面到处做字段兼容判断。
 *
 * 使用方式：
 *   import { getEtaMinutes, formatEtaDisplay } from '@/utils/eta'
 *   const mins = getEtaMinutes(item)        // number | null
 *   const text = formatEtaDisplay(item)      // "约 8 分钟" | "暂无"
 */

/**
 * 从任意对象中提取 ETA 分钟数（数值）。
 * 优先取后端正式字段 `predicted_eta_minutes`，回退到 `eta_minutes`、`eta`、`total_time_minutes`。
 *
 * @param {object} item - 推荐路线、站点、ETA 结果等
 * @returns {number|null}
 */
export function getEtaMinutes(item) {
  if (!item || typeof item !== 'object') return null

  const value = item.predicted_eta_minutes ?? item.eta_minutes ?? item.eta ?? item.total_time_minutes
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

/**
 * 将 ETA 分钟数格式化为展示文本。
 *
 * @param {number|object} source - 分钟数或包含 ETA 字段的对象
 * @returns {string} 如 "约 8 分钟" 或 "暂无实时到站"
 */
export function formatEtaDisplay(source) {
  const minutes = typeof source === 'object' ? getEtaMinutes(source) : Number(source)
  if (!Number.isFinite(minutes)) return '暂无实时到站'
  return `约 ${minutes} 分钟`
}