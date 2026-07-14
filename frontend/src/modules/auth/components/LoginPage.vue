<!--
  文件：src/modules/auth/components/LoginPage.vue
  用途：实现 auth 业务模块中的页面容器或业务组件。
  存放内容：该业务领域专属的界面结构、响应式状态和业务协调代码。
  实现功能：集中承载模块业务功能，并与路由入口、公共层和 API 层保持职责分离。
-->
<template>
  <main class="auth-page">
    <section class="auth-logo-panel">
      <div class="logo-slot">
        <img src="/logo/busmind-bus-logo.png" alt="智行公交公交车标识" />
      </div>
      <div>
        <p class="eyebrow">BusMind</p>
        <h1>智行公交</h1>
        <p>基于客流数据与 AI 助手的公交舒适出行系统</p>
      </div>
    </section>

    <section class="auth-card">
      <p class="eyebrow">账号登录</p>
      <h1>欢迎使用</h1>
      <p class="muted">登录后将根据账号角色进入乘客端或管理员端。</p>

      <form class="form-block" @submit.prevent="login">
        <label>
          账号
          <input v-model="form.account" placeholder="请输入账号" />
        </label>
        <label>
          密码
          <input v-model="form.password" type="password" placeholder="请输入密码" />
        </label>
        <p v-if="errorMessage" class="form-tip">{{ errorMessage }}</p>
        <button class="primary-button" type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="auth-actions">
        <RouterLink to="/register">注册账号</RouterLink>
        <span>使用后端账号与权限信息登录</span>
      </div>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearAuthToken, getCurrentUser, loginUser, saveAuthSession } from '@/api/user'
import { getApiErrorMessage } from '@/api/response'

const router = useRouter()
const form = reactive({ account: '', password: '' })
const loading = ref(false)
const errorMessage = ref('')

const login = async () => {
  const username = form.account.trim()
  if (!username || !form.password) {
    errorMessage.value = '请输入账号和密码'
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    const response = await loginUser({ username, password: form.password })
    const result = response?.data || {}
    if (!result?.access_token) throw new Error('登录响应缺少访问令牌')

    // 先保存 Token，再在登录响应未携带完整用户时请求 /users/me。
    saveAuthSession({ accessToken: result.access_token, user: result.user || null })
    let currentUser = result.user || null
    if (!currentUser?.role) {
      const meResponse = await getCurrentUser()
      currentUser = meResponse?.data?.user || meResponse?.data || currentUser
      saveAuthSession({ accessToken: result.access_token, user: currentUser })
    }
    router.push(currentUser?.role === 'admin' ? '/admin' : '/home')
  } catch (error) {
    clearAuthToken()
    errorMessage.value = getApiErrorMessage(error, '登录失败，请检查账号和密码')
  } finally {
    loading.value = false
  }
}
</script>
