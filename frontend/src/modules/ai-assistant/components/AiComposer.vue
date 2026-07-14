<template>
  <div class="ai-composer">
    <div class="ai-quick-prompts">
      <button v-for="item in quickQuestions" :key="item" type="button" :disabled="loading" @click="$emit('send', item)">
        {{ item }}
      </button>
    </div>
    <form class="map-ai-input" @submit.prevent="submit">
      <input v-model="input" placeholder="&#x4F8B;&#x5982;&#xFF1A;&#x54EA;&#x6761;&#x8DEF;&#x7EBF;&#x4E0D;&#x592A;&#x6324;&#xFF1F;" />
      <button class="primary-button" type="submit" :disabled="loading || !input.trim()">
        {{ loading ? '\u53d1\u9001\u4e2d' : '\u53d1\u9001' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ loading: { type: Boolean, default: false } })
const emit = defineEmits(['send'])
const input = ref('')
const quickQuestions = ['\u54ea\u6761\u8def\u7ebf\u6700\u5feb', '\u54ea\u6761\u8def\u7ebf\u4e0d\u592a\u6324', '\u4e3a\u4ec0\u4e48\u63a8\u8350\u8fd9\u6761']

function submit() {
  const text = input.value.trim()
  if (!text) return
  emit('send', text)
  input.value = ''
}
</script>

<style scoped>
.ai-quick-prompts { display:flex; gap:6px; margin-top:10px; overflow-x:auto; padding-bottom:2px; }.ai-quick-prompts button { flex:0 0 auto; border:1px solid rgba(255,255,255,.22); border-radius:999px; padding:6px 9px; color:rgba(255,255,255,.82); font-size:10px; background:rgba(255,255,255,.09); cursor:pointer; }.ai-quick-prompts button:disabled { opacity:.5; }
</style>

