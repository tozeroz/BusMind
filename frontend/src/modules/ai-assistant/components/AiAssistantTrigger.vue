<template>
  <button class="ai-floating-button" type="button" title="AI &#x51FA;&#x884C;&#x52A9;&#x624B;" @mousedown.stop="$emit('drag-start', $event)" @click="$emit('toggle')">AI</button>
</template>

<script setup>
defineEmits(['drag-start', 'toggle'])
</script>
