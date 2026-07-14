const STORAGE_KEY = 'busmind_local_query_history'
const MAX_RECORDS = 50

export function getLocalQueryHistory(storage = localStorage) {
  try {
    const value = JSON.parse(storage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

export function addLocalQueryHistory(record, storage = localStorage) {
  const createdAt = new Date().toISOString()
  const history = {
    history_id: `local-${Date.now()}`,
    query_type: 'route_search',
    result_summary: '',
    ...record,
    created_at: createdAt,
    _local: true
  }
  const duplicateKey = `${history.query_type}|${history.origin_name}|${history.destination_name}`
  const previous = getLocalQueryHistory(storage).filter((item) => (
    `${item.query_type}|${item.origin_name}|${item.destination_name}` !== duplicateKey
  ))
  storage.setItem(STORAGE_KEY, JSON.stringify([history, ...previous].slice(0, MAX_RECORDS)))
  return history
}

export function mergeQueryHistory(serverHistory = [], localHistory = getLocalQueryHistory()) {
  return [...serverHistory, ...localHistory]
    .sort((left, right) => new Date(right.created_at || 0) - new Date(left.created_at || 0))
    .slice(0, MAX_RECORDS)
}
