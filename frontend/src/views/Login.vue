<template>
  <div class="login-page">
    <transition name="login-card-switch" mode="out-in">
      <div class="login-card" :key="mode">
        <h1 class="title">HBCloud 开放网盘</h1>
        <p class="subtitle">请先登录后再访问网盘功能</p>

        <div class="tabs">
          <button
            class="tab-btn"
            :class="{ active: mode === 'login' }"
            type="button"
            @click="mode = 'login'"
          >
            登录
          </button>
          <button
            class="tab-btn"
            :class="{ active: mode === 'register' }"
            type="button"
            @click="mode = 'register'"
          >
            注册
          </button>
        </div>

        <transition name="login-switch" mode="out-in">
          <form
            v-if="mode === 'login'"
            key="login"
            class="form"
            @submit.prevent="onLogin"
          >
            <label class="field">
              <span class="label">手机号</span>
              <input v-model="loginPhone" type="text" placeholder="请输入手机号" />
            </label>
            <label class="field">
              <span class="label">密码</span>
              <input v-model="loginPassword" type="password" placeholder="请输入登录密码" />
            </label>
            <button class="submit" type="submit" :disabled="submitting">
              {{ submitting ? '处理中…' : '登录' }}
            </button>
          </form>
          <form
            v-else
            key="register"
            class="form"
            @submit.prevent="onRegister"
          >
            <label class="field">
              <span class="label">手机号</span>
              <input v-model="regPhone" type="text" placeholder="请输入手机号" />
            </label>
            <label class="field">
              <span class="label">姓名</span>
              <input v-model="regName" type="text" placeholder="请输入姓名" />
            </label>
            <label class="field">
              <span class="label">管理员邀请码</span>
              <input v-model="regInvite" type="text" placeholder="请输入管理员提供的邀请码" />
            </label>
            <label class="field">
              <span class="label">密码</span>
              <input v-model="regPassword" type="password" placeholder="请设置登录密码" />
            </label>
            <label class="field">
              <span class="label">确认密码</span>
              <input v-model="regPassword2" type="password" placeholder="请再次输入密码" />
            </label>
            <button class="submit" type="submit" :disabled="submitting">
              {{ submitting ? '处理中…' : '注册并登录' }}
            </button>
          </form>
        </transition>

        <p class="tip-row">
          <span class="tip-text">若忘记密码，请联系系统管理员。</span>
          <span class="tip-actions">
            <button type="button" class="link-btn" @click="showChangePwd = true">
              修改密码
            </button>
          </span>
        </p>
      </div>
    </transition>

    <transition name="change-pwd-popup" mode="out-in">
      <div v-if="showChangePwd" class="mask" @click="closeChangePwd">
        <div class="dialog" @click.stop>
          <div class="dialog-title">修改密码</div>
          <div class="dialog-body">
            <form class="form" @submit.prevent="onChangePassword">
              <label class="field">
                <span class="label">手机号</span>
                <input v-model="cpPhone" type="text" placeholder="请输入账号手机号" />
              </label>
              <label class="field">
                <span class="label">原密码</span>
                <input v-model="cpOldPassword" type="password" placeholder="请输入当前密码" />
              </label>
              <label class="field">
                <span class="label">新密码</span>
                <input v-model="cpNewPassword" type="password" placeholder="请输入新密码" />
              </label>
              <label class="field">
                <span class="label">确认新密码</span>
                <input v-model="cpNewPassword2" type="password" placeholder="请再次输入新密码" />
              </label>
              <div class="dialog-footer equal-buttons">
                <button class="submit-btn" type="submit" :disabled="submittingChange">
                  {{ submittingChange ? '处理中…' : '保存' }}
                </button>
                <button type="button" class="cancel-btn" @click="closeChangePwd">取消</button>
              </div>
            </form>
            <p class="cp-tip">如已忘记密码，请联系系统管理员协助重置账号密码。</p>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const mode = ref('login')
const submitting = ref(false)

const loginPhone = ref('')
const loginPassword = ref('')

const regPhone = ref('')
const regName = ref('')
const regInvite = ref('')
const regPassword = ref('')
const regPassword2 = ref('')

const errorTries = ref(0) // 当前会话内密码错误次数

const showChangePwd = ref(false)
const cpPhone = ref('')
const cpOldPassword = ref('')
const cpNewPassword = ref('')
const cpNewPassword2 = ref('')
const submittingChange = ref(false)

