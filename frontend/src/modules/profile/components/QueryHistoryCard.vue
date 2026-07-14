<template>
  <section class="profile-card activity-card">
    <header class="profile-card-header">
      <div><p>历史信息</p><h2>查询记录</h2></div>
      <span class="profile-card-count">{{ histories.length }} 条</span>
    </header>
    <div v-if="histories.length" class="activity-list profile-scroll-list">
      <article v-for="item in histories" :key="item.history_id">
        <time :datetime="item.created_at">{{ formatDateTime(item.created_at) }}</time>
        <strong>{{ historyTitle(item) }}</strong>
        <p>{{ historySummary(item) }}</p>
        <span class="history-type">{{ queryTypeLabel(item.query_type) }}</span>
      </article>
    </div>
    <div v-else class="profile-empty-state">
      <strong>暂无历史记录</strong>
      <p>完成路线检索或使用 AI 出行助手后，后端生成的记录会显示在这里。</p>
    </div>
  </section>
</template>

<script setup>
defineProps({ histories: { type: Array, default: () => [] } })
const queryTypeLabel = (value) => ({ route_recommendation: '路线推荐', route_search: '路线检索', station_search: '站点查询', passenger_flow: '客流查询', ai_travel: 'AI 出行助手', ai_chat: 'AI 出行助手' }[value] || value || '出行查询')
const historyTitle = (item) => item.origin_name && item.destination_name ? `${item.origin_name} → ${item.destination_name}` : (item.query_title || item.title || queryTypeLabel(item.query_type))
const historySummary = (item) => item.result_summary || item.query_content || (item.selected_route_id ? `选中线路 ID：${item.selected_route_id}` : '本次查询暂无结果摘要')
const formatDateTime = (value) => {
  const date = new Date(value)
  return value && !Number.isNaN(date.getTime()) ? date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }) : '时间未知'
}
</script>

<style scoped>
.profile-card-count { color: rgba(255,255,255,.72); font-size: 13px; }
.profile-scroll-list { max-height: 470px; padding-right: 4px; overflow-y: auto; scrollbar-color: rgba(255,255,255,.45) rgba(255,255,255,.08); }
.history-type { width: fit-content; border: 1px solid rgba(255,255,255,.2); border-radius: 999px; padding: 4px 9px; color: rgba(255,255,255,.78); font-size: 11px; background: rgba(255,255,255,.08); }
.profile-empty-state { min-height: 230px; display: grid; place-content: center; gap: 9px; border: 1px dashed rgba(255,255,255,.28); border-radius: 9px; padding: 24px; text-align: center; background: rgba(255,255,255,.06); }
.profile-empty-state p { max-width: 280px; margin: 0; color: rgba(255,255,255,.68); line-height: 1.6; }
</style>
