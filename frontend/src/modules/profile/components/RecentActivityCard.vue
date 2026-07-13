<!--
  文件：src/modules/profile/components/RecentActivityCard.vue
  用途：展示用户最近的公交查询与推荐记录。
  存放内容：时间、记录标题和结果摘要。
  实现功能：以时间顺序呈现最近三条出行足迹。
-->
<template>
  <section class="profile-card activity-card">
    <header class="profile-card-header"><div><p>最近记录</p><h2>出行足迹</h2></div></header>
    <div class="activity-list">
      <article v-for="(item,index) in visibleHistory" :key="item.history_id || index">
        <time>{{ formatClock(item.created_at) || fallback[index].time }}</time>
        <strong>{{ title(item,index) }}</strong>
        <p>{{ item.result_summary || item.query_content || fallback[index].summary }}</p>
      </article>
    </div>
  </section>
</template>
<script setup>
import { computed } from 'vue'
const props=defineProps({ histories:{type:Array,default:()=>[]} })
const fallback=[{time:'08:32',title:'查询滨海湾路线',summary:'选择滨海快线，预计 10 分钟到达'},{time:'12:10',title:'查看乌节站客流',summary:'当前客流适中，建议提前 8 分钟出发'},{time:'18:24',title:'AI 助手推荐',summary:'按“少走路”偏好生成舒适支线方案'}]
const visibleHistory=computed(()=>props.histories.length?props.histories.slice(0,3):fallback)
const formatClock=value=>{if(!value)return '';const date=new Date(value);return Number.isNaN(date.getTime())?'':date.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false})}
const title=(item,index)=>item.title||item.query_title||(item.origin_name&&item.destination_name?`${item.origin_name} → ${item.destination_name}`:fallback[index].title)
</script>