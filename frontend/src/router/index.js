import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../views/Home.vue'
import FileBrowser from '../views/FileBrowser.vue'
import Login from '../views/Login.vue'
import RecycleBin from '../views/RecycleBin.vue'
import Help from '../views/Help.vue'
import SpacePermission from '../views/SpacePermission.vue'
import UserManage from '../views/UserManage.vue'

const routes = [
  { path: '/login', name: 'Login', component: Login },
  { path: '/', name: 'Home', component: Home, meta: { requiresAuth: true } },
  { path: '/files', name: 'Files', component: FileBrowser, meta: { requiresAuth: true } },
  { path: '/recycle', name: 'RecycleBin', component: RecycleBin, meta: { requiresAuth: true } },
  { path: '/help', name: 'Help', component: Help },
  { path: '/space-permission', name: 'SpacePermission', component: SpacePermission, meta: { requiresAuth: true } },
  { path: '/users', name: 'UserManage', component: UserManage, meta: { requiresAuth: true, requiresOpOrSuper: true } },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('hbcloud_token')
  const userRaw = localStorage.getItem('hbcloud_user')
  let role = ''
  if (userRaw) {
    try {
      const u = JSON.parse(userRaw)
      role = (u.role || '').toLowerCase()
    } catch {
      role = ''
    }
  }

  if (to.meta.requiresAuth && !token) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  if (to.meta.requiresOpOrSuper && role !== 'op' && role !== 'super') {
    // 非 op/super 访问人员管理，直接回首页
    return next({ path: '/' })
  }

  next()
})

export default router
