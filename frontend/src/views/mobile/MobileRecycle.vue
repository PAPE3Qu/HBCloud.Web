<template>
  <div class="m-recycle">
    <div class="m-panel">
      <div class="m-row">
        <input
          v-model="keyword"
          class="m-input"
          type="text"
          placeholder="按名称或原路径搜索"
          @keyup.enter="loadList"
        />
        <button class="m-btn" type="button" @click="loadList">刷新</button>
      </div>
      <div class="m-row">
        <select v-model="spaceType" class="m-select" @change="loadList">
          <option value="">所有空间</option>
          <option value="public">公共空间</option>
          <option value="department">部门空间</option>
          <option value="safe">个人保险库</option>
        </select>
        <select v-model="scope" class="m-select" @change="loadList">
          <option value="all">全部类型</option>
          <option value="file">文件/文件夹</option>
          <option value="department">部门</option>
        </select>
      </div>
    </div>

    <div class="m-list">
      <div v-if="loading" class="m-empty">加载中…</div>
      <div v-else-if="!items.length" class="m-empty">暂无回收内容</div>

      <div
        v-for="it in items"
        :key="it.id"
        class="m-item"
        :class="{ selected: selectedIds.includes(it.id) }"
        @touchstart="onTouchStart(it)"
        @touchend="onTouchEnd"
        @touchmove="onTouchCancel"
      >
        <button class="m-item-main" type="button" @click="onTap(it)">
          <span v-if="selectionMode" class="chk" :class="{ on: selectedIds.includes(it.id) }">{{ selectedIds.includes(it.id) ? '✓' : '' }}</span>
          <span class="ico">{{ it.scope === 'department' ? '🏢' : (it.isDir ? '📁' : '📄') }}</span>
          <span class="name">
            <span class="n1">{{ it.scope === 'department' ? (it.departmentId || it.name) : it.name }}</span>
            <span class="n2">{{ formatSpace(it) }} · {{ it.originalPath || '/' }}</span>
            <span class="n2">删除：{{ formatTime(it.deletedAt) }} · {{ it.deletedBy || '-' }}</span>
          </span>
        </button>
        <button class="m-more" type="button" @click.stop="openInfo(it)">…</button>
      </div>
    </div>

    <transition name="m-fade">
      <div v-if="infoVisible" class="m-mask" @click="infoVisible = false">
        <div class="m-info" @click.stop>
          <div class="m-info-title">{{ infoItem?.scope === 'department' ? (infoItem?.departmentId || infoItem?.name) : infoItem?.name }}</div>
          <div class="m-info-row">原空间：{{ formatSpace(infoItem) }}</div>
          <div class="m-info-row">原路径：{{ infoItem?.originalPath || '/' }}</div>
          <div class="m-info-row">删除时间：{{ formatTime(infoItem?.deletedAt) }}</div>
          <div class="m-info-row">删除人：{{ infoItem?.deletedBy || '-' }}</div>
          <button class="m-info-close" type="button" @click="infoVisible = false">关闭</button>
        </div>
      </div>
    </transition>

    <transition name="m-fade">
      <div v-if="busy.active" class="m-mask" @click.stop>
        <div class="m-busy" @click.stop>
          <div class="t">{{ busy.text }}</div>
          <div class="bar"><div class="in" :style="{ width: busy.percent + '%' }"></div></div>
          <div class="p">{{ busy.percent }}%</div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import axios from 'axios'
import { resetMobileShell, setMobileMenu, setMobileShell } from '../../mobile/shellStore'
import { getUiMode, setUiMode } from '../../mobile/uiMode'
import { useRouter } from 'vue-router'

const router = useRouter()

const items = ref([])
const loading = ref(false)
const keyword = ref('')
const scope = ref('all')
const spaceType = ref('')
const page = ref(1)
const pageSize = ref(200)

const selectionMode = ref(false)
const selectedIds = ref([])

const infoVisible = ref(false)
const infoItem = ref(null)

const busy = ref({ active: false, text: '', percent: 0 })
let busyTimer = null

let longPressTimer = null

