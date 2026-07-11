<template>
  <section class="page-grid">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">个人中心</p>
          <h2>{{ user.nickname || user.username || '用户资料' }}</h2>
          <p class="muted">账号角色：{{ user.role || 'passenger' }}</p>
        </div>
        <button class="ghost-button" type="button" :disabled="loading" @click="loadProfile">
          {{ loading ? '加载中' : '刷新' }}
        </button>
      </div>

      <form class="admin-form-row" @submit.prevent="saveNickname">
        <input v-model="nickname" maxlength="50" placeholder="修改昵称" />
        <button class="primary-button" type="submit">保存昵称</button>
      </form>
      <p v-if="message" class="form-tip">{{ message }}</p>
    </div>

    <div class="detail-grid">
      <section class="panel">
        <div class="section-title">
          <div><p class="eyebrow">收藏</p><h3>收藏线路</h3></div>
        </div>
        <form class="admin-form-row" @submit.prevent="addFavorite">
          <input v-model.number="favoriteForm.target_id" type="number" min="1" placeholder="线路 ID" />
          <input v-model="favoriteForm.target_name" placeholder="线路名称" />
          <button class="primary-button" type="submit">添加</button>
        </form>
        <div class="card-list compact">
          <article v-for="item in favorites" :key="item.favorite_id" class="vehicle-row">
            <div>
              <strong>{{ item.target_name || `线路 ${item.target_id}` }}</strong>
              <p>{{ item.favorite_type }} · ID {{ item.target_id }}</p>
            </div>
            <button class="ghost-button" type="button" @click="removeFavorite(item.favorite_id)">取消收藏</button>
          </article>
          <p v-if="!favorites.length" class="muted">暂无收藏。</p>
        </div>
      </section>

      <section class="panel">
        <div class="section-title">
          <div><p class="eyebrow">历史</p><h3>最近查询</h3></div>
        </div>
        <div class="card-list compact">
          <article v-for="item in histories" :key="item.history_id" class="vehicle-card">
            <strong>{{ item.origin_name || '未知起点' }} → {{ item.destination_name || '未知终点' }}</strong>
            <p>{{ item.result_summary || item.query_content || item.query_type }}</p>
            <span>{{ formatTime(item.created_at) }}</span>
          </article>
          <p v-if="!histories.length" class="muted">暂无查询历史。</p>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import {
  addUserFavorite,
  deleteUserFavorite,
  getCurrentUser,
  getUserFavorites,
  getUserQueryHistory,
  updateCurrentUser
} from '@/api/user'

const user = reactive({})
const nickname = ref('')
const favorites = ref([])
const histories = ref([])
const favoriteForm = reactive({ target_id: null, target_name: '' })
const loading = ref(false)
const message = ref('')

const loadProfile = async () => {
  loading.value = true
  message.value = ''
  try {
    const [userResponse, favoritesResponse, historyResponse] = await Promise.all([
      getCurrentUser(),
      getUserFavorites({ page: 1, limit: 20 }),
      getUserQueryHistory({ page: 1, limit: 20 })
    ])
    const userData = userResponse.data?.user || userResponse.data || {}
    Object.assign(user, userData)
    nickname.value = user.nickname || ''
    favorites.value = favoritesResponse.data?.favorites || []
    histories.value = historyResponse.data?.histories || []
  } catch (error) {
    message.value = error?.response?.status === 401 ? '登录已失效，请重新登录' : '个人数据加载失败'
  } finally {
    loading.value = false
  }
}

const saveNickname = async () => {
  try {
    const response = await updateCurrentUser({ nickname: nickname.value.trim() })
    Object.assign(user, response.data || {})
    message.value = '昵称已更新'
  } catch (error) {
    message.value = error?.response?.data?.message || '昵称更新失败'
  }
}

const addFavorite = async () => {
  if (!favoriteForm.target_id) {
    message.value = '请输入有效线路 ID'
    return
  }
  try {
    await addUserFavorite({
      favorite_type: 'line',
      target_id: Number(favoriteForm.target_id),
      target_name: favoriteForm.target_name.trim()
    })
    favoriteForm.target_id = null
    favoriteForm.target_name = ''
    await loadProfile()
    message.value = '收藏已添加'
  } catch (error) {
    message.value = error?.response?.data?.message || '添加收藏失败'
  }
}

const removeFavorite = async (favoriteId) => {
  try {
    await deleteUserFavorite(favoriteId)
    favorites.value = favorites.value.filter((item) => item.favorite_id !== favoriteId)
    message.value = '收藏已取消'
  } catch (error) {
    message.value = error?.response?.data?.message || '取消收藏失败'
  }
}

const formatTime = (value) => value ? new Date(value).toLocaleString() : '未知时间'

onMounted(loadProfile)
</script>
