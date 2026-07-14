<template>
  <div class="map-ai-messages" aria-live="polite">
    <article v-for="message in messages" :key="message.id" :class="['mini-message', message.role]">
      <p>{{ message.content }}</p>
    </article>
  </div>
</template>

<script setup>
defineProps({ messages: { type: Array, default: () => [] } })
</script>