onMounted(() => {
  // 若本地已有登录用户信息，则默认填充手机号
  const raw = localStorage.getItem('hbcloud_user')
  if (raw) {
    try {
      const u = JSON.parse(raw)
      if (u && u.phone) cpPhone.value = u.phone
    } catch {
      // ignore
    }
  }
})

const saveLogin = (token, user) => {
  if (token) localStorage.setItem('hbcloud_token', token)
  if (user) localStorage.setItem('hbcloud_user', JSON.stringify(user))
}

const goAfterLogin = () => {
  const redirectRaw = route.query.redirect || '/'
  let redirect = String(redirectRaw)
  // 如果 redirect 包含 hash 前缀（例如 "#/files"），去掉前导 '#'
  if (redirect.startsWith('#')) {
    redirect = redirect.slice(1)
  }
  router.replace(redirect)
}

const closeChangePwd = () => {
  showChangePwd.value = false
  cpOldPassword.value = ''
  cpNewPassword.value = ''
  cpNewPassword2.value = ''
}

const onLogin = async () => {
  if (!loginPhone.value || !loginPassword.value) {
    alert('请填写手机号和密码')
    return
  }
  submitting.value = true
  try {
    const { data } = await axios.post('/api/auth/login', {
      phone: loginPhone.value.trim(),
      password: loginPassword.value,
    })
    // 登录成功：清空错误次数
    errorTries.value = 0
    saveLogin(data.token, data.user)
    goAfterLogin()
  } catch (e) {
    errorTries.value += 1
    const baseMsg = (e.response && e.response.data && e.response.data.detail) || '登录失败'
    const remain = Math.max(0, 5 - errorTries.value)
    const extra = remain > 0
      ? `\n提示：账号或密码错误。已错误 ${errorTries.value} 次（最多 5 次，之后账号将暂时锁定几分钟）。`
      : `\n提示：密码连续输错次数过多，账号可能已被暂时锁定，请稍后再试。`
    alert(baseMsg + extra)
  } finally {
    submitting.value = false
  }
}

const onRegister = async () => {
  if (!regPhone.value || !regName.value || !regInvite.value || !regPassword.value || !regPassword2.value) {
    alert('请完整填写所有字段')
    return
  }
  if (regPassword.value !== regPassword2.value) {
    alert('两次输入的密码不一致')
    return
  }
  submitting.value = true
  try {
    const payload = {
      phone: regPhone.value.trim(),
      name: regName.value.trim(),
      invite_code: regInvite.value.trim(),
      password: regPassword.value,
      password_confirm: regPassword2.value,
    }
    const { data } = await axios.post('/api/auth/register', payload)
    saveLogin(data.token, data.user)
    goAfterLogin()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '注册失败')
  } finally {
    submitting.value = false
  }
}

const onChangePassword = async () => {
  if (!cpPhone.value || !cpOldPassword.value || !cpNewPassword.value || !cpNewPassword2.value) {
    alert('请完整填写所有字段')
    return
  }
  if (cpNewPassword.value !== cpNewPassword2.value) {
    alert('两次输入的新密码不一致')
    return
  }
  submittingChange.value = true
  try {
    await axios.post('/api/auth/change-password', {
      phone: cpPhone.value.trim(),
      old_password: cpOldPassword.value,
      new_password: cpNewPassword.value,
      new_password_confirm: cpNewPassword2.value,
    })
    alert('密码修改成功，请使用新密码重新登录。')
    closeChangePwd()
    // 为安全起见，清除本地登录状态
    localStorage.removeItem('hbcloud_token')
    localStorage.removeItem('hbcloud_user')
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '修改密码失败')
  } finally {
    submittingChange.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
}

.login-card {
  width: 360px;
  background: #ffffff;
  border-radius: 8px;
  padding: 20px 24px 18px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.35);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}

/* 白色卡片整体切换过渡：轻微缩放与淡入，总时长不超过 0.3s */
.login-card-switch-enter-active,
.login-card-switch-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}

.login-card-switch-enter-from,
.login-card-switch-leave-to {
  opacity: 0;
  transform: scale(0.98);
}

.login-card-switch-enter-to,
.login-card-switch-leave-from {
  opacity: 1;
  transform: scale(1);
}

.title {
  font-size: 20px;
  margin: 0 0 4px;
}

.subtitle {
  margin: 0 0 10px;
  font-size: 13px;
  color: #6b7280;
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 10px;
}

