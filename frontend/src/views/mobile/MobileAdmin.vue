<template>
  <div class="m-admin">
    <!-- 直接复用桌面端空间权限页（在组件内部做移动端样式适配） -->
    <SpacePermission />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import SpacePermission from '../SpacePermission.vue'
import { resetMobileShell, setMobileMenu, setMobileShell } from '../../mobile/shellStore'
import { getUiMode, setUiMode } from '../../mobile/uiMode'

const router = useRouter()

onMounted(() => {
  resetMobileShell()
  setMobileShell({
    title: '管理',
    subtitle: '',
    showBackPlaceholder: true,
    backEnabled: false,
    onBack: null,
    showSearch: false,
  })

  const uiMode = getUiMode()
  const switchLabel = uiMode === 'desktop' ? '切换到移动版' : '切换到桌面版'

  setMobileMenu([
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
          router.replace('/m/admin')
        } else {
          setUiMode('desktop')
          router.replace('/space-permission')
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
.m-admin {
  padding: 6px 0 0;
}
</style>
