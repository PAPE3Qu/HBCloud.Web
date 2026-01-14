<template>
  <div class="m-home">
    <Home />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Home from '../Home.vue'
import { resetMobileShell, setMobileMenu, setMobileShell } from '../../mobile/shellStore'
import { getUiMode, setUiMode } from '../../mobile/uiMode'

const router = useRouter()

onMounted(() => {
  resetMobileShell()
  setMobileShell({
    title: '首页',
    subtitle: '',
    showBackPlaceholder: true,
    backEnabled: false,
    onBack: null,
    showSearch: false,
  })

  const userRaw = localStorage.getItem('hbcloud_user')
  let name = ''
  if (userRaw) {
    try {
      const u = JSON.parse(userRaw)
      name = (u.name || u.phone || '').toString()
    } catch {
      name = ''
    }
  }

  const uiMode = getUiMode()
  const switchLabel = uiMode === 'desktop' ? '切换到移动版' : '切换到桌面版'

  setMobileMenu([
    { key: 'welcome', label: `${name || '欢迎'} 使用`, disabled: true },
    { key: 'help', label: '帮助', onClick: async () => router.push('/help') },
    {
      key: 'logout',
      label: '登出',
      onClick: async () => {
        localStorage.removeItem('hbcloud_token')
        localStorage.removeItem('hbcloud_user')
        router.push('/login')
      },
    },
    {
      key: 'switch-ui',
      label: switchLabel,
      onClick: async () => {
        if (uiMode === 'desktop') {
          setUiMode('mobile')
          router.replace('/m/home')
        } else {
          setUiMode('desktop')
          router.replace('/')
        }
      },
    },
  ])
})

onUnmounted(() => {
  resetMobileShell()
})
</script>

<style scoped>
.m-home {
  padding: 6px 0 0;
}
</style>
