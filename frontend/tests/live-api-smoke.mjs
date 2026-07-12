import assert from 'node:assert/strict'

const base = (process.env.BUSMIND_API_BASE_URL || 'http://127.0.0.1:8001/api/v1').replace(/\/$/, '')
const results = []

async function call(name, path, options = {}) {
  const response = await fetch(`${base}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  })
  const payload = await response.json().catch(() => null)
  assert.ok(payload && typeof payload === 'object', `${name}: 响应不是 JSON 对象`)
  assert.ok('code' in payload || 'detail' in payload, `${name}: 缺少统一 code 或 FastAPI detail`)
  if (!response.ok) throw new Error(`${name}: HTTP ${response.status} ${payload?.message || JSON.stringify(payload?.detail)}`)
  assert.equal(payload.code, 0, `${name}: 业务 code 非 0`)
  results.push({ name, status: 'PASS', trace_id: payload.trace_id || '' })
  return payload.data
}

function skip(name, reason) { results.push({ name, status: 'SKIP', reason }) }

await call('API health', '/')
const linesData = await call('lines', '/lines?page=1&limit=5')
const stationsData = await call('stations', '/stations?page=1&limit=5')
const vehiclesData = await call('vehicles realtime', '/vehicles/realtime')
await call('map lines', '/map/lines')
await call('map stations', '/map/stations')
await call('map road segments', '/map/road-segments')
await call('passenger flow history', '/history/passenger-flow?granularity=hour')
await call('AI fallback/online', '/ai/travel', { method: 'POST', body: JSON.stringify({ mode: 'qa', question: '请给我一条公交出行建议', preference: 'balanced' }) })

const stations = stationsData?.stations || stationsData?.items || []
if (stations[0]?.station_name) {
  await call('location search', `/locations/search?keyword=${encodeURIComponent(stations[0].station_name)}&page=1&limit=5`)
} else skip('location search', '数据库没有站点')

if (stations.length >= 2) {
  await call('route recommendation', '/recommend-routes', {
    method: 'POST', body: JSON.stringify({ start_station_id: stations[0].station_id, end_station_id: stations[1].station_id, preference: 'balanced', allow_transfer: true, max_transfer_count: 1 })
  })
} else skip('route recommendation', '数据库不足两个站点')

const vehicles = vehiclesData?.vehicles || vehiclesData?.items || []
const vehicle = vehicles.find((item) => item.vehicle_id && (item.next_station_id || item.current_station_id))
if (vehicle) {
  const stationId = vehicle.next_station_id || vehicle.current_station_id
  await call('ETA', `/eta?vehicle_id=${vehicle.vehicle_id}&target_station_id=${stationId}&line_id=${vehicle.line_id}`)
  await call('passenger load', '/passenger-load-prediction', {
    method: 'POST', body: JSON.stringify({ line_id: vehicle.line_id, station_id: stationId, vehicle_id: vehicle.vehicle_id, ...(vehicle.capacity > 0 ? { capacity: vehicle.capacity } : {}), ...(vehicle.onboard_count >= 0 ? { current_onboard_count: vehicle.onboard_count } : {}) })
  })
} else skip('ETA/passenger load', '数据库没有带站点的车辆')

console.table(results)
const failed = results.filter((item) => item.status === 'FAIL')
assert.equal(failed.length, 0)
console.log(`Live smoke finished: ${results.filter((item) => item.status === 'PASS').length} passed, ${results.filter((item) => item.status === 'SKIP').length} skipped`)
