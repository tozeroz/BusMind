<template>
  <main class="auth-page">
    <section class="auth-card">
      <p class="eyebrow">创建账号</p>
      <h1>注册智行公交</h1>
      <p class="muted">当前为演示版本，注册后直接进入系统首页。</p>

      <form class="form-block" @submit.prevent="register">
        <label>
          用户名
          <input v-model="form.name" placeholder="请输入用户名" />
        </label>
        <label>
          手机号
          <input v-model="form.phone" placeholder="请输入手机号" />
        </label>
        <label>
          密码
          <input v-model="form.password" type="password" placeholder="请输入密码" />
        </label>
        <button class="primary-button" type="submit">完成注册</button>
      </form>

      <div class="auth-actions">
        <RouterLink to="/login">返回登录</RouterLink>
      </div>
    </section>
  </main>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const form = reactive({ name: '', phone: '', password: '' })

const register = () => {
  router.push('/home')
}
</script>
