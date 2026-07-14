<template>
  <section class="map-ai-card">
    <div class="section-title ai-panel-header">
      <div>
        <p class="eyebrow">AI &#x51FA;&#x884C;&#x52A9;&#x624B;</p>
        <h3>&#x8DEF;&#x7EBF;&#x5EFA;&#x8BAE;</h3>
        <small v-if="conversationId">&#x4F1A;&#x8BDD; {{ conversationId.slice(0, 8) }}</small>
      </div>
      <div class="ai-panel-actions">
        <button class="ghost-button compact-ghost" type="button" @click="$emit('new-chat')">&#x65B0;&#x5EFA;&#x5BF9;&#x8BDD;</button>
        <button class="ghost-button compact-ghost" type="button" @click="$emit('close')">&#x5173;&#x95ED;</button>
      </div>
    </div>

    <AiMessageList :messages="messages" />

    <div v-if="status === 'needs_clarification' && missingFields.length" class="ai-missing-fields">
      <span>&#x5F85;&#x8865;&#x5145;</span>
      <b v-for="field in missingFields" :key="field">{{ fieldLabel(field) }}</b>
    </div>

    <AiRouteCard
      v-if="route"
      :route="route"
      @map="$emit('map', $event)"
      @explain="$emit('explain')"
      @next="$emit('next')"
    />

    <AiComposer :loading="loading" @send="$emit('send', $event)" />
  </section>
</template>

<script setup>
import AiComposer from './AiComposer.vue'
import AiMessageList from './AiMessageList.vue'
import AiRouteCard from './AiRouteCard.vue'

defineProps({
  messages: { type: Array, default: () => [] },
  route: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  status: { type: String, default: 'idle' },
  missingFields: { type: Array, default: () => [] },
  conversationId: { type: String, default: '' }
})
defineEmits(['close', 'new-chat', 'send', 'map', 'explain', 'next'])

const fieldLabel = (field) => ({
  start_station_id: '\u8d77\u70b9',
  end_station_id: '\u7ec8\u70b9',
  route_id: '\u8def\u7ebf',
  'context.items': '\u8def\u7ebf\u4e0a\u4e0b\u6587'
})[field] || field
</script>

<style scoped>
.map-ai-card { grid-template-rows:auto minmax(96px,1fr) auto auto auto; }.ai-panel-header small { display:block; margin-top:4px; color:rgba(255,255,255,.5); font-size:9px; }.ai-panel-actions { display:flex; gap:6px; }.ai-panel-actions button { min-height:30px; padding:0 9px; font-size:10px; }.ai-missing-fields { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin-top:8px; color:rgba(255,255,255,.62); font-size:10px; }.ai-missing-fields b { border-radius:999px; padding:5px 8px; color:#17334a; background:#ffd09c; }
</style>

