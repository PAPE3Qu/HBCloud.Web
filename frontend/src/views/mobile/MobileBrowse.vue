<template>
  <div class="m-browse">
    <!-- 第一层：空间 + 快速访问（默认展开） -->
    <div v-if="level === 1" class="m-layer">
      <div class="m-section">
        <button class="m-section-head" type="button" @click="spacesExpanded = !spacesExpanded">
          <span class="m-section-title">空间</span>
          <span class="m-caret">{{ spacesExpanded ? '▾' : '▸' }}</span>
        </button>
        <div v-if="spacesExpanded" class="m-card">
          <button class="m-row" type="button" @click="enterSpace('public')">
            <span class="ico">☁️</span>
            <span class="name">公共空间</span>
            <span class="right">›</span>
          </button>

          <button class="m-row" type="button" @click="toggleDeptExpand">
            <span class="ico">🏢</span>
            <span class="name">部门空间</span>
            <span class="right">{{ deptExpanded ? '▾' : '›' }}</span>
          </button>
          <div v-if="deptExpanded" class="m-sub">
            <div v-if="deptLoading" class="m-sub-empty">加载中…</div>
            <button
              v-for="d in departments"
              :key="d.id"
              class="m-row sub"
              type="button"
              @click="enterDepartment(d)"
            >
              <span class="ico">📁</span>
              <span class="name">{{ d.name || d.id }}</span>
              <span class="right">›</span>
            </button>
            <div v-if="!deptLoading && !departments.length" class="m-sub-empty">暂无部门</div>
          </div>

          <button class="m-row" type="button" @click="enterSpace('safe')">
            <span class="ico">🔒</span>
            <span class="name">个人保险库</span>
            <span class="right">›</span>
          </button>
        </div>
      </div>

      <div class="m-section">
        <button class="m-section-head" type="button" @click="favExpanded = !favExpanded">
          <span class="m-section-title">快速访问</span>
          <span class="m-caret">{{ favExpanded ? '▾' : '▸' }}</span>
        </button>
        <div v-if="favExpanded" class="m-card">
          <div v-if="favLoading" class="m-sub-empty">加载中…</div>
          <button
            v-for="(fav, idx) in favorites"
            :key="idx"
            class="m-row"
            type="button"
            @click="enterFavorite(fav)"
          >
            <span class="ico">🚩</span>
            <span class="name">
              <span class="fav-title">{{ fav.displayName || lastSegment(fav.path) || '（未命名）' }}</span>
              <span class="fav-sub">{{ describeFav(fav) }}</span>
            </span>
            <span class="right">›</span>
          </button>
          <div v-if="!favLoading && !favorites.length" class="m-sub-empty">暂无快速访问</div>
        </div>
      </div>
    </div>

    <!-- 第二层：文件列表 -->
    <div v-else class="m-layer">
      <input ref="uploadInput" type="file" multiple class="m-hidden-input" @change="onFilesChosen" />
      <div v-if="loading" class="m-loading">加载中…</div>

      <div v-if="!loading && displayedItems.length === 0" class="m-empty">
        {{ inSearchMode ? '未找到匹配结果' : '此目录下暂无文件或文件夹' }}
      </div>

      <div class="m-list">
        <div
          v-for="it in displayedItems"
          :key="itemKey(it)"
          class="m-item"
          :class="{ selected: isSelected(it) }"
          @touchstart="onTouchStart(it)"
          @touchend="onTouchEnd"
          @touchmove="onTouchCancel"
        >
          <button class="m-item-main" type="button" @click="onItemTap(it)">
            <span v-if="selectionMode" class="sel">
              <span class="chk" :class="{ on: isSelected(it) }">{{ isSelected(it) ? '✓' : '' }}</span>
            </span>
            <span class="ico">{{ fileIcon(it) }}</span>
            <span class="name">
              <span class="n1">{{ it.name }}</span>
              <span class="n2">{{ it.is_dir ? '文件夹' : formatSize(it.size) }}{{ it.modified_time ? ' · ' + formatTime(it.modified_time) : '' }}</span>
            </span>
            <span v-if="it.is_dir" class="right">›</span>
          </button>

          <button class="m-more" type="button" @click.stop="openInfo(it)">…</button>
        </div>
      </div>

      <transition name="m-fade">
        <div v-if="infoVisible" class="m-mask" @click="infoVisible = false">
          <div class="m-info" @click.stop>
            <div class="m-info-title">{{ infoItem?.name }}</div>
            <div class="m-info-row">类型：{{ infoItem?.is_dir ? '文件夹' : '文件' }}</div>
            <div class="m-info-row" v-if="!infoItem?.is_dir">大小：{{ formatSize(infoItem?.size) }}</div>
            <div class="m-info-row">修改：{{ formatTime(infoItem?.modified_time) }}</div>
            <button class="m-info-close" type="button" @click="infoVisible = false">关闭</button>
          </div>
        </div>
      </transition>

      <transition name="m-fade">
        <div v-if="showImagePreview" class="m-mask" @click="closeImagePreview">
          <div class="m-preview" @click.stop>
            <img v-if="previewImage" :src="previewImage" alt="预览" />
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
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import SparkMD5 from 'spark-md5'
import { resetMobileShell, setMobileMenu, setMobileShell } from '../../mobile/shellStore'
import { getUiMode, setUiMode } from '../../mobile/uiMode'

