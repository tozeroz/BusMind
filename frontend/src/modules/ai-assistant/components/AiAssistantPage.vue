<!--
  文件：src/modules/ai-assistant/components/AiAssistantPage.vue
  用途：实现 ai-assistant 业务模块中的页面容器或业务组件。
  存放内容：该业务领域专属的界面结构、响应式状态和业务协调代码。
  实现功能：集中承载模块业务功能，并与路由入口、公共层和 API 层保持职责分离。
-->
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
        <strong>真实接口</strong>
        <span>POST /api/v1/ai/travel</span>
      </div>
    </aside>

    <main class="ai-chat-main">
      <header class="ai-chat-header">
        <div>
          <p class="eyebrow">AI 出行助手</p>
          <h2>公交自然语言问答</h2>
        </div>
        <div class="ai-header-actions">
          <RouterLink class="ghost-button" to="/home">返回主页</RouterLink>
          <span class="status-dot">DeepSeek 接入</span>
        </div>
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
import { sendAiMessage } from '@/api/ai'
import { getApiErrorMessage } from '@/api/response'

const input = ref('')
const activeConversation = ref(1)

function getCurrentClock() {
  const now = new Date()
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}

const conversations = ref([
  { id: 1, title: '新的出行咨询', desc: '真实接口会话' }
])

const messages = ref([
  {
    id: 1,
    role: 'assistant',
    time: getCurrentClock(),
    content: '你好，我会通过 POST /api/v1/ai/travel 回答公交出行问题；大模型不可用时后端会返回本地 fallback。'
  }
])

const quickQuestions = ['现在去教学楼怎么坐？', '哪条线路不太挤？', '下一班车多久到？']

const getTime = getCurrentClock

const ask = async (text) => {
  const question = text.trim()
  if (!question) return
  messages.value.push({ id: Date.now(), role: 'user', time: getTime(), content: question })
  const replyId = Date.now() + 1
  messages.value.push({
    id: replyId,
    role: 'assistant',
    time: getTime(),
    content: '正在请求后端 AI 出行助手...'
  })
  input.value = ''

  try {
    const response = await sendAiMessage({
      mode: 'qa',
      question,
      preference: 'balanced'
    })
    const answer = response.data?.answer
    const reminders = response.data?.reminders || []
    const reminderText = reminders.length ? `\n\n提醒：${reminders.join('；')}` : ''
    const fallbackText = response.data?.fallback ? '\n\n（当前为后端本地 fallback 回答）' : ''
    const traceText = response.trace_id ? `\n追踪号：${response.trace_id}` : ''
    const target = messages.value.find((message) => message.id === replyId)
    if (target) {
      target.content = `${answer || '后端未返回回答。'}${reminderText}${fallbackText}${traceText}`
      target.time = getTime()
    }
  } catch (error) {
    const target = messages.value.find((message) => message.id === replyId)
    if (target) {
      target.content = getApiErrorMessage(error, '后端 AI 接口暂不可用，请确认后端已启动。')
      target.time = getTime()
    }
  }
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
