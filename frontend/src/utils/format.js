/**
 * 文件：src/utils/format.js
 * 用途：提供前端共享的无副作用工具函数。
 * 存放内容：格式化、校验或数据转换代码。
 * 实现功能：集中复用纯计算逻辑，不维护响应式状态，也不直接调用接口。
 */
export const crowdClass = (level) => {
  const map = {
    空闲: 'level-free',
    适中: 'level-normal',
    拥挤: 'level-busy',
    非常拥挤: 'level-full'
  }
  return map[level] || 'level-normal'
}
