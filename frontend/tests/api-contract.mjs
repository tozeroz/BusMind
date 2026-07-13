/**
 * 文件：tests/api-contract.mjs
 * 用途：验证前端接口契约和集成行为。
 * 存放内容：可执行断言、测试数据以及冒烟测试流程。
 * 实现功能：在生产代码之外发现接口契约和真实联调回归。
 */
import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))
const srcDir = path.resolve(here, '../src')
const apiDir = path.join(srcDir, 'api')
const contractSource = await readFile(path.join(apiDir, 'contract.js'), 'utf8')
const moduleUrl = new URL('../src/api/contract.js', import.meta.url)
const { API_OPERATION_CONTRACT } = await import(moduleUrl)

async function collectSourceFiles(dir) {
  const entries = await readdir(dir, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      files.push(...await collectSourceFiles(fullPath))
    } else if (/\.(?:js|vue)$/.test(entry.name)) {
      files.push(fullPath)
    }
  }
  return files
}

assert.equal(API_OPERATION_CONTRACT.length, 72, '运行时 OpenAPI 应映射 72 个操作')
const unique = new Set(API_OPERATION_CONTRACT.map((item) => `${item.method} ${item.path}`))
assert.equal(unique.size, 72, '接口契约中存在重复 method/path')

const apiSources = await Promise.all(
  (await readdir(apiDir)).filter((name) => name.endsWith('.js') && name !== 'contract.js')
    .map((name) => readFile(path.join(apiDir, name), 'utf8'))
)
const allApiSource = apiSources.join('\n')
const missingWrappers = API_OPERATION_CONTRACT
  .filter((item) => item.wrapper)
  .filter((item) => !new RegExp(`\\b${item.wrapper}\\b`).test(allApiSource))

assert.deepEqual(
  missingWrappers,
  [],
  `以下接口映射函数未在 src/api 中实现：${missingWrappers.map((item) => item.wrapper).join(', ')}`
)
assert.match(contractSource, /app\.openapi\(\)/, '契约文件应说明来源')

const pageFiles = (await collectSourceFiles(srcDir)).filter((file) => !file.startsWith(`${apiDir}${path.sep}`))
const pageSources = await Promise.all(pageFiles.map(async (file) => ({
  file: path.relative(srcDir, file),
  source: await readFile(file, 'utf8')
})))

const findCalls = (wrapper) => {
  const callPattern = new RegExp(`\\b${wrapper}\\s*\\(`)
  return pageSources.filter(({ source }) => callPattern.test(source)).map(({ file }) => file)
}

const disconnected = API_OPERATION_CONTRACT
  .filter((item) => item.status === 'connected' && item.wrapper)
  .map((item) => ({ ...item, calls: findCalls(item.wrapper) }))
  .filter((item) => item.calls.length === 0)
assert.deepEqual(
  disconnected,
  [],
  `以下标记为 connected 的接口没有页面调用：${disconnected.map((item) => item.wrapper).join(', ')}`
)

const forbiddenPageCalls = API_OPERATION_CONTRACT
  .filter((item) => ['compatibility', 'deferred', 'deprecated'].includes(item.status) && item.wrapper)
  .map((item) => ({ ...item, calls: findCalls(item.wrapper) }))
  .filter((item) => item.calls.length > 0)
assert.deepEqual(
  forbiddenPageCalls,
  [],
  `兼容/暂缓/废弃接口不应被现行页面调用：${forbiddenPageCalls.map((item) => `${item.wrapper} -> ${item.calls.join(',')}`).join('；')}`
)

const statusCounts = API_OPERATION_CONTRACT.reduce((result, item) => {
  result[item.status] = (result[item.status] || 0) + 1
  return result
}, {})
const connectedCallSites = API_OPERATION_CONTRACT
  .filter((item) => item.status === 'connected' && item.wrapper)
  .reduce((sum, item) => sum + findCalls(item.wrapper).length, 0)

console.log('API contract OK:', statusCounts)
console.log(`Connected page calls OK: ${statusCounts.connected} operations, ${connectedCallSites} call sites`)