const router = useRouter()

const level = ref(1)
const spacesExpanded = ref(true)
const favExpanded = ref(true)

const deptExpanded = ref(false)
const deptLoading = ref(false)
const departments = ref([])

const favLoading = ref(false)
const favorites = ref([])

const ctx = ref({
  spaceType: 'public',
  departmentId: '',
  path: '.',
})

const items = ref([])
const loading = ref(false)

const inSearchMode = ref(false)
const searchResults = ref([])

const selectionMode = ref(false)
const selected = ref([])

const infoVisible = ref(false)
const infoItem = ref(null)

const previewImage = ref(null)
const showImagePreview = ref(false)

const busy = ref({ active: false, text: '', percent: 0 })

let longPressTimer = null
let longPressTriggered = false

const lastSegment = (p) => {
  if (!p || p === '.' || p === '/') return ''
  const parts = String(p).split('/').filter(Boolean)
  return parts[parts.length - 1] || ''
}

const describeFav = (fav) => {
  if (!fav) return ''
  if (fav.spaceType === 'public') return '公共空间'
  if (fav.spaceType === 'safe') return '个人保险库'
  if (fav.spaceType === 'department') {
    return fav.departmentId ? `部门空间 / ${fav.departmentId}` : '部门空间'
  }
  return fav.spaceType || ''
}

const enterSpace = async (spaceType) => {
  ctx.value = { spaceType, departmentId: '', path: '.' }
  level.value = 2
  await loadList()
}

const enterDepartment = async (d) => {
  ctx.value = { spaceType: 'department', departmentId: d.id, path: '.' }
  level.value = 2
  await loadList()
}

const enterFavorite = async (fav) => {
  ctx.value = {
    spaceType: fav.spaceType,
    departmentId: fav.departmentId || '',
    path: fav.path || '.',
  }
  level.value = 2
  await loadList()
}

const toggleDeptExpand = async () => {
  deptExpanded.value = !deptExpanded.value
  if (!deptExpanded.value) return
  if (departments.value.length) return
  await loadDepartments()
}

const loadDepartments = async () => {
  deptLoading.value = true
  try {
    const { data } = await axios.get('/api/files/departments')
    departments.value = data || []
  } catch {
    departments.value = []
  } finally {
    deptLoading.value = false
  }
}

const loadFavorites = async () => {
  favLoading.value = true
  try {
    const { data } = await axios.get('/api/files/favorites')
    favorites.value = data || []
  } catch {
    favorites.value = []
  } finally {
    favLoading.value = false
  }
}

const displayedItems = computed(() => (inSearchMode.value ? searchResults.value : items.value))

const fileIcon = (item) => {
  if (item.is_dir) return '📁'
  const lower = (item.name || '').toLowerCase()
  if (lower.endsWith('.zip')) return '📦'
  if (lower.endsWith('.pdf')) return '📄'
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp') || lower.endsWith('.bmp')) return '🖼️'
  return '📃'
}

const itemKey = (item) => `${item.name}-${item.is_dir ? 'd' : 'f'}-${item._path || ''}`

const isSelected = (item) => selected.value.some((s) => s.name === item.name && s.is_dir === item.is_dir && (s._path || '') === (item._path || ''))

const toggleSelect = (item) => {
  if (isSelected(item)) {
    selected.value = selected.value.filter((s) => !(s.name === item.name && s.is_dir === item.is_dir && (s._path || '') === (item._path || '')))
  } else {
    selected.value = [...selected.value, { ...item }]
  }
}

