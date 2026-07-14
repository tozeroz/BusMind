import { computed, ref, watch } from 'vue'
import { addUserFavorite, deleteUserFavorite, getUserFavorites } from '@/api/user'
import { getApiErrorMessage, unwrapData } from '@/api/response'

export function useLineFavorite(line) {
  const favoriteId = ref(null)
  const loading = ref(false)
  const message = ref('')
  let requestSequence = 0

  const lineId = computed(() => Number(line.value?.line_id ?? line.value?.id))
  const canFavorite = computed(() => Number.isInteger(lineId.value) && lineId.value > 0)
  const isFavorite = computed(() => {
    if (favoriteId.value === null || favoriteId.value === undefined || favoriteId.value === '') return false
    const value = Number(favoriteId.value)
    return Number.isInteger(value) && value > 0
  })
  const lineName = () => String(
    line.value?.line_name
    || line.value?.title
    || line.value?.service_no
    || line.value?.line_code
    || `线路 ${lineId.value}`
  ).trim()

  async function syncFavorite() {
    const currentLineId = lineId.value
    const sequence = ++requestSequence
    favoriteId.value = null
    message.value = ''
    if (!Number.isInteger(currentLineId) || currentLineId <= 0) return
    loading.value = true
    try {
      const response = await getUserFavorites({ page: 1, limit: 100 })
      if (sequence !== requestSequence) return
      const favorites = unwrapData(response, {})?.favorites || []
      const match = favorites.find((item) => (
        ['route', 'line'].includes(item.favorite_type)
        && Number(item.target_id) === currentLineId
      ))
      favoriteId.value = match?.favorite_id ?? null
    } catch (error) {
      if (sequence === requestSequence) message.value = getApiErrorMessage(error, '收藏状态读取失败')
    } finally {
      if (sequence === requestSequence) loading.value = false
    }
  }

  async function toggleFavorite() {
    if (!canFavorite.value || loading.value) return
    loading.value = true
    message.value = ''
    try {
      if (isFavorite.value) {
        const id = Number(favoriteId.value)
        if (!Number.isInteger(id) || id <= 0) return
        await deleteUserFavorite(id)
        favoriteId.value = null
        message.value = '已取消收藏'
      } else {
        const response = await addUserFavorite({
          favorite_type: 'route',
          target_id: Math.trunc(lineId.value),
          target_name: lineName()
        })
        favoriteId.value = unwrapData(response, {})?.favorite_id ?? null
        message.value = '线路已收藏'
        if (!favoriteId.value) await syncFavorite()
      }
    } catch (error) {
      if ([400, 409].includes(error?.response?.status)) {
        await syncFavorite()
        if (isFavorite.value) message.value = '线路已收藏'
      } else {
        message.value = getApiErrorMessage(error, '收藏操作失败')
      }
    } finally {
      loading.value = false
    }
  }

  watch(lineId, syncFavorite, { immediate: true })
  return { canFavorite, isFavorite, loading, message, toggleFavorite }
}
