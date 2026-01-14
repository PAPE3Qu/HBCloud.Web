import { reactive } from 'vue'

// 仅用于 /m/* 移动端壳（顶部栏/菜单/搜索栏）与子页面的协作
export const mobileShellState = reactive({
  // 顶部第一行（返回占位 / 标题 / 菜单）
  title: '浏览',
  subtitle: '',
  showBackPlaceholder: true,
  backEnabled: false,
  onBack: null,

  // 顶部第二行（搜索）
  showSearch: false,
  searchPlaceholder: '搜索',
  searchQuery: '',
  onSearch: null,
  onClearSearch: null,

  // 右上角菜单
  menuItems: [],
})

export function setMobileShell(patch) {
  if (!patch) return
  Object.assign(mobileShellState, patch)
}

export function setMobileMenu(items) {
  mobileShellState.menuItems = Array.isArray(items) ? items : []
}

export function resetMobileShell() {
  setMobileShell({
    title: '浏览',
    subtitle: '',
    showBackPlaceholder: true,
    backEnabled: false,
    onBack: null,
    showSearch: false,
    searchPlaceholder: '搜索',
    searchQuery: '',
    onSearch: null,
    onClearSearch: null,
    menuItems: [],
  })
}
