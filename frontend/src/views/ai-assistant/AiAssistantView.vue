<template>
  <section class="ai-chat-shell">
    <aside class="ai-chat-sider">
      <button class="new-chat-button" type="button" @click="newChat">新建对话</button>

      <div class="conversation-list">
        <button
          v-for="item in conversations"
          :key="item.id"
          class="conversation-item"
          :class="{ active: item.id === activeConversation }"
          type="button"
          @click="activeConversation = item.id"
        >
          <span>{{ item.title }}</span>
          <small>{{ item.desc }}</small>
        </button>
      </div>

      <div class="sider-note">
        <strong>后端预留</strong>
        <span>POST /api/ai/chat</span>
      </div>
    </aside>

    <main class="ai-chat-main">
      <header class="ai-chat-header">
        <div>
          <p class="eyebrow">AI 出行助手</p>
          <h2>公交自然语言问答</h2>
        </div>
        <span class="status-dot">演示模式</span>
      </header>

      <div class="ai-message-list">
        <article
          v-for="message in messages"
          :key="message.id"
          class="ai-message"
          :class="{ user: message.role === 'user' }"
        >
          <div class="avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
          <div class="message-body">
            <div class="message-meta">
              <strong>{{ message.role === 'user' ? '乘客' : '智行助手' }}</strong>
              <span>{{ message.time }}</span>
            </div>
            <p>{{ message.content }}</p>
          </div>
        </article>
      </div>

      <div class="prompt-row">
        <button v-for="item in quickQuestions" :key="item" type="button" @click="ask(item)">
          {{ item }}
        </button>
      </div>

      <form class="ai-input-bar" @submit.prevent="ask(input)">
        <textarea
          v-model="input"
          rows="1"
          placeholder="请输入你的出行问题，例如：现在去教学楼哪条线路不太挤？"
          @keydown.enter.exact.prevent="ask(input)"
        ></textarea>
        <button class="send-button" type="submit">发送</button>
      </form>
    </main>
  </section>
</template>

<script setup>
import { ref } from 'vue'

const input = ref('')
const activeConversation = ref(1)

const conversations = ref([
  { id: 1, title: '去教学楼怎么坐', desc: '少拥挤路线' },
  { id: 2, title: '下一班车多久到', desc: 'ETA 查询' },
  { id: 3, title: '图书馆返程建议', desc: '舒适出行' }
])

const messages = ref([
  {
    id: 1,
    role: 'assistant',
    time: '09:20',
    content: '你好，我可以结合公交线路、车辆 ETA 和客流数据，为你生成更容易理解的出行建议。'
  },
  {
    id: 2,
    role: 'user',
    time: '09:21',
    content: '现在从宿舍区去教学楼，哪条线路不太挤？'
  },
  {
    id: 3,
    role: 'assistant',
    time: '09:21',
    content: '建议优先查看校园 2 号线。它预计等待 8 分钟，当前客流为适中，整体乘坐体验比校园 1 号线更舒适。'
  }
])

const quickQuestions = ['现在去教学楼怎么坐？', '哪条线路不太挤？', '下一班车多久到？']

const getTime = () => {
  const now = new Date()
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}

const ask = (text) => {
  const question = text.trim()
  if (!question) return
  messages.value.push({ id: Date.now(), role: 'user', time: getTime(), content: question })
  messages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    time: getTime(),
    content: '根据当前模拟数据，建议选择校园 2 号线。后续接入后端后，这里会调用 AI 接口并结合实时客流量、ETA 和线路数据生成回答。'
  })
  input.value = ''
}

const newChat = () => {
  const id = Date.now()
  conversations.value.unshift({ id, title: '新的出行咨询', desc: '待输入问题' })
  activeConversation.value = id
  messages.value = [
    {
      id: id + 1,
      role: 'assistant',
      time: getTime(),
      content: '新的对话已创建，请输入你的公交出行问题。'
    }
  ]
}
</script>
