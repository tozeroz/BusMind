export * from './ai'
export * from './admin'
export * from './history'
export * from './intelligence'
export * from './location'
export * from './map'
export * from './transit'
export * from './user'
export * from './vehicle'

// @deprecated: simulation.js 已废弃，统一导出中不再包含。
// 如有特殊需求需临时引用，请直接 import from '@/api/simulation'，但新代码应使用 @/api/admin。