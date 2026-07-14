/**
 * 文件：src/modules/profile/composables/useProfilePage.js
 * 用途：集中管理个人中心页面的数据与交互状态。
 * 存放内容：用户资料、收藏、查询历史、编辑状态和接口调用。
 * 实现功能：为个人中心页面组件提供统一的数据加载、资料保存和收藏管理能力。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import {
  deleteUserFavorite,
  getCurrentUser,
  getUserFavorites,
  getUserQueryHistory,
  saveCurrentUser,
  updateCurrentUser
} from '@/api/user'
import { getApiErrorMessage } from '@/api/response'
import { getLocalQueryHistory, mergeQueryHistory } from '@/modules/profile/utils/localQueryHistory'

export function useProfilePage() {
  const user = reactive({})
  const favorites = ref([])
  const histories = ref([])
  const loading = ref(false)
  const saving = ref(false)
  const editing = ref(false)
  const message = ref('')
  const profileForm = reactive({ nickname: '', phone: '', email: '', city: '' })
  const preference = reactive({ comfort: 88, speed: 72, walking: 64 })

  const displayName = computed(() => user.nickname || user.username || '乘客')
  const avatarText = computed(() => displayName.value.slice(0, 1).toUpperCase())
  const roleText = computed(() => user.role === 'admin' ? '管理员' : '客户端用户')
  const favoriteCount = computed(() => favorites.value.length)
  const queryCount = computed(() => histories.value.length)
  const averageWait = computed(() => {
    const values = histories.value.map((item) => Number(item.eta_minutes)).filter(Number.isFinite)
    if (!values.length) return '6.5'
    return (values.reduce((sum, item) => sum + item, 0) / values.length).toFixed(1)
  })

  function syncForm() {
    Object.assign(profileForm, {
      nickname: user.nickname || user.username || '',
      phone: user.phone || user.mobile || '138****2026',
      email: user.email || 'client@busmind.cn',
      city: user.city || 'Singapore'
    })
  }

  async function loadProfile() {
    loading.value = true
    message.value = ''
    try {
      const [userResponse, favoritesResponse, historyResponse] = await Promise.all([
        getCurrentUser(),
        getUserFavorites({ page: 1, limit: 20 }),
        getUserQueryHistory({ page: 1, limit: 20 })
      ])
      Object.assign(user, userResponse.data?.user || userResponse.data || {})
      favorites.value = favoritesResponse.data?.favorites || []
      histories.value = mergeQueryHistory(historyResponse.data?.histories || [], getLocalQueryHistory())
      syncForm()
    } catch (error) {
      message.value = error?.response?.status === 401
        ? '登录已失效，请重新登录。'
        : getApiErrorMessage(error, '个人数据加载失败')
    } finally {
      loading.value = false
    }
  }

  async function saveProfile() {
    saving.value = true
    message.value = ''
    try {
      const response = await updateCurrentUser({ nickname: profileForm.nickname.trim() })
      Object.assign(user, response.data || {}, { nickname: profileForm.nickname.trim() })
      saveCurrentUser(user)
      editing.value = false
      message.value = '资料已更新。'
    } catch (error) {
      message.value = getApiErrorMessage(error, '资料更新失败')
    } finally {
      saving.value = false
    }
  }

  function cancelEdit() {
    syncForm()
    editing.value = false
  }

  async function removeFavorite(favoriteId) {
    try {
      await deleteUserFavorite(favoriteId)
      favorites.value = favorites.value.filter((item) => Number(item.favorite_id) !== Number(favoriteId))
      message.value = '已取消收藏。'
    } catch (error) {
      message.value = getApiErrorMessage(error, '取消收藏失败')
    }
  }

  onMounted(loadProfile)

  return {
    user, favorites, histories, loading, saving, editing, message, profileForm, preference,
    displayName, avatarText, roleText, favoriteCount, queryCount, averageWait,
    loadProfile, saveProfile, cancelEdit, removeFavorite
  }
}