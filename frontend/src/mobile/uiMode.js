const KEY = 'hbcloud_ui_mode'

// 'auto' | 'mobile' | 'desktop'
export function getUiMode() {
  const v = (localStorage.getItem(KEY) || 'auto').toLowerCase()
  if (v === 'mobile' || v === 'desktop' || v === 'auto') return v
  return 'auto'
}

export function setUiMode(mode) {
  const m = (mode || 'auto').toLowerCase()
  if (m !== 'mobile' && m !== 'desktop' && m !== 'auto') return
  localStorage.setItem(KEY, m)
}

export function isSmallScreen() {
  try {
    return window.matchMedia && window.matchMedia('(max-width: 820px)').matches
  } catch {
    return false
  }
}

export function mapDesktopToMobile(path) {
  if (path === '/' || path === '') return '/m/home'
  if (path.startsWith('/files')) return '/m/browse'
  if (path.startsWith('/recycle')) return '/m/recycle'
  if (path.startsWith('/space-permission')) return '/m/admin'
  // 其它页面保持在移动壳里可继续导航（回落到浏览）
  return '/m/browse'
}

export function mapMobileToDesktop(path) {
  if (path.startsWith('/m/home')) return '/'
  if (path.startsWith('/m/browse')) return '/files'
  if (path.startsWith('/m/recycle')) return '/recycle'
  if (path.startsWith('/m/admin')) return '/space-permission'
  return '/'
}
