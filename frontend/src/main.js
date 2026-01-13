import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import axios from 'axios'

// 首次加载时，如无 token 且直接访问根路径，则重定向到登录页
const rawToken = localStorage.getItem('hbcloud_token')
if (!rawToken && window.location.pathname === '/') {
  window.location.replace('/login')
}

// 全局 axios 配置：为所有 /api 请求自动附加 Bearer Token
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('hbcloud_token')
  if (token && config && config.url && config.url.startsWith('/api/')) {
    config.headers = config.headers || {}
    if (!config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// 全局 Axios 配置：401/invalid_token 时自动跳转登录页
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const detail = error.response.data && error.response.data.detail
      if (detail === 'not_authenticated' || detail === 'invalid_token') {
        // 增加中文提示：在自动跳转登录页前先友好提示一次
        window.alert('登录已过期或凭证无效，请重新登录后继续使用。')
        localStorage.removeItem('hbcloud_token')
        localStorage.removeItem('hbcloud_user')
        router.push({ name: 'Login' })
      }
    }
    return Promise.reject(error)
  }
)

const app = createApp(App)
app.use(router)
app.mount('#app')