const formatTime = (ts) => {
  if (!ts) return '-'
  const d = new Date(ts * 1000)
  const pad = (n) => (n < 10 ? '0' + n : '' + n)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const departments = ref([])
const loadDepartments = async () => {
  try {
    const { data } = await axios.get('/api/files/departments')
    departments.value = data || []
  } catch {
    departments.value = []
  }
}

const findDeptName = (deptId) => {
  const id = (deptId || '').trim()
  if (!id) return ''
  const hit = departments.value.find((d) => d.id === id)
  return hit ? hit.name : id
}

const formatSpace = (it) => {
  if (!it) return '-'
  if (it.spaceType === 'public') return '公共空间'
  if (it.spaceType === 'safe') return '个人保险库'
  if (it.spaceType === 'department') {
    if (it.scope !== 'department') {
      const extra = it.extra || {}
      const extraName = (extra.deptName || extra.departmentName || extra.name || '').trim()
      const name = extraName || findDeptName(it.departmentId)
      return name ? `部门空间 / ${name}` : '部门空间'
    }
    const extra = it.extra || {}
    const extraName = (extra.deptName || extra.departmentName || extra.name || '').trim()
    const name = extraName || findDeptName(it.departmentId)
    return name ? `部门（${name}）` : '部门'
  }
  return it.spaceType || '-'
}

const loadList = async () => {
  loading.value = true
  selectedIds.value = []
  selectionMode.value = false
  try {
    const params = { page: page.value, pageSize: pageSize.value }
    if (scope.value && scope.value !== 'all') params.scope = scope.value
    if (spaceType.value) params.spaceType = spaceType.value
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    const { data } = await axios.get('/api/files/recycle/list', { params })
    items.value = data.items || []
  } catch (e) {
    items.value = []
    window.alert((e.response && e.response.data && e.response.data.detail) || '加载回收站失败')
  } finally {
    loading.value = false
  }
}

const startBusy = (text) => {
  busy.value = { active: true, text, percent: 5 }
  if (busyTimer) {
    clearInterval(busyTimer)
    busyTimer = null
  }
  busyTimer = setInterval(() => {
    if (!busy.value.active) return
    if (busy.value.percent >= 95) return
    busy.value = { ...busy.value, percent: busy.value.percent + 3 }
  }, 800)
}

const finishBusy = (text) => {
  busy.value = { ...busy.value, text, percent: 100 }
  if (busyTimer) {
    clearInterval(busyTimer)
    busyTimer = null
  }
  setTimeout(() => {
    busy.value = { active: false, text: '', percent: 0 }
  }, 350)
}

const restoreSelected = async () => {
  if (!selectedIds.value.length) return
  startBusy(`正在还原 ${selectedIds.value.length} 项，请稍候…`)
  try {
    const { data } = await axios.post('/api/files/recycle/restore', { ids: selectedIds.value })
    const failed = (data && data.failed) ? data.failed : []
    await loadList()
    if (failed.length) {
      finishBusy('还原完成（部分未处理）')
      setTimeout(() => window.alert('部分项目无权操作，请联系管理员。'), 120)
      return
    }
    finishBusy('还原完成')
  } catch (e) {
    finishBusy('还原失败')
    setTimeout(() => {
      if (e.response && e.response.status === 403) {
        window.alert('空间未开放或无访问权限，请联系管理员')
      } else {
        window.alert((e.response && e.response.data && e.response.data.detail) || '还原失败')
      }
    }, 120)
  }
}

const purgeSelected = async () => {
  if (!selectedIds.value.length) return
  const ok = window.confirm(`将彻底删除选中的 ${selectedIds.value.length} 项，操作不可恢复，是否确认？`)
  if (!ok) return
  startBusy(`正在彻底删除 ${selectedIds.value.length} 项，请稍候…`)
  try {
    const { data } = await axios.post('/api/files/recycle/purge', { ids: selectedIds.value })
    const failed = (data && data.failed) ? data.failed : []
    await loadList()
    if (failed.length) {
      finishBusy('彻底删除完成（部分未处理）')
      setTimeout(() => window.alert('部分项目无权操作，请联系管理员。'), 120)
      return
    }
    finishBusy('彻底删除完成')
  } catch (e) {
    finishBusy('彻底删除失败')
    setTimeout(() => window.alert((e.response && e.response.data && e.response.data.detail) || '彻底删除失败'), 120)
  }
}

const clearSelection = () => {
  selectedIds.value = []
  selectionMode.value = false
}

const toggleOne = (id) => {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]
  }
}

