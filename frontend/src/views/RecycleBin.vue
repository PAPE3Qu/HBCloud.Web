<template>
  <transition name="fade-page" appear>
    <div class="recycle-bin">
      <div class="toolbar">
        <div class="left">
          <h2 class="title">回收站</h2>
          <span class="summary">共 {{ total }} 项</span>
        </div>
        <div class="right">
          <input
            v-model="keyword"
            type="text"
            class="keyword-input"
            placeholder="按名称或原路径搜索"
            @keyup.enter="loadList"
          />
          <select v-model="scope" class="select-basic" @change="onFilterChange">
            <option value="all">全部类型</option>
            <option value="file">文件/文件夹</option>
            <option value="department">部门</option>
          </select>
          <select v-model="spaceType" class="select-basic" @change="onFilterChange">
            <option value="">所有空间</option>
            <option value="public">公共空间</option>
            <option value="department">部门空间</option>
            <option value="safe">个人保险库</option>
          </select>
          <button class="btn" type="button" @click="loadList">刷新</button>
          <button
            class="btn"
            type="button"
            :disabled="selectedIds.length === 0"
            @click="onRestoreSelected"
          >还原选中</button>
          <button
            class="btn btn-danger"
            type="button"
            :disabled="selectedIds.length === 0"
            @click="onPurgeSelected"
          >彻底删除选中</button>
          <button
            v-if="isSuperAdmin"
            class="btn btn-danger"
            type="button"
            :disabled="total === 0"
            @click="onEmptyAll"
          >清空回收站</button>
        </div>
      </div>

      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th style="width: 40px; text-align: center">
                <input type="checkbox" :checked="isAllChecked" @change="toggleAll" />
              </th>
              <th style="width: 80px">类型</th>
              <th>名称</th>
              <th>原空间</th>
              <th>原路径</th>
              <th style="width: 150px">删除时间</th>
              <th style="width: 120px">删除人</th>
              <th style="width: 190px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="loading">加载中...</td>
            </tr>
            <tr
              v-for="it in items"
              :key="it.id"
              class="row-btn"
              :class="{ selected: selectedIds.includes(it.id) }"
              @click="onRowClick(it)"
            >
              <td style="text-align: center" @click.stop>
                <input type="checkbox" :checked="selectedIds.includes(it.id)" @change="toggleOne(it.id)" />
              </td>
              <td>
                <span v-if="it.scope === 'department'">部门</span>
                <span v-else-if="it.isDir">文件夹</span>
                <span v-else>文件</span>
              </td>
              <td>
                <span class="cell-text" :title="it.scope === 'department' ? (it.departmentId || it.name) : it.name">
                  {{ it.scope === 'department' ? (it.departmentId || it.name) : it.name }}
                </span>
              </td>
              <td>{{ formatSpace(it) }}</td>
              <td>
                <span class="cell-text" :title="it.originalPath || '/'">
                  {{ it.originalPath || '/' }}
                </span>
              </td>
              <td>{{ formatTime(it.deletedAt) }}</td>
              <td>{{ it.deletedBy || '-' }}</td>
              <td class="ops" @click.stop>
                <button class="op-btn" type="button" @click="onLocate(it)">定位</button>
                <button class="op-btn" type="button" @click="onRestoreSingle(it.id)">还原</button>
                <button class="op-btn op-danger" type="button" @click="onPurgeSingle(it.id)">彻底删除</button>
              </td>
            </tr>
            <tr v-if="!loading && items.length === 0">
              <td colspan="8" class="empty">暂无回收内容</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 任务遮罩：复用与文件浏览类似的风格，用于彻底删除/清空等耗时操作 -->
      <transition name="fade-task">
        <div v-if="busyTask.active" class="task-mask">
          <div class="task-dialog">
            <div class="task-title">{{ busyTask.text }}</div>
            <div class="task-tip">请勿关闭页面或频繁重复操作，耐心等待当前任务完成。</div>
            <div class="task-progress-bar">
              <div class="task-progress-inner" :style="{ width: busyTask.percent + '%' }"></div>
            </div>
            <div class="task-progress-text">{{ busyTask.percent }}%</div>
          </div>
        </div>
      </transition>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const items = ref([])
const total = ref(0)
const loading = ref(false)
const scope = ref('all')
const spaceType = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(200)
const selectedIds = ref([])

const currentUser = ref(null)

const loadCurrentUser = () => {
  const raw = localStorage.getItem('hbcloud_user')
  if (!raw) return
  try {
    currentUser.value = JSON.parse(raw)
  } catch {
    currentUser.value = null
  }
}

const isSuperAdmin = computed(() => currentUser.value && currentUser.value.role === 'super')

const isAllChecked = computed(() => {
  return items.value.length > 0 && selectedIds.value.length === items.value.length
})

const toggleAll = (e) => {
  if (e.target.checked) {
    selectedIds.value = items.value.map((it) => it.id)
  } else {
    selectedIds.value = []
  }
}

const toggleOne = (id) => {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]
  }
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
  const hit = departments.value.find(d => d.id === id)
  return hit ? hit.name : id
}

