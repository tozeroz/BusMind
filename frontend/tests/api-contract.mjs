import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))
const apiDir = path.resolve(here, '../src/api')
const contractSource = await readFile(path.join(apiDir, 'contract.js'), 'utf8')
const moduleUrl = new URL('../src/api/contract.js', import.meta.url)
const { API_OPERATION_CONTRACT } = await import(moduleUrl)

assert.equal(API_OPERATION_CONTRACT.length, 72, '运行时 OpenAPI 应映射 72 个操作')
const unique = new Set(API_OPERATION_CONTRACT.map((item) => `${item.method} ${item.path}`))
assert.equal(unique.size, 72, '接口契约中存在重复 method/path')

const apiSources = await Promise.all(
  (await readdir(apiDir)).filter((name) => name.endsWith('.js') && name !== 'contract.js')
    .map((name) => readFile(path.join(apiDir, name), 'utf8'))
)
const allSource = apiSources.join('\n')
const missingWrappers = API_OPERATION_CONTRACT
  .filter((item) => item.wrapper)
  .filter((item) => !new RegExp(`\\b${item.wrapper}\\b`).test(allSource))

assert.deepEqual(missingWrappers, [], `以下接口映射函数未在 src/api 中实现：${missingWrappers.map((item) => item.wrapper).join(', ')}`)
assert.match(contractSource, /app\.openapi\(\)/, '契约文件应说明来源')

const statusCounts = API_OPERATION_CONTRACT.reduce((result, item) => {
  result[item.status] = (result[item.status] || 0) + 1
  return result
}, {})
console.log('API contract OK:', statusCounts)
