/**
 * BusMind API 统一响应适配。
 * Axios 拦截器返回统一外壳：{ code, message, data, trace_id, timestamp }。
 */
export function unwrapData(response, fallback = null) {
  if (response == null) return fallback
  if (Object.prototype.hasOwnProperty.call(response, 'data')) {
    return response.data ?? fallback
  }
  return response
}

export function unwrapList(response, key, fallback = []) {
  const data = unwrapData(response, null)
  if (Array.isArray(data)) return data
  if (!data || typeof data !== 'object') return fallback
  if (key && Array.isArray(data[key])) return data[key]
  if (Array.isArray(data.items)) return data.items
  return fallback
}

function validationDetailText(detail) {
  if (!Array.isArray(detail)) return ''
  return detail
    .map((item) => {
      const location = Array.isArray(item?.loc) ? item.loc.filter((part) => part !== 'body').join('.') : ''
      return [location, item?.msg].filter(Boolean).join(' ')
    })
    .filter(Boolean)
    .join('；')
}

export function getApiErrorMessage(error, fallback = '请求失败，请稍后重试') {
  const payload = error?.response?.data
  const detail = payload?.detail

  if (typeof payload?.message === 'string' && payload.message.trim()) return payload.message
  if (typeof detail?.message === 'string' && detail.message.trim()) return detail.message
  if (typeof detail === 'string' && detail.trim()) return detail

  const validationMessage = validationDetailText(detail)
  if (validationMessage) return validationMessage

  if (typeof error?.apiMessage === 'string' && error.apiMessage.trim()) return error.apiMessage
  if (typeof error?.message === 'string' && error.message.trim() && error.message !== 'Network Error') {
    return error.message
  }
  if (error?.message === 'Network Error') return '无法连接后端服务，请确认后端已启动并检查代理配置'
  return fallback
}

export function getTraceId(responseOrError) {
  return responseOrError?.trace_id
    || responseOrError?.response?.data?.trace_id
    || responseOrError?.response?.data?.detail?.trace_id
    || ''
}