const formatSpace = (it) => {
  if (it.spaceType === 'public') return '公共空间'
  if (it.spaceType === 'safe') return '个人保险库'
  if (it.spaceType === 'department') {
    // 文件/文件夹：显示“部门空间 / 具体部门名”
    if (it.scope !== 'department') {
      const extra = it.extra || {}
      const extraName = (extra.deptName || extra.departmentName || extra.name || '').trim()
      const name = extraName || findDeptName(it.departmentId)
      return name ? `部门空间 / ${name}` : '部门空间'
    }
    // 部门本身被删除：展示为“部门（XXX）”
    const extra = it.extra || {}
    const extraName = (extra.deptName || extra.departmentName || extra.name || '').trim()
    const name = extraName || findDeptName(it.departmentId)
    return name ? `部门（${name}）` : '部门'
  }
  return it.spaceType || '-'
}

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const pad = (n) => (n < 10 ? '0' + n : '' + n)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const loadList = async () => {
  loading.value = true
  selectedIds.value = []
  try {
    const params = {
      page: page.value,
      pageSize: pageSize.value,
    }
    if (scope.value && scope.value !== 'all') params.scope = scope.value
    if (spaceType.value) params.spaceType = spaceType.value
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    const { data } = await axios.get('/api/files/recycle/list', { params })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    items.value = []
    total.value = 0
    // 简单提示即可
    window.alert((e.response && e.response.data && e.response.data.detail) || '加载回收站失败')
  } finally {
    loading.value = false
  }
}

const onFilterChange = () => {
  page.value = 1
  loadList()
}

// 任务遮罩状态（与 FileBrowser 中 busyTask 保持风格一致）
const busyTask = ref({ active: false, text: '', percent: 0 })
let busyTimer = null

const startBusy = (text) => {
  busyTask.value = { active: true, text, percent: 5 }
  if (busyTimer) {
    clearInterval(busyTimer)
    busyTimer = null
  }
  // 简单线性增加，最多到 95%
  busyTimer = setInterval(() => {
    if (!busyTask.value.active) return
    if (busyTask.value.percent >= 95) return
    busyTask.value = {
      ...busyTask.value,
      percent: busyTask.value.percent + 3,
    }
  }, 800)
}

const finishBusy = (text) => {
  busyTask.value = { ...busyTask.value, text, percent: 100 }
  if (busyTimer) {
    clearInterval(busyTimer)
    busyTimer = null
  }
  setTimeout(() => {
    busyTask.value = { active: false, text: '', percent: 0 }
  }, 400)
}

const onRestoreSelected = async () => {
  if (!selectedIds.value.length) return
  startBusy(`正在还原 ${selectedIds.value.length} 项，请稍候…`)
  try {
    const { data } = await axios.post('/api/files/recycle/restore', { ids: selectedIds.value })

    const restored = (data && data.restored) ? data.restored : []
    const failed = (data && data.failed) ? data.failed : []

    // 先刷新列表，让已成功处理的项消失
    await loadList()

    if (failed.length) {
      finishBusy('还原完成（部分未处理）')
      setTimeout(() => {
        // 按需求：不展开原因，只给统一口径
        window.alert('部分项目无权操作，请联系管理员。')
      }, 100)
      return
    }

    // 全成功
    finishBusy(restored.length ? '还原完成' : '未还原任何项目')
  } catch (e) {
    finishBusy('还原失败')
    setTimeout(() => {
      if (e.response && e.response.status === 403) {
        window.alert('空间未开放或无访问权限，请联系管理员')
      } else {
        window.alert((e.response && e.response.data && e.response.data.detail) || '还原失败')
      }
    }, 100)
  }
}

const onPurgeSelected = async () => {
  if (!selectedIds.value.length) return
  const ok = window.confirm(`将彻底删除选中的 ${selectedIds.value.length} 项，操作不可恢复，是否确认？`)
  if (!ok) return
  startBusy(`正在彻底删除 ${selectedIds.value.length} 项，请稍候…`)
  try {
    const { data } = await axios.post('/api/files/recycle/purge', { ids: selectedIds.value })

    const purged = (data && data.purged) ? data.purged : []
    const failed = (data && data.failed) ? data.failed : []

    await loadList()

    if (failed.length) {
      finishBusy('彻底删除完成（部分未处理）')
      setTimeout(() => {
        window.alert('部分项目无权操作，请联系管理员。')
      }, 100)
      return
    }

    finishBusy(purged.length ? '彻底删除完成' : '未删除任何项目')
  } catch (e) {
    finishBusy('彻底删除失败')
    setTimeout(() => {
      window.alert((e.response && e.response.data && e.response.data.detail) || '彻底删除失败')
    }, 100)
  }
}

const onRestoreSingle = async (id) => {
  selectedIds.value = [id]
  await onRestoreSelected()
}

const onPurgeSingle = async (id) => {
  selectedIds.value = [id]
  await onPurgeSelected()
}

