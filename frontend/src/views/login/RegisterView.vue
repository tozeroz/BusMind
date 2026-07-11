<template>
  <main class="auth-page">
    <section class="auth-card">
      <p class="eyebrow">创建账号</p>
      <h1>注册智行公交</h1>
      <p class="muted">注册成功后返回登录页。</p>

      <form class="form-block" @submit.prevent="register">
        <label>
          用户名
          <input v-model="form.name" minlength="4" maxlength="32" placeholder="4-32 位用户名" />
        </label>
        <label>
          昵称
          <input v-model="form.nickname" maxlength="50" placeholder="请输入昵称（可选）" />
        </label>
        <label>
          密码
          <input v-model="form.password" type="password" minlength="8" maxlength="64" placeholder="8-64 位密码" />
        </label>
        <p v-if="message" class="form-tip">{{ message }}</p>
        <button class="primary-button" type="submit" :disabled="loading">
          {{ loading ? '注册中...' : '完成注册' }}
        </button>
      </form>

      <div class="auth-actions">
        <RouterLink to="/login">返回登录</RouterLink>
      </div>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { registerUser } from '@/api/user'

const router = useRouter()
const form = reactive({ name: '', nickname: '', password: '' })
const loading = ref(false)
const message = ref('')

const register = async () => {
  const username = form.name.trim()
  if (username.length < 4 || form.password.length < 8) {
    message.value = '用户名至少 4 位，密码至少 8 位'
    return
  }

  loading.value = true
  message.value = ''
  try {
    const response = await registerUser({
      username,
      password: form.password,
      nickname: form.nickname.trim(),
      role: 'passenger'
    })
    if (response?.code !== 0) {
      message.value = response?.message || '注册失败，请稍后重试'
      return
    }
    router.push({ path: '/login', query: { registered: '1' } })
  } catch (error) {
    message.value = error?.response?.data?.message
      || error?.response?.data?.detail?.message
      || error?.message
      || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>
