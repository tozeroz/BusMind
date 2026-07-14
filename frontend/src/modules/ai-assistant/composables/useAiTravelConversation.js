import { ref } from 'vue'
import { askAiTravel } from '@/api/ai'
import { RECOMMENDATION_PREFERENCES } from '@/api/recommendation'
import { getApiErrorMessage, unwrapData } from '@/api/response'

const welcomeMessage = () => ({
  id: Date.now(),
  role: 'assistant',
  content: '\u4f60\u597d\uff0c\u6211\u4f1a\u7ed3\u5408\u5f53\u524d\u884c\u7a0b\u3001\u8def\u7ebf\u65f6\u95f4\u548c\u5ba2\u8f7d\u60c5\u51b5\u7ed9\u51fa\u5efa\u8bae\u3002'
})

const preferenceFromText = (text) => {
  if (/\u5c11\u8d70|\u6b65\u884c/.test(text)) return RECOMMENDATION_PREFERENCES.LESS_WALKING
  if (/\u5c11\u6362|\u6362\u4e58/.test(text)) return RECOMMENDATION_PREFERENCES.LESS_TRANSFER
  if (/\u6700\u5feb|\u5feb\u4e00\u70b9/.test(text)) return RECOMMENDATION_PREFERENCES.FASTEST
  if (/\u8212\u9002|\u4e0d\u6324|\u5ba2\u6d41\u4f4e/.test(text)) return RECOMMENDATION_PREFERENCES.COMFORT
  return RECOMMENDATION_PREFERENCES.BALANCED
}

const isPositiveStationId = (value) => Number.isInteger(Number(value)) && Number(value) > 0

export function useAiTravelConversation({ getJourneyContext, normalizeRoute }) {
  const messages = ref([welcomeMessage()])
  const conversationId = ref(null)
  const currentRoute = ref(null)
  const status = ref('idle')
  const missingFields = ref([])
  const fallback = ref(false)
  const isSending = ref(false)

  const updateReply = (id, content, role = 'assistant') => {
    const target = messages.value.find((message) => message.id === id)
    if (target) Object.assign(target, { content, role })
  }

  async function send(question, options = {}) {
    const text = String(question || '').trim()
    if (!text || isSending.value) return null

    const userId = Date.now()
    const replyId = userId + 1
    messages.value.push({ id: userId, role: 'user', content: text })
    messages.value.push({ id: replyId, role: 'assistant', content: '\u6b63\u5728\u6574\u7406\u884c\u7a0b\u8bc1\u636e...' })
    isSending.value = true

    try {
      const journey = getJourneyContext?.() || {}
      const payload = {
        question: text,
        ...(conversationId.value ? { conversation_id: conversationId.value } : {}),
        ...(isPositiveStationId(journey.startStationId) ? { start_station_id: Number(journey.startStationId) } : {}),
        ...(isPositiveStationId(journey.endStationId) ? { end_station_id: Number(journey.endStationId) } : {}),
        ...(options.routeId ? { route_id: options.routeId } : {}),
        preference: preferenceFromText(text)
      }
      if (Array.isArray(journey.rawRoutes) && journey.rawRoutes.length) {
        payload.context = {
          current_location: journey.startName,
          destination: journey.endName,
          items: journey.rawRoutes
        }
      }

      const response = await askAiTravel(payload)
      const data = unwrapData(response, {})
      conversationId.value = data.conversation_id || conversationId.value
      status.value = data.status || 'completed'
      missingFields.value = Array.isArray(data.missing_fields) ? data.missing_fields : []
      fallback.value = data.fallback === true

      const reminders = Array.isArray(data.reminders) ? data.reminders.filter(Boolean) : []
      const reminderText = reminders.length ? `\n\n\u63d0\u9192\uff1a${reminders.join('\uff1b')}` : ''
      const degradedText = fallback.value ? '\n\n\u5f53\u524d AI \u670d\u52a1\u5df2\u964d\u7ea7\uff0c\u4ee5\u540e\u7aef\u672c\u5730\u6a21\u677f\u56de\u7b54\u3002' : ''
      updateReply(replyId, `${data.answer || '\u540e\u7aef\u672a\u8fd4\u56de\u56de\u7b54\u3002'}${reminderText}${degradedText}`)

      const relatedRoute = Array.isArray(data.related_routes) ? data.related_routes[0] : null
      if (relatedRoute) currentRoute.value = normalizeRoute(relatedRoute)
      return data
    } catch (error) {
      status.value = 'error'
      missingFields.value = []
      fallback.value = false
      updateReply(replyId, getApiErrorMessage(error, '\u540e\u7aef AI \u63a5\u53e3\u6682\u4e0d\u53ef\u7528\uff0c\u8bf7\u786e\u8ba4\u540e\u7aef\u5df2\u542f\u52a8\u3002'), 'error')
      return null
    } finally {
      isSending.value = false
    }
  }

  const explainCurrentRoute = () => currentRoute.value
    ? send('\u4e3a\u4ec0\u4e48\u63a8\u8350\u8fd9\u6761\u8def\u7ebf\uff1f', { routeId: currentRoute.value.routeId || currentRoute.value.route_id })
    : null

  const requestNextRoute = () => send('\u6362\u4e00\u6761')

  function newConversation() {
    messages.value = [welcomeMessage()]
    conversationId.value = null
    currentRoute.value = null
    status.value = 'idle'
    missingFields.value = []
    fallback.value = false
  }

  return {
    messages,
    conversationId,
    currentRoute,
    status,
    missingFields,
    fallback,
    isSending,
    send,
    explainCurrentRoute,
    requestNextRoute,
    newConversation
  }
}