const onEmptyAll = async () => {
  if (!isSuperAdmin.value) return
  if (!total.value) return
  const ok = window.confirm('将清空回收站中当前所有内容，操作不可恢复，是否确认？')
  if (!ok) return
  startBusy('正在清空回收站，请稍候…')
  try {
    await axios.post('/api/files/recycle/empty')
    await loadList()
    finishBusy('清空完成')
  } catch (e) {
    finishBusy('清空失败')
    setTimeout(() => {
      window.alert((e.response && e.response.data && e.response.data.detail) || '清空回收站失败')
    }, 100)
  }
}

const router = useRouter()

const copyText = async (text) => {
  const t = String(text || '')
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(t)
      return
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
  } catch {
    // ignore
  }
}

const onLocate = async (it) => {
  // 部门被删除的条目：无法定位到文件浏览
  if (it.scope === 'department') {
    window.alert('部门类型记录不支持定位。')
    return
  }

  // 原始位置：spaceType + (departmentId) + originalPath + name
  const q = {
    spaceType: it.spaceType || 'public',
    path: it.originalPath || '.',
    name: it.name || '',
  }
  if (it.spaceType === 'department' && it.departmentId) {
    q.departmentId = it.departmentId
  }

  // 跳转到文件管理页，并高亮目标文件
  await router.push({ path: '/files', query: q })
}

const onRowClick = async (it) => {
  toggleOne(it.id)
  // 单击行时，如果点的是“原路径”列（无按钮），不做复制，避免误触。
}

onMounted(async () => {
  loadCurrentUser()
  await loadDepartments()
  await loadList()
})
</script>

<style scoped>
.recycle-bin {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 页面淡入：进入回收站时轻微淡入，统一 0.15s */
.fade-page-enter-active,
.fade-page-leave-active {
  transition: opacity 0.15s ease;
}
.fade-page-enter-from,
.fade-page-leave-to {
  opacity: 0;
}

/* 任务遮罩淡入淡出，统一 0.15s */
.fade-task-enter-active,
.fade-task-leave-active {
  transition: opacity 0.15s ease;
}
.fade-task-enter-from,
.fade-task-leave-to {
  opacity: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.title {
  margin: 0;
  font-size: 1.1rem;
}

.summary {
  font-size: 0.9rem;
  color: #6b7280;
}

.right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.keyword-input {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  min-width: 200px;
  font-size: 0.9rem;
}

.select-basic {
  min-width: 110px;
  padding: 0.35rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #e5e7eb;
  color: #111827;
  font-size: 0.85rem;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.select-basic:hover {
  background-color: #d1d5db;
  border-color: #6b7280;
}

.select-basic:focus {
  outline: none;
  border-color: #2563eb;
  background-color: #e0edff;
}

.btn {
  min-width: 90px;
  padding: 0.25rem 0.9rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #e5e7eb;
  color: #111827;
  font-size: 0.85rem;
  cursor: pointer;
}

.btn:hover:enabled {
  background-color: #d1d5db;
}

.btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.btn-danger {
  border-color: #fca5a5;
  color: #b91c1c;
}

.btn-danger:hover:enabled {
  background-color: #fee2e2;
}

.table-wrapper {
  flex: 1 1 auto;
  overflow: auto;
  background-color: #ffffff;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

.table-wrapper table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

th,
td {
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.9rem;
}

th {
  background-color: #f3f4f6;
  text-align: left;
}

.loading,
.empty {
  text-align: center;
  color: #6b7280;
}

.ops {
  text-align: right;
  white-space: nowrap;
}

.op-btn {
  display: inline-block;
  margin-left: 4px;
  padding: 0.15rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #f4f4f4;
  color: #111827;
  font-size: 0.8rem;
  cursor: pointer;
}

.op-btn.op-danger {
  border-color: #fca5a5;
  color: #b91c1c;
}

.op-btn:hover {
  background-color: #d1d5db;
}

.task-mask {
  position: fixed;
  inset: 0;
  background-color: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 998;
}

.task-dialog {
  min-width: 260px;
  max-width: 360px;
  background-color: #ffffff;
  border-radius: 4px;
  padding: 12px 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
  transition: transform 0.15s ease, opacity 0.15s ease;
}

.task-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
}

.task-tip {
  font-size: 12px;
  color: #6b7280;
}

.task-progress-bar {
  margin-top: 6px;
  width: 100%;
  height: 6px;
  background-color: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
}

.task-progress-inner {
  height: 100%;
  background-color: #059669;
  transition: width 0.15s ease;
}

.task-progress-text {
  margin-top: 4px;
  font-size: 12px;
  color: #374151;
  text-align: right;
}

/* 表格单元格按钮化：避免文字被当作普通文本选中 */
.cell-btn,
.cell-link-btn {
  display: none;
}

/* 整行按钮化：不使用边框，仅 hover/selected 变色；避免文本选中 */
.row-btn {
  cursor: pointer;
  user-select: none;
}

.row-btn:hover {
  background-color: #f3f4f6;
}

.row-btn.selected {
  background-color: #eff6ff;
}

/* 单元格文本：超出省略，跟随行 hover/selected 变色 */
.cell-text {
  display: inline-block;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 定位按钮与其它按钮一致，但稍短 */
.ops .op-btn {
  margin-left: 4px;
}
</style>