.tab-btn {
  flex: 1 1 0;
  border-radius: 4px;
  border: 1px solid #d1d5db;
  background: #f3f4f6;
  padding: 4px 0;
  font-size: 13px;
  cursor: pointer;
}

.tab-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field {
  display: flex;
  flex-direction: column;
  font-size: 13px;
}

.label {
  margin-bottom: 2px;
}

input[type='text'],
input[type='password'] {
  border-radius: 4px;
  border: 1px solid #d1d5db;
  padding: 6px 8px;
  font-size: 13px;
}

.submit {
  margin-top: 6px;
  border-radius: 4px;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #ffffff;
  padding: 6px 0;
  font-size: 14px;
  cursor: pointer;
}

.submit:disabled {
  opacity: 0.6;
  cursor: default;
}

.tip-row {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.tip-text {
  text-align: left;
}

.tip-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.link-btn {
  border: none;
  background: transparent;
  padding: 0;
  margin: 0;
  color: #2563eb;
  cursor: pointer;
  font-size: 12px;
}

.hint-text {
  color: #6b7280;
}

.mask {
  position: fixed;
  inset: 0;
  background-color: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  width: 360px;
  max-width: 90vw;
  background-color: #ffffff;
  border-radius: 6px;
  padding: 12px 16px 14px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
}

.dialog-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.dialog-body {
  font-size: 13px;
}

.dialog-footer {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.equal-buttons {
  justify-content: center;
}

.equal-buttons .submit-btn,
.equal-buttons .cancel-btn {
  flex: 1 1 0;
  padding: 8px 0;
  line-height: 1.4;
  box-sizing: border-box;
}

.submit-btn {
  border-radius: 4px;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.cancel-btn {
  border-radius: 4px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
}

.cp-tip {
  margin-top: 10px;
  font-size: 12px;
  color: #6b7280;
}

/* 登录/注册表单切换过渡动画：总时长约0.3s，子元素自上而下依次显现 */
.login-switch-enter-active,
.login-switch-leave-active {
  transition: opacity 0.28s ease, transform 0.28s ease;
}

.login-switch-enter-from,
.login-switch-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.login-switch-enter-to,
.login-switch-leave-from {
  opacity: 1;
  transform: translateY(0);
}

/* 子元素依次显现：label 从上到下轻微延迟，按钮略晚一点 */
.login-switch-enter-active .field:nth-of-type(1),
.login-switch-enter-active .field:nth-of-type(2),
.login-switch-enter-active .field:nth-of-type(3),
.login-switch-enter-active .field:nth-of-type(4),
.login-switch-enter-active .field:nth-of-type(5) {
  opacity: 0;
  transform: translateY(4px);
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.login-switch-enter-active .submit {
  opacity: 0;
  transform: translateY(4px);
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.login-switch-enter-to .field:nth-of-type(1) {
  opacity: 1;
  transform: translateY(0);
  transition-delay: 0.02s;
}

.login-switch-enter-to .field:nth-of-type(2) {
  opacity: 1;
  transform: translateY(0);
  transition-delay: 0.06s;
}

.login-switch-enter-to .field:nth-of-type(3) {
  opacity: 1;
  transform: translateY(0);
  transition-delay: 0.1s;
}

.login-switch-enter-to .field:nth-of-type(4) {
  opacity: 1;
  transform: translateY(0);
  transition-delay: 0.14s;
}

.login-switch-enter-to .field:nth-of-type(5) {
  opacity: 1;
  transform: translateY(0);
  transition-delay: 0.18s;
}

.login-switch-enter-to .submit {
  opacity: 1;
  transform: translateY(0);
  transition-delay: 0.22s;
}

/* 修改密码弹窗淡入淡出过渡 */
.change-pwd-popup-enter-active,
.change-pwd-popup-leave-active {
  transition: opacity 0.15s ease;
}

.change-pwd-popup-enter-from,
.change-pwd-popup-leave-to {
  opacity: 0;
}

.change-pwd-popup-enter-to,
.change-pwd-popup-leave-from {
  opacity: 1;
}

.change-pwd-popup-enter-active .dialog,
.change-pwd-popup-leave-active .dialog {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.change-pwd-popup-enter-from .dialog,
.change-pwd-popup-leave-to .dialog {
  opacity: 0;
  transform: translateY(8px);
}

.change-pwd-popup-enter-to .dialog,
.change-pwd-popup-leave-from .dialog {
  opacity: 1;
  transform: translateY(0);
}
</style>
