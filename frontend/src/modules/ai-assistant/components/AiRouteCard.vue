<template>
  <div class="ai-route-result">
    <div>
      <p class="eyebrow">&#x5173;&#x8054;&#x8DEF;&#x7EBF;</p>
      <h4>{{ route.title }}</h4>
    </div>
    <div class="recommend-meta compact-meta">
      <span>{{ route.eta }} &#x5206;&#x949F;</span>
      <span>{{ route.load }}</span>
      <span>{{ route.score }} &#x5206;</span>
    </div>
    <div class="ai-route-actions">
      <button class="primary-button" type="button" @click="$emit('map', route)">&#x5730;&#x56FE;&#x67E5;&#x770B;</button>
      <button class="ghost-button" type="button" @click="$emit('explain')">&#x4E3A;&#x4EC0;&#x4E48;&#x63A8;&#x8350;</button>
      <button class="ghost-button" type="button" @click="$emit('next')">&#x6362;&#x4E00;&#x6761;</button>
    </div>
  </div>
</template>

<script setup>
defineProps({ route: { type: Object, required: true } })
defineEmits(['map', 'explain', 'next'])
</script>

<style scoped>
.ai-route-result { grid-template-columns:1fr; }.ai-route-actions { display:grid; grid-template-columns:1fr 1fr; gap:7px; }.ai-route-actions .primary-button { grid-row:auto; grid-column:1/-1; }.ai-route-actions button { min-height:32px; padding:0 9px; font-size:11px; }
</style>

