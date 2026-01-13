<template>
  <div class="app-root">
    <!-- 水印层：仅登录后显示，覆盖全屏但不影响交互 -->
    <div
      v-if="watermarkText"
      class="app-watermark"
      aria-hidden="true"
      :style="watermarkStyle"
    ></div>

    <header class="app-header">
      <div class="app-left">
        <h1>HBCloud 河北分院开放网盘</h1>
      </div>
      <div class="app-right">
        <span class="welcome-text">{{ welcomeText }}</span>
        <!-- 在帮助页时，按钮文案显示为“返回” -->
        <button class="help-btn" type="button" @click="goHelp">
          {{ route.path === '/help' ? '返回' : '帮助' }}
        </button>
        <button class="logout-btn" type="button" @click="onLogout">登出</button>
      </div>
    </header>
    <aside class="app-sidebar">
      <nav class="sidebar-nav">
        <router-link to="/" class="side-link">
          <span class="icon">🏠</span>
          <span class="label">首页</span>
        </router-link>
        <router-link to="/files" class="side-link">
          <span class="icon">📁</span>
          <span class="label">文件浏览</span>
        </router-link>
        <!-- 新增：回收站入口，与首页、文件浏览并列 -->
        <router-link to="/recycle" class="side-link">
          <span class="icon">🚮</span>
          <span class="label">回收站</span>
        </router-link>
        <button type="button" class="side-link side-button" @click="openFavorites">
          <span class="icon">🚩</span>
          <span class="label">快速访问</span>
        </button>
      </nav>
      <!-- 侧边栏底部占位按钮“空间权限”，暂不绑定功能 -->
      <div class="sidebar-footer">
        <!-- 人员管理：仅 super/op 显示 -->
        <button
          v-if="isOpOrSuper"
          type="button"
          class="user-manage-btn"
          @click="goUserManage"
        >
          <span class="icon">🏅</span>
          <span class="label">人员管理</span>
        </button>
        <button type="button" class="space-permission-btn" @click="goSpacePermission">
          <span class="icon">🔏</span>
          <span class="label">空间权限</span>
        </button>
      </div>
    </aside>
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

// 记录上一次非 /help 的页面路径，用于从帮助页返回
if (!window.__hbcloud_last_route__) {
  window.__hbcloud_last_route__ = '/'
}

const user = ref(null)

const loadUser = () => {
  const raw = localStorage.getItem('hbcloud_user')
  if (!raw) return
  try {
    user.value = JSON.parse(raw)
  } catch {
    user.value = null
  }
}

onMounted(() => {
  loadUser()
})

// 提供一个全局可访问的刷新方法，供子页面调用
if (window) {
  window.__hbcloud_refresh_user__ = loadUser
}

const welcomeText = computed(() => {
  const name = (user.value && (user.value.name || user.value.phone)) || ''
  if (name) return `${name}，欢迎使用`
  return '欢迎使用'
})

// 水印内容：姓名 + 手机号（有任一即可显示）
const watermarkText = computed(() => {
  const u = user.value || {}
  const name = (u.name || '').toString().trim()
  const phone = (u.phone || '').toString().trim()
  const text = [name, phone].filter(Boolean).join('  ')
  return text || ''
})

