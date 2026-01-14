<template>
  <div class="m-shell">
    <div class="m-top">
      <div class="m-top-row">
        <button
          class="m-back"
          type="button"
          :class="{ hidden: state.showBackPlaceholder && !state.backEnabled }"
          :disabled="!state.backEnabled"
          @click="onBack"
          aria-label="返回"
        >
          ←
        </button>
        <div class="m-title">
          <div class="m-title-main">{{ state.title || '浏览' }}</div>
          <div v-if="state.subtitle" class="m-title-sub">{{ state.subtitle }}</div>
        </div>
        <button class="m-menu" type="button" @click="menuOpen = true" aria-label="菜单">…</button>
      </div>

      <div v-if="state.showSearch" class="m-search">
        <div class="m-search-inner">
          <span class="m-search-icon">🔍</span>
          <input
            v-model="state.searchQuery"
            class="m-search-input"
            type="text"
            :placeholder="state.searchPlaceholder || '搜索'"
            @keyup.enter="runSearch"
          />
          <button
            v-if="state.searchQuery"
            class="m-search-clear"
            type="button"
            @click="clearSearch"
          >
            ✕
          </button>
        </div>
      </div>
    </div>

    <div class="m-body">
      <router-view />
    </div>

    <nav class="m-tabs" aria-label="底部导航">
      <router-link to="/m/home" class="m-tab" active-class="active">
        <div class="ico">🏠</div>
        <div class="txt">首页</div>
      </router-link>
      <router-link to="/m/browse" class="m-tab" active-class="active">
        <div class="ico">📁</div>
        <div class="txt">文件浏览</div>
      </router-link>
      <router-link to="/m/recycle" class="m-tab" active-class="active">
        <div class="ico">🚮</div>
        <div class="txt">回收站</div>
      </router-link>
      <router-link to="/m/admin" class="m-tab" active-class="active">
        <div class="ico">🔏</div>
        <div class="txt">管理</div>
      </router-link>
    </nav>

    <transition name="m-fade">
      <div v-if="menuOpen" class="m-menu-mask" @click="menuOpen = false">
        <div class="m-menu-panel" @click.stop>
          <button class="m-menu-close" type="button" @click="menuOpen = false">关闭</button>
          <div class="m-menu-list">
            <button
              v-for="it in visibleMenuItems"
              :key="it.key"
              class="m-menu-item"
              type="button"
              :disabled="!!it.disabled"
              @click="onMenuItem(it)"
            >
              {{ it.label }}
            </button>
            <div v-if="!visibleMenuItems.length" class="m-menu-empty">暂无可用操作</div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { mobileShellState as state } from '../../mobile/shellStore'

const router = useRouter()
const route = useRoute()
const menuOpen = ref(false)

const visibleMenuItems = computed(() => {
  return (state.menuItems || []).filter((x) => x && !x.hidden)
})

const onBack = async () => {
  if (!state.backEnabled) return
  if (typeof state.onBack === 'function') {
    try {
      await state.onBack()
      return
    } catch {
      // ignore
    }
  }
  // 兜底：路由回退
  router.back()
}

const runSearch = async () => {
  if (typeof state.onSearch !== 'function') return
  await state.onSearch(state.searchQuery || '')
}

const clearSearch = async () => {
  state.searchQuery = ''
  if (typeof state.onClearSearch === 'function') {
    await state.onClearSearch()
    return
  }
  if (typeof state.onSearch === 'function') {
    await state.onSearch('')
  }
}

const onMenuItem = async (it) => {
  if (!it || it.disabled) return
  menuOpen.value = false
  if (typeof it.onClick === 'function') {
    await it.onClick({ router, route })
  }
}
</script>

<style scoped>
.m-shell {
  position: fixed;
  inset: 0;
  background: #f3f4f6;
  display: flex;
  flex-direction: column;
}

.m-top {
  position: sticky;
  top: 0;
  z-index: 50;
  background: #f3f4f6;
  padding: 10px 12px 6px;
}

.m-top-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.m-back {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #fff;
  font-size: 18px;
}

.m-back.hidden {
  opacity: 0;
  pointer-events: none;
}

.m-title {
  flex: 1;
  min-width: 0;
}

.m-title-main {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: #111827;
  line-height: 1.1;
}

.m-title-sub {
  margin-top: 2px;
  color: #6b7280;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.m-menu {
  width: 42px;
  height: 42px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #fff;
  font-size: 24px;
  line-height: 1;
}

.m-search {
  margin-top: 10px;
}

.m-search-inner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #e5e7eb;
  border-radius: 999px;
}

.m-search-icon {
  width: 18px;
  text-align: center;
}

.m-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 16px;
}

.m-search-clear {
  border: none;
  background: transparent;
  font-size: 16px;
  padding: 4px 6px;
}

.m-body {
  flex: 1;
  overflow: auto;
  padding: 0 12px 86px;
}

.m-tabs {
  position: fixed;
  left: 10px;
  right: 10px;
  bottom: 12px;
  height: 66px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #e5e7eb;
  backdrop-filter: blur(10px);
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  z-index: 60;
}

.m-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  text-decoration: none;
  color: #374151;
  border-radius: 18px;
}

.m-tab .ico {
  font-size: 18px;
  line-height: 1;
}

.m-tab .txt {
  font-size: 12px;
}

.m-tab.active {
  color: #2563eb;
}

.m-menu-mask {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.35);
  z-index: 80;
  display: flex;
  justify-content: flex-end;
}

.m-menu-panel {
  width: min(320px, 92vw);
  margin: 12px;
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.m-menu-close {
  width: 100%;
  border: none;
  background: #f9fafb;
  padding: 12px;
  font-size: 14px;
}

.m-menu-list {
  display: flex;
  flex-direction: column;
}

.m-menu-item {
  text-align: left;
  width: 100%;
  padding: 14px 14px;
  border: none;
  background: #fff;
  border-top: 1px solid #f3f4f6;
  font-size: 15px;
}

.m-menu-item:disabled {
  color: #9ca3af;
}

.m-menu-empty {
  padding: 14px;
  color: #6b7280;
}

.m-fade-enter-active,
.m-fade-leave-active {
  transition: opacity 0.18s ease;
}
.m-fade-enter-from,
.m-fade-leave-to {
  opacity: 0;
}
</style>