const formatSize = (n) => {
  const v = Number(n || 0)
  if (!v) return '0B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let x = v
  while (x >= 1024 && i < units.length - 1) {
    x /= 1024
    i++
  }
  const s = x >= 10 || i === 0 ? x.toFixed(0) : x.toFixed(1)
  return `${s}${units[i]}`
}

const formatTime = (ts) => {
  if (!ts) return '-'
  const d = new Date(ts * 1000)
  const pad = (n) => (n < 10 ? '0' + n : '' + n)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const buildDownloadUrl = (name, pathForItem, inline) => {
  const params = new URLSearchParams()
  params.append('spaceType', ctx.value.spaceType)
  if (ctx.value.spaceType === 'department') params.append('departmentId', ctx.value.departmentId)
  params.append('path', pathForItem)
  params.append('name', name)
  if (inline) params.append('disposition', 'inline')
  return `/api/files/download?${params.toString()}`
}

const copyToClipboard = async (text) => {
  const t = String(text || '')
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(t)
      return true
    }
  } catch {
    // fallback
  }
  try {
    const textarea = document.createElement('textarea')
    textarea.value = t
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    return true
  } catch {
    return false
  }
}

const openPreview = (item) => {
  const lower = (item.name || '').toLowerCase()
  const pathForItem = inSearchMode.value && item._path != null ? (item._path || '.') : (ctx.value.path || '.')
  const url = buildDownloadUrl(item.name, pathForItem, true)
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp')) {
    previewImage.value = url
    showImagePreview.value = true
    return
  }
  if (lower.endsWith('.pdf') || lower.endsWith('.md')) {
    window.open(url, '_blank')
    return
  }
}

const closeImagePreview = () => {
  showImagePreview.value = false
  previewImage.value = null
}

const openInfo = (item) => {
  infoItem.value = item
  infoVisible.value = true
}

const loadList = async () => {
  if (ctx.value.spaceType === 'department' && !ctx.value.departmentId) {
    items.value = []
    return
  }
  loading.value = true
  try {
    const params = { spaceType: ctx.value.spaceType, path: ctx.value.path || '.' }
    if (ctx.value.spaceType === 'department') params.departmentId = ctx.value.departmentId
    const { data } = await axios.get('/api/files/list', { params })
    items.value = data.items || []
  } catch (e) {
    items.value = []
    if (e.response && e.response.status === 403) {
      window.alert('空间未开放或无访问权限，请联系管理员')
    }
  } finally {
    loading.value = false
  }
}

const runSearch = async (keyword) => {
  const k = String(keyword || '').trim()
  if (!k) {
    inSearchMode.value = false
    searchResults.value = []
    selected.value = []
    await loadList()
    return
  }
  loading.value = true
  try {
    const params = { spaceType: ctx.value.spaceType, path: ctx.value.path || '.', keyword: k }
    if (ctx.value.spaceType === 'department') params.departmentId = ctx.value.departmentId
    const { data } = await axios.get('/api/files/search', { params })
    // 后端返回中使用 path 字段，这里兼容 FileBrowser 的 _path 约定
    searchResults.value = (data || []).map((r) => ({
      name: r.name,
      is_dir: r.is_dir,
      size: r.size,
      modified_time: r.modified_time,
      _path: r.path,
    }))
    inSearchMode.value = true
    selected.value = []
  } finally {
    loading.value = false
  }
}

const clearSearch = async () => {
  inSearchMode.value = false
  searchResults.value = []
  selected.value = []
  await loadList()
}

const goUpOrExit = async () => {
  if (inSearchMode.value) {
    await clearSearch()
    return
  }
  const p = (ctx.value.path || '.').toString()
  if (p === '.' || p === '' || p === '/') {
    // 回到第一层
    level.value = 1
    selected.value = []
    selectionMode.value = false
    return
  }
  const parts = p.split('/').filter(Boolean)
  parts.pop()
  ctx.value = { ...ctx.value, path: parts.length ? parts.join('/') : '.' }
  selected.value = []
  selectionMode.value = false
  await loadList()
}

const onItemTap = async (item) => {
  if (selectionMode.value) {
    toggleSelect(item)
    return
  }
  if (item.is_dir) {
    // 进入文件夹
    const base = ctx.value.path && ctx.value.path !== '.' ? ctx.value.path : ''
    ctx.value = { ...ctx.value, path: base ? `${base}/${item.name}` : item.name }
    await loadList()
    return
  }
  openPreview(item)
}