// 用 SVG 平铺水印：比 text-shadow 更稳定，缩放/分辨率变化也能覆盖全屏
const watermarkStyle = computed(() => {
  if (!watermarkText.value) return {}

  // 轻量 escape，避免引号/换行破坏 data-uri
  const text = watermarkText.value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')

  // 单元尺寸：每个水印间距（可调）
  const tileW = 240
  const tileH = 240

  // 45°（这里用 -45° 让文字从左下到右上倾斜）
  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${tileW}" height="${tileH}" viewBox="0 0 ${tileW} ${tileH}">
  <g transform="translate(${tileW / 2} ${tileH / 2}) rotate(-45)">
    <text x="0" y="0" text-anchor="middle" dominant-baseline="middle"
      font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',Arial,sans-serif"
      font-size="18" fill="#111827" fill-opacity="0.12" letter-spacing="2">${text}</text>
  </g>
</svg>`

  // URI 编码（encodeURIComponent 对 # 等字符更安全）
  const dataUri = `data:image/svg+xml,${encodeURIComponent(svg)}`

  return {
    backgroundImage: `url("${dataUri}")`,
    backgroundRepeat: 'repeat',
    backgroundSize: `${tileW}px ${tileH}px`
  }
})

const onLogout = () => {
  // 清理本地登录信息并跳转登录页
  localStorage.removeItem('hbcloud_token')
  localStorage.removeItem('hbcloud_user')
  window.location.href = '/login'
}

// 进入帮助前记住当前路径；在帮助页时点击则返回
const goHelp = () => {
  if (route.path === '/help') {
    const backTarget = window.__hbcloud_last_route__ || '/'
    router.push(backTarget)
  } else {
    window.__hbcloud_last_route__ = route.fullPath || route.path || '/'
    router.push('/help')
  }
}

const goSpacePermission = () => {
  router.push('/space-permission')
}

const isOpOrSuper = computed(() => {
  const role = (user.value && (user.value.role || '')) || ''
  const r = role.toLowerCase()
  return r === 'op' || r === 'super'
})

const goUserManage = () => {
  router.push('/users')
}

const openFavorites = async () => {
  // 仅在文件浏览页有效，其它页面只切到 /files
  if (route.path !== '/files') {
    // 使用路由 query 触发 FileBrowser 在挂载时打开快速访问面板
    await router.push({ path: '/files', query: { fav_panel: '1' } })
  } else {
    window.dispatchEvent(new CustomEvent('hbcloud-open-favorites'))
  }
}
</script>

<style scoped>
.app-root {
  /* 整个应用占满视口，并作为定位参考 */
  position: fixed;
  inset: 0;
  display: block;
  background-color: #f3f4f6;
}

.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem; /* 略微增高顶部栏 */
  background-color: #1f2937;
  color: #fff;
}

.app-left {
  display: flex;
  align-items: center;
}

.app-header h1 {
  font-size: 1.3rem;
  margin: 0;
  white-space: nowrap;
}

.app-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9rem;
}

.welcome-text {
  color: #d1d5db;
}

.help-btn {
  padding: 0.3rem 0.85rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: transparent;
  color: #e5e7eb;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.help-btn:hover {
  background-color: #374151;
}

.logout-btn {
  padding: 0.3rem 0.85rem;
  border-radius: 4px;
  border: 1px solid #ef4444;
  background-color: transparent;
  color: #fca5a5;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.logout-btn:hover {
  background-color: #b91c1c;
  border-color: #fee2e2;
  color: #fef2f2;
}

.app-sidebar {
  position: fixed;
  top: 3.2rem; /* 与 header 高度匹配，可根据实际微调 */
  bottom: 0;
  left: 0;
  width: 200px;
  background-color: #111827;
  color: #e5e7eb;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
}

/* 新增：侧边栏底部区域，放置“空间权限”按钮 */
.sidebar-footer {
  margin-top: auto; /* 将底部区域推到侧边栏最底部 */
  padding: 0.6rem 0.8rem;
  border-top: 1px solid #1f2937;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.space-permission-btn {
  width: 100%;
  display: flex;
  align-items: center;
  padding: 0.55rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #4b5563;
  background-color: #111827;
  color: #e5e7eb;
  cursor: default; /* 功能占位，暂不提供点击行为 */
  font-size: 0.9rem;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.space-permission-btn .icon {
  width: 1.5rem;
  margin-right: 0.5rem;
  text-align: center;
}

.space-permission-btn .label {
  text-align: left;
}

.space-permission-btn:hover {
  background-color: #1f2937;
  border-color: #6b7280;
}

.user-manage-btn {
  width: 100%;
  display: flex;
  align-items: center;
  padding: 0.55rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #4b5563;
  background-color: #111827;
  color: #e5e7eb;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.user-manage-btn .icon {
  width: 1.5rem;
  margin-right: 0.5rem;
  text-align: center;
}

.user-manage-btn .label {
  text-align: left;
}

.user-manage-btn:hover {
  background-color: #1f2937;
  border-color: #6b7280;
}

.side-link {
  display: flex;
  align-items: center;
  padding: 0.7rem 1.1rem;
  text-decoration: none;
  color: #e5e7eb;
  font-size: 0.95rem;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.side-link .icon {
  width: 1.5rem;
  margin-right: 0.5rem;
  text-align: center;
}

.side-link .label {
  text-align: left;
}

.side-link:hover {
  background-color: #1f2937;
}

.router-link-active.side-link {
  background-color: #2563eb;
  color: #f9fafb;
}

.side-button {
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
}

.app-main {
  position: fixed;
  top: 3.2rem; /* 与 header 高度一致 */
  bottom: 0;
  left: 200px; /* 侧边栏宽度 */
  right: 0;
  padding: 1rem;
  background-color: #f3f4f6;
  overflow: auto; /* 仅内容区滚动 */
}

/* 路由页面切换 0.25s 统一过渡 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease;
}
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

/* 全屏倾斜水印层：不影响阅读与使用，不可选中和点击 */
.app-watermark {
  position: fixed;
  inset: 0;
  z-index: 9; /* header(10) 之下，确保顶部栏按钮可用 */
  pointer-events: none;
  user-select: none;

  /* 背景平铺由 watermarkStyle 提供 */
}
</style>
