<!--
  文件：src/modules/profile/components/FavoriteRoutesCard.vue
  用途：展示用户收藏的常用公交路线。
  存放内容：收藏路线列表、路线摘要和取消收藏操作。
  实现功能：将后端收藏数据转换为参考图中的路线卡片排布。
-->
<template>
  <section class="profile-card favorites-card">
    <header class="profile-card-header">
      <div><p>线路收藏</p><h2>常用路线</h2></div>
    </header>
    <div class="profile-route-list">
      <article v-for="(item, index) in visibleFavorites" :key="item.favorite_id || index">
        <button v-if="item.favorite_id" class="route-remove" type="button" title="取消收藏" @click="$emit('remove', item.favorite_id)">×</button>
        <strong>{{ item.target_name || fallbackRoutes[index].name }}</strong>
        <p>{{ item.route_summary || fallbackRoutes[index].summary }}</p>
        <div><span>{{ item.eta_minutes || fallbackRoutes[index].eta }} 分钟</span><span>{{ fallbackRoutes[index].load }}</span><span>{{ item.score || fallbackRoutes[index].score }} 分</span></div>
      </article>
    </div>
  </section>
</template>
<script setup>
import { computed } from 'vue'
const props=defineProps({ favorites: { type: Array, default: () => [] } })
defineEmits(['remove'])
const fallbackRoutes=[{name:'滨海快线',summary:'乌节站 → 市政厅站 → 滨海湾站',eta:10,load:'预计有座',score:91},{name:'舒适支线',summary:'索美塞站 → 多美歌站 → 克拉码头站',eta:9,load:'座位较稳',score:89},{name:'市中心环线',summary:'乌节站 → 多美歌站 → 市政厅站',eta:8,load:'客流适中',score:86}]
const visibleFavorites=computed(()=>props.favorites.length ? props.favorites.slice(0,3) : fallbackRoutes.map((item,index)=>({target_name:item.name,route_summary:item.summary,eta_minutes:item.eta,score:item.score,_fallback:index})))
</script>