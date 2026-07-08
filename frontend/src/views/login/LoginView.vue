<template>
  <main class="auth-page">
    <section class="auth-logo-panel">
      <div class="logo-slot">
        <!-- 后续将 logo 图片放到 frontend/public/logo/ 目录后，把下面注释打开并修改文件名即可 -->
        <!-- <img src="/logo/busmind-logo.png" alt="智行公交 Logo" /> -->
        <span>Logo</span>
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
      <p class="muted">当前为演示版本，可选择进入乘客端或管理员端。</p>

      <form class="form-block" @submit.prevent>
        <label>
          账号
          <input v-model="form.account" placeholder="请输入账号" />
        </label>
        <label>
          密码
          <input v-model="form.password" type="password" placeholder="请输入密码" />
        </label>
      </form>

      <div class="login-choice-grid">
        <button class="primary-button" type="button" @click="goClient">进入乘客端</button>
        <button class="ghost-button" type="button" @click="goAdmin">进入管理员端</button>
      </div>

      <div class="auth-actions">
        <RouterLink to="/register">注册账号</RouterLink>
        <span>后续接入数据库后按账号权限跳转</span>
      </div>
    </section>
  </main>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const form = reactive({ account: 'demo', password: '123456' })

const goClient = () => {
  router.push('/home')
}

const goAdmin = () => {
  router.push('/admin')
}
</script>
