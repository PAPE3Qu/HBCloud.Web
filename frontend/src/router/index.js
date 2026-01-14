import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../views/Home.vue'
import FileBrowser from '../views/FileBrowser.vue'
import Login from '../views/Login.vue'
import RecycleBin from '../views/RecycleBin.vue'
import Help from '../views/Help.vue'
import SpacePermission from '../views/SpacePermission.vue'
import UserManage from '../views/UserManage.vue'

import MobileShell from '../views/mobile/MobileShell.vue'
import MobileHome from '../views/mobile/MobileHome.vue'
import MobileBrowse from '../views/mobile/MobileBrowse.vue'
import MobileRecycle from '../views/mobile/MobileRecycle.vue'
import MobileAdmin from '../views/mobile/MobileAdmin.vue'

import { getUiMode, isSmallScreen, mapDesktopToMobile, mapMobileToDesktop } from '../mobile/uiMode'

const routes = [
  { path: '/login', name: 'Login', component: Login },
  { path: '/', name: 'Home', component: Home, meta: { requiresAuth: true } },
  { path: '/files', name: 'Files', component: FileBrowser, meta: { requiresAuth: true } },
  { path: '/recycle', name: 'RecycleBin', component: RecycleBin, meta: { requiresAuth: true } },
  { path: '/help', name: 'Help', component: Help },
  { path: '/space-permission', name: 'SpacePermission', component: SpacePermission, meta: { requiresAuth: true } },
  { path: '/users', name: 'UserManage', component: UserManage, meta: { requiresAuth: true, requiresOpOrSuper: true } },

  // 移动端独立界面：/m/*
  {
    path: '/m',
    component: MobileShell,
    meta: { requiresAuth: true, isMobileShell: true },
    redirect: '/m/browse',
    children: [
      { path: 'home', name: 'MobileHome', component: MobileHome, meta: { requiresAuth: true, isMobileShell: true } },
      { path: 'browse', name: 'MobileBrowse', component: MobileBrowse, meta: { requiresAuth: true, isMobileShell: true } },
      { path: 'recycle', name: 'MobileRecycle', component: MobileRecycle, meta: { requiresAuth: true, isMobileShell: true } },
      { path: 'admin', name: 'MobileAdmin', component: MobileAdmin, meta: { requiresAuth: true, isMobileShell: true } },
    ],
  },
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

  // UI 模式：auto / mobile / desktop
  const uiMode = getUiMode()
  const goingMobile = to.path.startsWith('/m')
  const small = isSmallScreen()

  // desktop 强制：拒绝进入 /m
  if (uiMode === 'desktop' && goingMobile) {
    return next({ path: mapMobileToDesktop(to.path) })
  }

  // mobile 强制：把桌面路由映射到 /m
  if (uiMode === 'mobile' && !goingMobile && to.path !== '/login') {
    return next({ path: mapDesktopToMobile(to.path) })
  }

  // auto：小屏自动进入移动端（登录页/帮助页不强制）
  if (uiMode === 'auto' && small && !goingMobile && to.path !== '/login' && to.path !== '/help') {
    return next({ path: mapDesktopToMobile(to.path) })
  }

  if (to.meta.requiresOpOrSuper && role !== 'op' && role !== 'super') {
    // 非 op/super 访问人员管理，直接回首页
    return next({ path: '/' })
  }

  next()
})

export default router