const onTouchStart = (item) => {
  longPressTriggered = false
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
  longPressTimer = setTimeout(() => {
    longPressTriggered = true
    if (!selectionMode.value) {
      selectionMode.value = true
      selected.value = []
    }
    toggleSelect(item)
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

const computeFileMd5 = (file) => {
  return new Promise((resolve, reject) => {
    const chunkSize = 2 * 1024 * 1024
    const chunks = Math.ceil(file.size / chunkSize)
    let current = 0
    const spark = new SparkMD5.ArrayBuffer()
    const reader = new FileReader()

    reader.onload = (e) => {
      spark.append(e.target.result)
      current += 1
      if (current < chunks) {
        loadNext()
      } else {
        resolve(spark.end())
      }
    }
    reader.onerror = () => reject(new Error('md5_failed'))

    const loadNext = () => {
      const start = current * chunkSize
      const end = Math.min(start + chunkSize, file.size)
      const slice = file.slice(start, end)
      reader.readAsArrayBuffer(slice)
    }

    if (file.size === 0) {
      resolve(SparkMD5.hash(''))
    } else {
      loadNext()
    }
  })
}

const uploadInput = ref(null)

const openUpload = () => {
  if (!uploadInput.value) return
  uploadInput.value.value = ''
  uploadInput.value.click()
}

const onFilesChosen = async (e) => {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  busy.value = { active: true, text: '正在计算文件校验码…', percent: 5 }
  try {
    const md5List = []
    for (let i = 0; i < files.length; i++) {
      const md5 = await computeFileMd5(files[i])
      md5List.push(md5)
      busy.value = { ...busy.value, percent: Math.min(30, Math.round(((i + 1) / files.length) * 30)) }
    }
    const form = new FormData()
    form.append('spaceType', ctx.value.spaceType)
    if (ctx.value.spaceType === 'department') form.append('departmentId', ctx.value.departmentId)
    form.append('path', ctx.value.path || '.')
    files.forEach((f, idx) => {
      form.append('files', f)
      form.append('md5', md5List[idx])
    })
    busy.value = { active: true, text: '正在上传…', percent: 40 }
    await axios.post('/api/files/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    busy.value = { active: true, text: '上传完成，正在刷新…', percent: 95 }
    await loadList()
    window.alert('上传成功')
  } catch (e2) {
    window.alert((e2.response && e2.response.data && e2.response.data.detail) || '上传失败')
  } finally {
    busy.value = { active: false, text: '', percent: 0 }
    if (uploadInput.value) uploadInput.value.value = ''
  }
}

const deleteSelected = async () => {
  if (!selected.value.length) return
  const ok = window.confirm(`将把选中的 ${selected.value.length} 个项目移入回收站，是否继续？`)
  if (!ok) return
  try {
    const pathForList = ctx.value.path || '.'
    const itemsPayload = selected.value.map((it) => ({
      spaceType: ctx.value.spaceType,
      departmentId: ctx.value.spaceType === 'department' ? ctx.value.departmentId : null,
      path: inSearchMode.value && it._path != null ? (it._path || '.') : pathForList,
      name: it.name,
      is_dir: it.is_dir,
    }))
    await axios.delete('/api/files', { data: { items: itemsPayload } })
    selected.value = []
    selectionMode.value = false
    await loadList()
  } catch (e) {
    window.alert((e.response && e.response.data && e.response.data.detail) || '删除失败')
  }
}

const renameSelected = async () => {
  if (selected.value.length !== 1) return
  const item = selected.value[0]
  const newName = window.prompt('请输入新名称：', item.name)
  if (!newName || newName === item.name) return
  try {
    await axios.put('/api/files/rename', {
      spaceType: ctx.value.spaceType,
      departmentId: ctx.value.spaceType === 'department' ? ctx.value.departmentId : null,
      path: inSearchMode.value && item._path != null ? (item._path || '.') : (ctx.value.path || '.'),
      oldName: item.name,
      newName,
      isDir: item.is_dir,
    })
    selected.value = []
    selectionMode.value = false
    if (inSearchMode.value) {
      await runSearch((shellSearchKeyword.value || '').trim())
    } else {
      await loadList()
    }
  } catch (e) {
    window.alert((e.response && e.response.data && e.response.data.detail) || '重命名失败')
  }
}

const createFolder = async () => {
  const name = (window.prompt('请输入新建文件夹名称：', '') || '').trim()
  if (!name) return
  try {
    await axios.post('/api/files/folder', {
      spaceType: ctx.value.spaceType,
      departmentId: ctx.value.spaceType === 'department' ? ctx.value.departmentId : null,
      path: ctx.value.path || '.',
      name,
    })
    await loadList()
  } catch (e) {
    window.alert((e.response && e.response.data && e.response.data.detail) || '新建文件夹失败')
  }
}

const downloadSelected = async () => {
  if (selected.value.length !== 1) return
  const it = selected.value[0]
  if (it.is_dir) return
  const pathForItem = inSearchMode.value && it._path != null ? (it._path || '.') : (ctx.value.path || '.')
  const url = buildDownloadUrl(it.name, pathForItem, false)
  window.open(url, '_blank')
}

const shareSelected = async () => {
  if (ctx.value.spaceType === 'safe') {
    window.alert('个人保险库不支持分享，请在公共或部门空间使用分享功能')
    return
  }

  const basePath = (ctx.value.path || '.')
  const payload = {
    spaceType: ctx.value.spaceType,
    departmentId: ctx.value.spaceType === 'department' ? (ctx.value.departmentId || null) : null,
    path: basePath === '.' ? '' : basePath,
    anchorName: '',
    selectedNames: [],
  }

  if (selected.value.length) {
    payload.anchorName = selected.value[0].name
    payload.selectedNames = selected.value.map((x) => x.name)
  }

  try {
    const { data: shareResp } = await axios.post('/api/share', payload)
    const shareId = shareResp.shareId
    const link = `${window.location.origin}/#/files?shareId=${encodeURIComponent(shareId)}`

    // 尽量保持与桌面端一致的说明
    const count = payload.selectedNames.length
    const titlePart = count === 0
      ? '一些文件/文件夹'
      : count === 1
        ? `文件“${payload.anchorName}”`
        : `共 ${count} 个文件/文件夹，例如“${payload.anchorName}”等`
    const shareText = [
      '我在 HBCloud 河北分院网盘分享了新的文件：',
      titlePart,
      '',
      '请在内网环境登录系统后使用本链接。',
      '',
      link,
    ].join('\n')

    // 审计失败不影响复制
    try {
      await axios.post('/api/audit/share', payload)
    } catch {
      // ignore
    }

    const ok = await copyToClipboard(shareText)
    window.alert(ok ? '已复制分享说明及链接' : '复制失败，请手动复制')
  } catch (e) {
    window.alert((e.response && e.response.data && e.response.data.detail) || '创建分享失败，请稍后重试')
  }
}

const addToFavorites = async () => {
  try {
    await axios.post('/api/files/favorites', {
      spaceType: ctx.value.spaceType,
      departmentId: ctx.value.spaceType === 'department' ? ctx.value.departmentId : null,
      path: ctx.value.path || '.',
      displayName: lastSegment(ctx.value.path) || '',
    })
    await loadFavorites()
    window.alert('已添加到快速访问')
  } catch (e) {
    window.alert((e.response && e.response.data && e.response.data.detail) || '添加失败')
  }
}

const shellSearchKeyword = ref('')

const updateTopBar = () => {
  const spaceLabel = ctx.value.spaceType === 'public' ? '公共空间' : ctx.value.spaceType === 'safe' ? '个人保险库' : (ctx.value.departmentId ? `部门空间 / ${ctx.value.departmentId}` : '部门空间')
  const folderLabel = (ctx.value.path && ctx.value.path !== '.' ? ctx.value.path : '根目录')
  const subtitle = level.value === 2 ? `${spaceLabel} · ${folderLabel}` : ''

  setMobileShell({
    title: level.value === 1 ? '浏览' : '文件浏览',
    subtitle,
    showBackPlaceholder: true,
    backEnabled: level.value === 2,
    onBack: goUpOrExit,
    showSearch: level.value === 2,
    searchPlaceholder: '搜索（当前目录及子文件夹）',
    onSearch: async (kw) => {
      shellSearchKeyword.value = kw || ''
      await runSearch(kw)
    },
    onClearSearch: clearSearch,
  })

  const uiMode = getUiMode()
  const switchLabel = uiMode === 'desktop' ? '切换到移动版' : '切换到桌面版'

  setMobileMenu([
    {
      key: 'refresh',
      label: '刷新',
      onClick: async () => {
        if (level.value === 1) {
          await Promise.all([loadFavorites(), loadDepartments()])
          return
        }
        await loadList()
      },
    },
    {
      key: 'select-clear',
      label: '清除选择',
      hidden: !selectionMode.value,
      onClick: async () => {
        selected.value = []
        selectionMode.value = false
      },
    },
    {
      key: 'upload',
      label: '上传文件',
      hidden: level.value !== 2,
      onClick: async () => openUpload(),
    },
    {
      key: 'mkdir',
      label: '新建文件夹',
      hidden: level.value !== 2,
      onClick: async () => createFolder(),
    },
    {
      key: 'fav-add',
      label: '收藏当前目录到快速访问',
      hidden: level.value !== 2,
      onClick: async () => addToFavorites(),
    },
    {
      key: 'download',
      label: '下载（需选中 1 个文件）',
      hidden: level.value !== 2,
      disabled: !(selected.value.length === 1 && selected.value[0] && !selected.value[0].is_dir),
      onClick: async () => downloadSelected(),
    },
    {
      key: 'share',
      label: '分享',
      hidden: level.value !== 2,
      disabled: ctx.value.spaceType === 'safe',
      onClick: async () => shareSelected(),
    },
    {
      key: 'rename',
      label: '重命名（需选中 1 项）',
      hidden: level.value !== 2,
      disabled: selected.value.length !== 1,
      onClick: async () => renameSelected(),
    },
    {
      key: 'delete',
      label: '删除（移入回收站）',
      hidden: level.value !== 2,
      disabled: selected.value.length === 0,
      onClick: async () => deleteSelected(),
    },
    {
      key: 'move',
      label: '移动（暂需桌面端）',
      hidden: level.value !== 2,
      disabled: true,
    },
    {
      key: 'copy',
      label: '复制（暂需桌面端）',
      hidden: level.value !== 2,
      disabled: true,
    },
    {
      key: 'help',
      label: '帮助',
      onClick: async () => router.push('/help'),
    },
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
          router.replace('/m/browse')
        } else {
          setUiMode('desktop')
          router.replace('/files')
        }
      },
    },
  ])
}

watch([level, () => ctx.value.spaceType, () => ctx.value.departmentId, () => ctx.value.path, selectionMode, selected], () => {
  nextTick(() => updateTopBar())
})

onMounted(async () => {
  resetMobileShell()
  await Promise.all([loadFavorites()])
  updateTopBar()
})

onUnmounted(() => {
  resetMobileShell()
})
</script>

<style scoped>
.m-hidden-input {
  display: none;
}

.m-layer {
  padding: 6px 0 0;
}

.m-section {
  margin-top: 14px;
}

.m-section-head {
  width: 100%;
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 2px;
}

.m-section-title {
  font-size: 14px;
  color: #111827;
  font-weight: 700;
}

.m-caret {
  color: #6b7280;
}

.m-card {
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.m-row {
  width: 100%;
  border: none;
  background: #fff;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 14px;
  border-top: 1px solid #f3f4f6;
  text-align: left;
}

.m-row:first-child {
  border-top: none;
}

.m-row.sub {
  padding-left: 24px;
}

.m-row .ico {
  width: 28px;
  text-align: center;
  font-size: 18px;
}

.m-row .name {
  flex: 1;
  min-width: 0;
}

.fav-title {
  display: block;
  font-size: 15px;
  color: #111827;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fav-sub {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.m-row .right {
  color: #9ca3af;
}

.m-sub {
  background: #fff;
}

.m-sub-empty {
  padding: 12px 14px;
  color: #6b7280;
  font-size: 13px;
}

.m-loading {
  color: #6b7280;
  padding: 14px 2px;
}

.m-empty {
  color: #6b7280;
  padding: 18px 2px;
}

.m-list {
  margin-top: 10px;
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
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

.sel {
  width: 26px;
  display: flex;
  justify-content: center;
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

.m-item-main .ico {
  width: 22px;
  text-align: center;
}

.m-item-main .name {
  flex: 1;
  min-width: 0;
}

.n1 {
  display: block;
  font-size: 15px;
  font-weight: 600;
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

.m-item-main .right {
  color: #9ca3af;
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

.m-preview {
  width: min(520px, 96vw);
  background: #111827;
  border-radius: 14px;
  overflow: hidden;
}

.m-preview img {
  width: 100%;
  height: auto;
  display: block;
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
