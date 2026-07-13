<!--
  文件：src/modules/profile/components/PreferenceWeightsCard.vue
  用途：展示并调整个人路线推荐权重。
  存放内容：舒适、效率和少步行三个可交互滑杆。
  实现功能：提供与参考图一致的偏好设置区域和即时数值反馈。
-->
<template>
  <section class="profile-card preference-card">
    <header class="profile-card-header"><div><p>偏好设置</p><h2>推荐权重</h2></div></header>
    <label v-for="item in items" :key="item.key">
      <span>{{ item.label }}</span><input v-model.number="preference[item.key]" type="range" min="0" max="100" /><strong>{{ preference[item.key] }}%</strong>
    </label>
  </section>
</template>
<script setup>
defineProps({ preference:{type:Object,required:true} })
const items=[{key:'comfort',label:'舒适度'},{key:'speed',label:'效率'},{key:'walking',label:'少步行'}]
</script>