const onTap = (it) => {
  if (!it) return
  if (selectionMode.value) {
    toggleOne(it.id)
    return
  }
  // 单击默认不做定位/操作（移动端仅信息 + 顶部菜单）
}

const onTouchStart = (it) => {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
  longPressTimer = setTimeout(() => {
    if (!selectionMode.value) selectionMode.value = true
    toggleOne(it.id)
  }, 450)
}

const onTouchEnd = () => {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

const onTouchCancel = () => {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

const openInfo = (it) => {
  infoItem.value = it
  infoVisible.value = true
}

const updateTopBar = () => {
  setMobileShell({
    title: '回收站',
    subtitle: '',
    showBackPlaceholder: true,
    backEnabled: false,
    onBack: null,
    showSearch: false,
  })

  const uiMode = getUiMode()
  const switchLabel = uiMode === 'desktop' ? '切换到移动版' : '切换到桌面版'

  setMobileMenu([
    { key: 'refresh', label: '刷新', onClick: async () => loadList() },
    { key: 'sel-clear', label: '清除选择', hidden: !selectionMode.value, onClick: async () => clearSelection() },
    { key: 'restore', label: '还原选中', disabled: selectedIds.value.length === 0, onClick: async () => restoreSelected() },
    { key: 'purge', label: '彻底删除选中', disabled: selectedIds.value.length === 0, onClick: async () => purgeSelected() },
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
          router.replace('/m/recycle')
        } else {
          setUiMode('desktop')
          router.replace('/recycle')
        }
      },
    },
  ])
}

watch([selectionMode, selectedIds], () => nextTick(updateTopBar))

onMounted(async () => {
  resetMobileShell()
  await loadDepartments()
  await loadList()
  updateTopBar()
})

onUnmounted(() => {
  resetMobileShell()
  if (busyTimer) {
    clearInterval(busyTimer)
    busyTimer = null
  }
})
</script>

<style scoped>
.m-panel {
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  padding: 12px;
  margin-top: 8px;
}

.m-row {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.m-row:first-child {
  margin-top: 0;
}

.m-input {
  flex: 1;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 10px 12px;
  font-size: 14px;
}

.m-select {
  flex: 1;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 10px 12px;
  font-size: 14px;
  background: #fff;
}

.m-btn {
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  padding: 10px 12px;
}

.m-list {
  margin-top: 12px;
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.m-empty {
  color: #6b7280;
  padding: 18px 14px;
}

.m-item {
  display: flex;
  align-items: stretch;
  border-top: 1px solid #f3f4f6;
}

.m-item:first-child {
  border-top: none;
}

.m-item.selected {
  background: #eff6ff;
}

.m-item-main {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 12px;
  border: none;
  background: transparent;
  text-align: left;
}

.chk {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: 2px solid #93c5fd;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
}

.chk.on {
  background: #2563eb;
  border-color: #2563eb;
}

.ico {
  width: 22px;
  text-align: center;
}

.name {
  flex: 1;
  min-width: 0;
}

.n1 {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.n2 {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.m-more {
  width: 44px;
  border: none;
  background: transparent;
  font-size: 22px;
  color: #6b7280;
}

.m-mask {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.35);
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px;
}

.m-info {
  width: min(360px, 92vw);
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  padding: 14px;
}

.m-info-title {
  font-size: 16px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 10px;
}

.m-info-row {
  font-size: 13px;
  color: #374151;
  margin: 6px 0;
}

.m-info-close {
  width: 100%;
  margin-top: 10px;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
}

.m-busy {
  width: min(360px, 92vw);
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  padding: 14px;
}

.m-busy .t {
  font-weight: 700;
  color: #111827;
}

.m-busy .bar {
  margin-top: 10px;
  height: 10px;
  border-radius: 999px;
  background: #e5e7eb;
  overflow: hidden;
}

.m-busy .bar .in {
  height: 100%;
  background: #2563eb;
}

.m-busy .p {
  margin-top: 8px;
  color: #6b7280;
  font-size: 12px;
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
