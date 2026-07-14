<template>
  <section class="profile-card favorites-card">
    <header class="profile-card-header">
      <div><p>线路收藏</p><h2>收藏线路</h2></div>
      <span class="profile-card-count">{{ favorites.length }} 条</span>
    </header>
    <div v-if="favorites.length" class="profile-route-list profile-scroll-list">
      <article v-for="item in favorites" :key="item.favorite_id">
        <button class="route-remove" type="button" title="取消收藏" :aria-label="`取消收藏 ${favoriteName(item)}`" @click="$emit('remove', item.favorite_id)">×</button>
        <strong>{{ favoriteName(item) }}</strong>
        <p>已收藏的{{ favoriteType(item.favorite_type) }}，可通过线路 ID 快速识别。</p>
        <div><span>{{ favoriteType(item.favorite_type) }}</span><span>ID {{ item.target_id }}</span><span>{{ formatDate(item.created_at) }}</span></div>
      </article>
    </div>
    <div v-else class="profile-empty-state">
      <strong>还没有收藏线路</strong>
      <p>在首页选中一条线路后，点击“收藏线路”即可保存到这里。</p>
    </div>
  </section>
</template>

<script setup>
defineProps({ favorites: { type: Array, default: () => [] } })
defineEmits(['remove'])
const favoriteName = (item) => item.target_name || `线路 ${item.target_id}`
const favoriteType = (value) => ['route', 'line'].includes(value) ? '公交线路' : (value || '收藏')
const formatDate = (value) => {
  const date = new Date(value)
  return value && !Number.isNaN(date.getTime()) ? date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) : '时间未知'
}
</script>

<style scoped>
.profile-card-count { color: rgba(255,255,255,.72); font-size: 13px; }
.profile-scroll-list { max-height: 470px; padding-right: 4px; overflow-y: auto; scrollbar-color: rgba(255,255,255,.45) rgba(255,255,255,.08); }
.profile-empty-state { min-height: 230px; display: grid; place-content: center; gap: 9px; border: 1px dashed rgba(255,255,255,.28); border-radius: 9px; padding: 24px; text-align: center; background: rgba(255,255,255,.06); }
.profile-empty-state p { max-width: 280px; margin: 0; color: rgba(255,255,255,.68); line-height: 1.6; }
</style>
