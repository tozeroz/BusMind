<!--
  文件：src/modules/auth/components/RegisterPage.vue
  用途：实现 auth 业务模块中的页面容器或业务组件。
  存放内容：该业务领域专属的界面结构、响应式状态和业务协调代码。
  实现功能：集中承载模块业务功能，并与路由入口、公共层和 API 层保持职责分离。
-->
<template>
  <main class="auth-page">
    <section class="auth-card">
      <p class="eyebrow">创建账号</p>
      <h1>注册智行公交</h1>
      <p class="muted">注册成功后返回登录页。</p>

      <form class="form-block" @submit.prevent="register">
        <label>
          用户名
          <input v-model="form.username" minlength="4" maxlength="32" placeholder="4-32 位用户名" />
        </label>
        <label>
          昵称
          <input v-model="form.nickname" maxlength="32" placeholder="请输入昵称（可选）" />
        </label>
        <label>
          邮箱
          <input v-model="form.email" type="email" placeholder="请输入邮箱地址" />
        </label>
        <div class="code-row">
          <label class="code-label">
            验证码
            <input v-model="form.verificationCode" maxlength="6" placeholder="6 位数字" inputmode="numeric" />
          </label>
          <button
            type="button"
            class="countdown-button"
            :disabled="codeCooldown > 0 || codeSending"
            @click="sendCode"
          >
            {{ codeButtonText }}
          </button>
        </div>
        <label>
          密码
          <input v-model="form.password" type="password" minlength="8" maxlength="64" placeholder="8-64 位密码" />
        </label>
        <label>
          确认密码
          <input v-model="form.passwordConfirm" type="password" minlength="8" maxlength="64" placeholder="请再次输入密码" />
        </label>
        <p v-if="message" class="form-tip">{{ message }}</p>
        <button class="primary-button" type="submit" :disabled="registering">
          {{ registering ? '注册中...' : '完成注册' }}
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
import { registerUser, sendRegisterEmailCode } from '@/api/user'
import { getApiErrorMessage } from '@/api/response'

const router = useRouter()
const form = reactive({
  username: '',
  nickname: '',
  email: '',
  verificationCode: '',
  password: '',
  passwordConfirm: '',
})
const registering = ref(false)
const codeSending = ref(false)
const codeCooldown = ref(0)
const message = ref('')

let cooldownTimer = null

const EMAIL_RE = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/

const codeButtonText = ref('发送验证码')

function startCooldown() {
  codeCooldown.value = 60
  codeButtonText.value = `${codeCooldown.value}s`
  cooldownTimer = setInterval(() => {
    codeCooldown.value--
    if (codeCooldown.value <= 0) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
      codeButtonText.value = '发送验证码'
    } else {
      codeButtonText.value = `${codeCooldown.value}s`
    }
  }, 1000)
}

const sendCode = async () => {
  const email = form.email.trim()
  if (!email || !EMAIL_RE.test(email)) {
    message.value = '请输入正确的邮箱地址'
    return
  }

  codeSending.value = true
  message.value = ''
  try {
    await sendRegisterEmailCode({ email })
    message.value = '验证码已发送，请查收邮箱'
    startCooldown()
  } catch (error) {
    message.value = getApiErrorMessage(error, '验证码发送失败，请稍后重试')
  } finally {
    codeSending.value = false
  }
}

const register = async () => {
  const username = form.username.trim()
  const nickname = form.nickname.trim()
  const email = form.email.trim()
  const verificationCode = form.verificationCode.trim()
  const password = form.password
  const passwordConfirm = form.passwordConfirm

  if (username.length < 4 || username.length > 32) {
    message.value = '用户名需 4-32 位'
    return
  }
  if (!email || !EMAIL_RE.test(email)) {
    message.value = '请输入正确的邮箱地址'
    return
  }
  if (!/^\d{6}$/.test(verificationCode)) {
    message.value = '验证码为 6 位数字'
    return
  }
  if (password.length < 8 || password.length > 64) {
    message.value = '密码需 8-64 位'
    return
  }
  if (password !== passwordConfirm) {
    message.value = '两次密码不一致'
    return
  }

  registering.value = true
  message.value = ''
  try {
    const response = await registerUser({
      username,
      password,
      password_confirm: passwordConfirm,
      email,
      verification_code: verificationCode,
      nickname,
    })
    if (response?.code !== 0) {
      message.value = response?.message || '注册失败，请稍后重试'
      return
    }
    router.push({ path: '/login', query: { registered: '1' } })
  } catch (error) {
    message.value = getApiErrorMessage(error, '注册失败，请稍后重试')
  } finally {
    registering.value = false
  }
}
</script>

<style scoped>
.code-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: end;
}

.code-label {
  display: grid;
  gap: 6px;
}

.countdown-button {
  min-height: 42px;
  border: 0;
  border-radius: 30px;
  padding: 0 18px;
  color: #fff;
  background: rgba(255, 255, 255, 0.18);
  font-size: 14px;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.2s;
}

.countdown-button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.28);
}

.countdown-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>