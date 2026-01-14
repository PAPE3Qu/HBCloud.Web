<template>
  <div class="home-layout" :class="{ 'is-mobile-shell': isMobileShell }">
    <div class="home-center">
      <div ref="publishCardRef" class="publish-card card card-elevated">
        <div class="publish-header">
          <div class="avatar-circle"></div>
          <div class="publish-meta">
            <div class="publish-title">{{ editingId ? '编辑动态' : '发布新动态' }}</div>
            <div class="publish-sub">发布最新的资料更新、通知说明等内容</div>
          </div>
        </div>
        <div class="publish-body">
          <!-- 标题输入：占满整行 -->
          <div class="row">
            <input class="input title-input" v-model="title" placeholder="填写一个简短的标题（可选）" />
          </div>
          <!-- 正文输入：占满卡片宽度，字号稍大 -->
          <div class="row">
            <textarea
              class="textarea content-input"
              v-model="content"
              placeholder="发布内容正文。例如：本周新增了某某资料，具体路径在……"
            ></textarea>
          </div>
          <!-- 发布者 + 部门 -->
          <div class="row row-inline">
            <div class="field">
              <div class="field-label">发布身份</div>
              <input class="input" v-model="author" placeholder="必填，如：张三 或 人事部" disabled />
            </div>
            <div class="field">
              <div class="field-label">部门</div>
              <select class="select-basic" v-model="postDepartmentId">
                <option value="">公共空间</option>
                <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
              </select>
            </div>
          </div>
          <!-- 附件选择 -->
          <div class="row attachments-row">
            <div class="attachments">
              <button class="btn btn-primary" type="button" @click="openAttachPicker">
                选择附件
              </button>
              <div class="attach-list" v-if="attachments.length">
                <span v-for="(a, idx) in attachments" :key="idx" class="attach-chip">
                  <span class="chip-text">{{ a.name }}</span>
                  <button class="chip-close" type="button" @click="removeAttachment(idx)">✕</button>
                </span>
              </div>
              <div class="hint">最多选择 5 个文件 或 1 个文件夹（不可混用）</div>
            </div>
          </div>
        </div>
        <div class="publish-footer">
          <button
            class="btn btn-primary"
            type="button"
            @click="onPublish"
            :disabled="!content.trim() || !author.trim()"
          >
            {{ editingId ? '保存编辑' : '发布动态' }}
          </button>
          <button class="btn btn-ghost" type="button" v-if="editingId" @click="onCancelEdit">取消编辑</button>
        </div>
      </div>

      <div class="list-card card card-elevated">
        <div class="list-header">
          <div class="list-title">最新动态</div>
          <div class="list-filter">
            <span class="field-label field-label-muted">部门 筛选</span>
            <select class="select-basic" v-model="filterDepartmentId" @change="loadPosts">
              <option value="">全部</option>
              <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>
        </div>
        <!-- 动态列表：去掉“暂无公告”参与过渡，避免先出现再瞬间消失导致整体位移 -->
        <transition-group name="post-fade" tag="div" class="posts">
          <div class="post-card" v-for="p in posts" :key="p.id">
            <div class="post-header">
              <div class="post-avatar">{{ (p.author || '用').slice(0,1) }}</div>
              <div class="post-head-main">
                <div class="post-title">{{ p.title || '（无标题）' }}</div>
                <div class="post-meta">
                  <span class="meta-author">{{ p.author || '匿名' }}</span>
                  <span class="meta-dot">·</span>
                  <span class="meta-time">{{ formatTime(p.created_at) }}</span>
                  <span v-if="p.departmentId" class="meta-dept">｜{{ findDeptName(p.departmentId) }}</span>
                </div>
              </div>
            </div>
            <div class="post-content">{{ p.content }}</div>
            <div class="post-attachments" v-if="p.attachments && p.attachments.length">
              <div class="post-attachments-header">
                <span class="attach-title">附件（{{ p.attachments.length }}）</span>
              </div>
              <div class="post-attach-list">
                <button
                  v-for="(a, idx) in p.attachments"
                  :key="idx"
                  class="attach-item-btn"
                  type="button"
                  @click="openAttachment(a)"
                >
                  <span class="attach-name">{{ a.name }}</span>
                </button>
              </div>
            </div>
            <div class="post-footer">
              <div class="post-footer-left">
                <button
                  v-if="p.attachments && p.attachments.length"
                  class="btn btn-ghost btn-sm"
                  type="button"
                  @click="downloadAllAttachments(p)"
                >
                  打包下载全部
                </button>
              </div>
              <div class="post-actions">
                <button
                  class="btn btn-sm"
                  type="button"
                  @click="onEditPost(p)"
                  :disabled="!canManagePost(p)"
                >
                  编辑
                </button>
                <button
                  class="btn btn-sm btn-danger"
                  type="button"
                  @click="onDeletePost(p)"
                  :disabled="!canManagePost(p)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </transition-group>

        <!-- 单独渲染“暂无公告”，不放在 transition-group 里 -->
        <div v-if="!posts.length && !loading" class="empty empty-static">
          暂无公告
        </div>

        <div class="pagination" v-if="total > 0">
          <button class="btn" type="button" :disabled="page<=1" @click="goto(page-1)">上一页</button>
          <span class="page-info">第 {{ page }} / {{ totalPages }} 页</span>
          <button class="btn" type="button" :disabled="page>=totalPages" @click="goto(page+1)">下一页</button>
        </div>
      </div>
    </div>

    <aside v-if="!isMobileShell" class="home-right">
      <div class="right-card tips-card">
        <div class="right-title">使用小提示</div>
        <transition name="fade-tip" mode="out-in">
          <p class="tip-text" :key="currentTipIndex">{{ tips[currentTipIndex] }}</p>
        </transition>
      </div>
      <div class="right-card calendar-card">
        <div class="right-title">日历</div>
        <div class="calendar-placeholder">
          <div class="calendar-date">{{ todayStr }}</div>
          <div class="calendar-week">周{{ weekDayStr }}</div>
        </div>
      </div>
      <div class="right-card feedback-card">
        <div class="right-title">留言 / 反馈</div>
        <textarea
          v-model="feedbackText"
          class="feedback-textarea"
          rows="4"
          placeholder="欢迎留下您对系统使用的建议或问题，这里只在后台查看，不对外展示。"
        ></textarea>
        <button
          class="feedback-btn"
          type="button"
          :disabled="submittingFeedback || !feedbackText.trim()"
          @click="submitFeedback"
        >
          {{ submittingFeedback ? '提交中...' : '提交反馈' }}
        </button>
        <div class="feedback-meta">已收到 {{ feedbackCount }} 条反馈</div>
      </div>
    </aside>

    <!-- 回到顶部按钮 -->
    <transition name="fade-back-top">
      <button
        v-if="showBackTop"
        type="button"
        class="back-top-btn"
        @click="scrollToTop"
      >↑ 回到顶部</button>
    </transition>

    <!-- 选择附件弹窗：增加淡入淡出过渡 -->
    <transition name="fade-dialog">
    <div v-if="showAttachPicker" class="mask" @click="closeAttachPicker">
      <div class="dialog" @click.stop>
        <!-- 头部：空间/部门选择，放在同一行，各占一半宽度 -->
        <div class="row picker-header-row">
          <label class="field picker-field">
            <span class="field-label">空间</span>
            <select class="select-basic" v-model="pickerSpaceType" @change="resetPicker" :disabled="postDepartmentId">
              <option value="public">公共空间</option>
              <option value="department">部门空间</option>
            </select>
          </label>
          <label class="field picker-field" v-if="pickerSpaceType === 'department'">
            <span class="field-label">部门</span>
            <select
              class="select-basic"
              v-model="pickerDepartmentId"
              @change="resetPicker"
              :disabled="postDepartmentId"
            >
              <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </label>
          <div class="picker-field" v-else></div>
        </div>
        <!-- 路径导航 -->
        <div class="row">
          <div class="picker-pathbar">
            <button class="btn btn-icon" type="button" @click="pickerGoRoot">首页</button>
            <button class="btn btn-icon" type="button" @click="pickerGoUp" :disabled="!pickerCanGoUp">上级</button>
            <span class="path">当前路径：/{{ pickerPath }}</span>
          </div>
        </div>
        <!-- 列表操作提示 -->
        <div class="row">
          <div class="picker-actions">
            <button class="btn" type="button" @click="loadPicker">刷新</button>
            <span class="hint">勾选选择：最多5文件或1文件夹（不可混用）。双击文件夹浏览文件夹内部。</span>
          </div>
        </div>
        <!-- 文件列表 -->
        <div class="picker-list">
          <table>
            <thead>
              <tr>
                <th style="width:36px;text-align:center">
                  <input type="checkbox" disabled />
                </th>
                <th>名称</th>
                <th>类型</th>
                <th>大小</th>
                <th>修改时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="it in pickerItems" :key="it.name" :class="{ dir: it.is_dir }">
                <td style="text-align:center">
                  <input
                    type="checkbox"
                    :checked="isPickerSelected(it)"
                    :disabled="isPickerCheckboxDisabled(it)"
                    @change="togglePickerSelect(it)"
                  />
                </td>
                <td>
                  <!-- 用按钮承载交互：文件夹点击进入；文件点击选择/取消选择 -->
                  <button
                    class="picker-name-btn"
                    type="button"
                    :class="{ dir: it.is_dir }"
                    @dblclick="onPickerDblClick(it)"
                    @click="it.is_dir ? onPickerDblClick(it) : togglePickerSelect(it)"
                    :title="it.is_dir ? '进入文件夹' : '选择/取消选择'"
                  >
                    <span class="picker-name-icon" aria-hidden="true">{{ getFileIcon(it, it.is_dir) }}</span>
                    <span class="picker-name-text">{{ it.name }}</span>
                    <span v-if="it.is_dir" class="picker-enter-hint" aria-hidden="true">进入</span>
                  </button>
                </td>
                <td>{{ it.is_dir ? '文件夹' : '文件' }}</td>
                <td>{{ it.is_dir ? '-' : formatSize(it.size) }}</td>
                <td>{{ formatTime(it.modified_time) }}</td>
              </tr>
              <tr v-if="!pickerItems.length && !pickerLoading">
                <td colspan="5" class="empty">暂无数据</td>
              </tr>
              <tr v-if="pickerLoading">
                <td colspan="5" class="loading">加载中...</td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- 底部：大小提示 + 按钮 -->
        <div class="row picker-footer">
          <div style="flex: 1;">
            <div class="hint" style="margin-bottom: 8px;">
              已选大小：{{ pickerSelectedSizeGB }}GB
              <span v-if="pickerSizeExceedsLimit" style="color: #e74c3c; font-weight: bold;">
                （超过1G限制，可能出现下载错误）
              </span>
            </div>
          </div>
          <button class="btn btn-primary" type="button" @click="confirmAttachments">确定</button>
          <button class="btn" type="button" @click="closeAttachPicker">取消</button>
        </div>
      </div>
    </div>
  </transition>
    <!-- 首页打包任务遮罩：保持原有结构，只统一过渡时间 -->
    <transition name="fade-task">
      <div v-if="busyTask.active" class="task-mask">
        <div class="task-dialog">
          <div class="task-title">{{ busyTask.text }}</div>
          <div class="task-tip">请勿频繁重复操作，耐心等待当前打包任务完成。</div>
          <div class="task-progress-bar">
            <div class="task-progress-inner" :style="{ width: busyTask.percent + '%' }"></div>
          </div>
          <div class="task-progress-text">{{ busyTask.percent }}%</div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const isMobileShell = computed(() => (route.path || '').startsWith('/m'))

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

loadCurrentUser()

const isSuper = computed(() => currentUser.value && currentUser.value.role === 'super')

// 使用发布人姓名 author 与当前登录用户姓名匹配，保证本人可编辑/删除；超级管理员可管理所有动态
const canManagePost = (post) => {
  if (!currentUser.value) return false
  if (isSuper.value) return true
  const userName = (currentUser.value.name || '').trim()
  const postAuthor = (post.author || '').trim()
  if (!userName || !postAuthor) return false
  return userName === postAuthor
}

const posts = ref([])

const publishCardRef = ref(null)
const title = ref('')
const content = ref('')
const author = ref('')
const postDepartmentId = ref('')
const attachments = ref([])
const editingId = ref(null)

const departments = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const filterDepartmentId = ref('')

// 附件选择器状态
const showAttachPicker = ref(false)
const pickerSpaceType = ref('public')
const pickerDepartmentId = ref('')
const pickerPath = ref('')
const pickerItems = ref([])
const pickerLoading = ref(false)
const pickerSelected = ref([]) // { name, is_dir }

const pickerCanGoUp = computed(() => pickerPath.value && pickerPath.value !== '')

// 计算已选项目的总大小
const pickerSelectedSize = computed(() => {
  return pickerSelected.value.reduce((sum, item) => {
    // 直接使用item中的size，因为选择文件夹时已经异步获取了实际大小
    return sum + (Number(item.size) || 0)
  }, 0)
})

const pickerSelectedSizeGB = computed(() => (pickerSelectedSize.value / 1024 / 1024 / 1024).toFixed(2))
const pickerSizeExceedsLimit = computed(() => pickerSelectedSize.value > 1024 * 1024 * 1024)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const pad = (n) => (n < 10 ? '0' + n : '' + n)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const formatSize = (size) => {
  if (size === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let idx = 0
  let val = size
  while (val >= 1024 && idx < units.length - 1) {
    val /= 1024
    idx++
  }
  return `${val.toFixed(1)} ${units[idx]}`
}

const loadDepartments = async () => {
  const { data } = await axios.get('/api/files/departments')
  departments.value = data || []
}

const loadPosts = async () => {
  loading.value = true
  try {
    const params = { page: page.value, pageSize: pageSize.value }
    if (filterDepartmentId.value) params.departmentId = filterDepartmentId.value
    const { data } = await axios.get('/api/home/posts', { params })
    posts.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
      posts.value = []
      total.value = 0
    } else if (e.response && e.response.status === 404) {
      posts.value = []
      total.value = 0
    } else {
      console.error('加载首页公告失败', e)
    }
  } finally {
    loading.value = false
  }
}

// 打开附件选择器时，禁止选择 safe 空间
const openAttachPicker = () => {
  showAttachPicker.value = true
  pickerSelected.value = []
  pickerPath.value = ''
  // 规则：公开动态只能选公共空间；部门动态只能选同部门空间
  if (postDepartmentId.value) {
    pickerSpaceType.value = 'department'
    pickerDepartmentId.value = postDepartmentId.value
  } else {
    pickerSpaceType.value = 'public'
    pickerDepartmentId.value = ''
  }
  loadPicker()
}

const closeAttachPicker = () => {
  showAttachPicker.value = false
}

const resetPicker = () => {
  pickerPath.value = ''
  pickerSelected.value = []
  // 若当前是部门动态，则强制锁定空间与部门，不允许切换
  if (postDepartmentId.value) {
    pickerSpaceType.value = 'department'
    pickerDepartmentId.value = postDepartmentId.value
  } else {
    pickerSpaceType.value = 'public'
    pickerDepartmentId.value = ''
  }
  loadPicker()
}

const pickerGoUp = () => {
  if (!pickerPath.value) return
  const parts = pickerPath.value.split('/')
  parts.pop()
  pickerPath.value = parts.join('/')
  loadPicker()
}

const pickerGoRoot = () => {
  pickerPath.value = ''
  loadPicker()
}

const loadPicker = async () => {
  pickerLoading.value = true
  try {
    // 不允许 safe 空间作为动态附件来源
    if (pickerSpaceType.value === 'safe') {
      pickerItems.value = []
      return
    }
    // 部门动态：必须选定部门，且与发布部门一致
    if (postDepartmentId.value) {
      pickerSpaceType.value = 'department'
      pickerDepartmentId.value = postDepartmentId.value
    }
    if (pickerSpaceType.value === 'department' && !pickerDepartmentId.value) {
      pickerItems.value = []
      return
    }

    const params = {
      spaceType: pickerSpaceType.value,
      path: pickerPath.value || ''
    }
    if (pickerSpaceType.value === 'department') {
      params.departmentId = pickerDepartmentId.value
    }
    const { data } = await axios.get('/api/files/list', { params })
    pickerItems.value = data.items || []
  } catch (e) {
    console.error('loadPicker failed', e)
    pickerItems.value = []
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
    }
  } finally {
    pickerLoading.value = false
  }
}

const onPickerDblClick = (it) => {
  if (!it.is_dir) return
  const parts = pickerPath.value ? pickerPath.value.split('/') : []
  parts.push(it.name)
  pickerPath.value = parts.join('/')
  loadPicker()
}

const isPickerSelected = (it) => pickerSelected.value.some(s => s.name === it.name && s.is_dir === it.is_dir)

const isPickerCheckboxDisabled = (it) => {
  const hasDir = pickerSelected.value.some(a => a.is_dir)
  const filesCount = pickerSelected.value.filter(a => !a.is_dir).length
  if (hasDir) {
    // 已选文件夹：禁用所有未选的文件和文件夹（只能有一个）
    return !isPickerSelected(it)
  }
  if (filesCount >= 5) {
    // 已选5文件：禁用所有未选的文件，文件夹也禁用（不能混用）
    return !isPickerSelected(it)
  }
  // 未达到限制：如果当前是文件夹且已有文件选择，则禁用（不能混用）
  if (it.is_dir && filesCount > 0) return true
  return false
}

const togglePickerSelect = (it) => {
  const sel = isPickerSelected(it)
  if (sel) {
    pickerSelected.value = pickerSelected.value.filter(s => !(s.name === it.name && s.is_dir === it.is_dir))
  } else {
    // 规则校验
    const hasDir = pickerSelected.value.some(a => a.is_dir)
    const filesCount = pickerSelected.value.filter(a => !a.is_dir).length
    if (it.is_dir) {
      if (pickerSelected.value.length > 0) return
      // 文件夹：添加时计算实际大小
      const calcDirSize = async () => {
        try {
          const params = {
            spaceType: pickerSpaceType.value,
            path: pickerPath.value || '',
            name: it.name
          }
          if (pickerSpaceType.value === 'department') {
            params.departmentId = pickerDepartmentId.value
          }
          const { data } = await axios.get('/api/files/dir-size', { params })
          const dirSize = data.size || 0
          // 先添加到选中列表（先用size=0占位）
          const newItem = { name: it.name, is_dir: true, size: dirSize }
          if (!pickerSelected.value.some(s => s.name === it.name && s.is_dir === it.is_dir)) {
            pickerSelected.value.push(newItem)
          } else {
            // 如果已存在，更新其size
            const idx = pickerSelected.value.findIndex(s => s.name === it.name && s.is_dir === it.is_dir)
            if (idx >= 0) {
              pickerSelected.value[idx].size = dirSize
            }
          }
        } catch (e) {
          console.error('获取文件夹大小失败', e)
          // 如果获取失败，仍然添加但size为0
          if (!pickerSelected.value.some(s => s.name === it.name && s.is_dir === it.is_dir)) {
            pickerSelected.value.push({ name: it.name, is_dir: true, size: 0 })
          }
        }
      }
      // 先添加占位，然后获取大小
      pickerSelected.value.push({ name: it.name, is_dir: true, size: 0 })
      calcDirSize()
    } else {
      if (hasDir) return
      if (filesCount >= 5) return
      pickerSelected.value.push({ name: it.name, is_dir: false, size: it.size || 0 })
    }
  }
}

const confirmAttachments = () => {
  // 按当前空间/部门/路径生成附件数组
  const attBase = {
    spaceType: pickerSpaceType.value,
    departmentId: pickerSpaceType.value === 'department' ? pickerDepartmentId.value : null,
    path: pickerPath.value || ''
  }
  attachments.value = pickerSelected.value.map(s => ({ 
    ...attBase, 
    name: s.name, 
    is_dir: s.is_dir,
    size: s.size || 0
  }))
  closeAttachPicker()
}

const removeAttachment = (idx) => {
  attachments.value.splice(idx, 1)
}

const resetForm = () => {
  title.value = ''
  content.value = ''
  // 保留发布身份为当前登录者姓名，不清空 author
  postDepartmentId.value = ''
  attachments.value = []
  editingId.value = null
}

const onPublish = async () => {
  const usedAuthor = (currentUser.value && currentUser.value.name) || author.value
  if (!usedAuthor || !usedAuthor.trim()) {
    alert('当前未获取到登录用户姓名，请重新登录或联系管理员。')
    return
  }
  // 前置校验：附件空间必须与动态空间一致
  if (postDepartmentId.value) {
    const bad = attachments.value.some(a => a.spaceType !== 'department' || (a.departmentId || '') !== postDepartmentId.value)
    if (bad) {
      alert('部门动态仅允许选择当前部门空间内的附件')
      return
    }
  } else {
    const bad = attachments.value.some(a => a.spaceType !== 'public')
    if (bad) {
      alert('公开动态仅允许选择公共空间附件')
      return
    }
  }

  try {
    const payload = {
      title: title.value || '',
      content: content.value,
      author: usedAuthor.trim(),
      departmentId: postDepartmentId.value || null,
      attachments: attachments.value,
    }
    if (!editingId.value) {
      await axios.post('/api/home/posts', payload)
    } else {
      await axios.put(`/api/home/posts/${editingId.value}`, payload)
    }
    resetForm()
    author.value = usedAuthor.trim()
    page.value = 1
    await loadPosts()
  } catch (e) {
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
    } else if (e.response && e.response.status === 404) {
      alert('当前后端未启用首页公告接口（/api/home/posts），请检查服务端是否已更新并重启。')
    } else {
      alert((e.response && e.response.data && e.response.data.detail) || '发布失败')
    }
  }
}

const onEditPost = async (p) => {
  editingId.value = p.id
  title.value = p.title || ''
  content.value = p.content
  author.value = p.author || ''
  postDepartmentId.value = p.departmentId || ''
  attachments.value = (p.attachments || []).map(a => ({ ...a }))
  await nextTick()
  if (publishCardRef.value && typeof publishCardRef.value.getBoundingClientRect === 'function') {
    const el = getScrollEl()
    const rect = publishCardRef.value.getBoundingClientRect()
    const containerRect = el === window ? { top: 0 } : el.getBoundingClientRect()
    const current = el === window ? (window.scrollY || window.pageYOffset || 0) : el.scrollTop
    const offset = rect.top - containerRect.top - 8
    const target = current + offset
    scrollTo(target)
  } else {
    scrollToTop()
  }
}

const onCancelEdit = () => {
  resetForm()
}

const onDeletePost = async (p) => {
  if (!confirm('确定要删除这条动态吗？删除后不可恢复。')) return
  try {
    await axios.delete(`/api/home/posts/${p.id}`)
    await loadPosts()
    if (!posts.value.length && page.value > 1) {
      page.value -= 1
      await loadPosts()
    }
  } catch (e) {
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
      return
    }
    alert((e.response && e.response.data && e.response.data.detail) || '删除失败')
  }
}

const busyTask = ref({ active: false, text: '', percent: 0 })
let busyTaskTimer = null
const busyTaskMeta = ref({ startTime: 0, totalBytes: 0, basePercent: 0, maxPercent: 99 })

const startEstimatedBusyTask = (text, basePercent, maxPercent, totalBytes) => {
  busyTask.value = { active: true, text, percent: basePercent }
  busyTaskMeta.value = { startTime: Date.now(), totalBytes: totalBytes || 0, basePercent, maxPercent }
  if (busyTaskTimer) {
    clearInterval(busyTaskTimer)
    busyTaskTimer = null
  }
  const SPEED = 50 * 1024 * 1024
  busyTaskTimer = setInterval(() => {
    if (!busyTask.value.active) return
    const meta = busyTaskMeta.value
    if (!meta.totalBytes || meta.totalBytes <= 0) {
      if (busyTask.value.percent < meta.maxPercent) {
        busyTask.value.percent = Math.min(meta.maxPercent, busyTask.value.percent + 1)
      }
      return
    }
    const elapsed = (Date.now() - meta.startTime) / 1000
    const estimatedDoneBytes = elapsed * SPEED
    const ratio = Math.min(1, estimatedDoneBytes / meta.totalBytes)
    const span = meta.maxPercent - meta.basePercent
    const est = meta.basePercent + Math.round(span * ratio)
    if (est > busyTask.value.percent && busyTask.value.percent < meta.maxPercent) {
 
      busyTask.value.percent = Math.min(meta.maxPercent, est)
    }
  }, 1000)
}

const finishBusyTask = (text, finalPercent = 100, delay = 200) => {
  busyTask.value.text = text
  busyTask.value.percent = finalPercent
  if (busyTaskTimer) {
    clearInterval(busyTaskTimer)
    busyTaskTimer = null
  }
  setTimeout(() => {
    busyTask.value = { active: false, text: '', percent: 0 }
    busyTaskMeta.value = { startTime: 0, totalBytes: 0, basePercent: 0, maxPercent: 99 }
  }, delay)
}

const downloadAllAttachments = async (p) => {
  if (!p.attachments || !p.attachments.length) return
  const totalSize = p.attachments.reduce((sum, a) => sum + (Number(a.size) || 0), 0)
  startEstimatedBusyTask(`正在打包 ${p.attachments.length} 个附件，请稍候…`, 5, 99, totalSize)
  try {
    const payload = {
      title: p.title || '附件',
      items: p.attachments.map((a) => ({
        spaceType: a.spaceType,
        departmentId: a.spaceType === 'department' ? a.departmentId : null,
        path: a.path || '.',
        name: a.name,
      })),
    }
    const { data } = await axios.post('/api/files/pack-async', payload)
    const jobId = data.jobId
    let pollCount = 0
    while (true) {
      await new Promise((r) => setTimeout(r, 1000))
      const res = await axios.get('/api/files/pack-status', { params: { jobId } })
      const job = res.data
      if (job.status === 'ready' && job.result) {
        finishBusyTask('打包完成，正在开始下载…', 100, 400)
        const d = job.result
        if (d && typeof d.missingCount === 'number' && d.missingCount > 0) {
          alert(`注意：有 ${d.missingCount} 个附件已不存在或被移动，本次仅下载当前仍然存在的附件。`)
        }
        const params = new URLSearchParams()
        params.append('spaceType', d.spaceType)
        if (d.departmentId) {
          params.append('departmentId', d.departmentId)
        }
        params.append('path', d.path || '.')
        params.append('name', d.name)
        const url = `/api/files/download?${params.toString()}`
        window.open(url, '_blank')
        break
      }
      if (job.status === 'failed') {
        finishBusyTask('打包下载失败', 100, 500)
        throw new Error(job.error || '打包失败')
      }
      pollCount++
      if (pollCount > 300) {
        finishBusyTask('打包超时', 100, 500)
        throw new Error('打包超时')
      }
    }
  } catch (e) {
    finishBusyTask('打包下载失败', 100, 500)
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
      return
    }
    const detail = (e.response && e.response.data && e.response.data.detail) || e.message || String(e)
    if (detail && (detail.includes('超过') || detail.includes('大小限制') || detail.includes('1G') || detail.includes('1GB'))) {
      alert(detail)
    } else if (detail === '未找到可打包的文件，请检查附件是否已被移动或删除') {
      alert('所有附件均不存在或已被移动，无法打包下载。')
    } else {
      alert(detail || '打包下载失败')
    }
  }
}

const openAttachment = async (a) => {
  if (a.is_dir) return
  const lower = (a.name || '').toLowerCase()
  const previewable = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.pdf']
  const ext = previewable.find(e => lower.endsWith(e))
  if (!ext) return

  const params = new URLSearchParams()
  params.append('spaceType', a.spaceType)
  if (a.spaceType === 'department' && a.departmentId) {
    params.append('departmentId', a.departmentId)
  }
  const normalizedPath = !a.path ? '.' : a.path
  params.append('path', normalizedPath)
  params.append('name', a.name)
  params.append('disposition', 'inline')
  const url = `/api/files/download?${params.toString()}`

  try {
    await axios.head(url)
    window.open(url, '_blank')
  } catch (e) {
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
      return
    }
    const msg = (e.response && e.response.status === 404)
      ? '该附件对应的文件已被移动或删除，请联系发布者确认最新位置。'
      : '无法打开该附件，文件可能已被移动或删除。'
    alert(msg)
  }
}

const goto = async (p) => {
  page.value = p
  await loadPosts()
  await nextTick()
  scrollToListTop()
}

// 右侧 Tips 轮播
const tips = ref([
  '文件预览：双击文件夹进入下级目录，双击文件可预览或在新标签打开（支持图片和 PDF 等常见格式）。',
  '空间选择：公共空间放院内统一资料，部门空间放科室内部文件，个人保险库存放与自己相关的敏感或工作资料。',
  '安全删除：在文件页删除只是移入回收站，如有误删可以到左侧“回收站”里还原，彻底删除后才真的清掉文件。',
  '打包下载：勾选多个文件或文件夹后点击“打包下载”，系统会自动打成一个 ZIP，省去一个个点的麻烦。',
  '搜索定位：在文件浏览中按名称搜索当前目录及子目录，给文件起个“好名字”，以后会更容易被找到。',
  '动态附件：发布首页动态时可附带最多 5 个文件或 1 个文件夹，同事点进来就能一键打包下载相关资料。',
  '保险库使用：个人保险库只有自己能看到，适合先存草稿或暂时不想公开的内容，用完记得整理归档。',
  '问题反馈：遇到打不开的附件或操作不清楚的地方，可以随手用右侧“留言 / 反馈”告诉管理员，一般会很快处理。',
])

const currentTipIndex = ref(0)
let tipTimer = null

// 日历展示
const todayStr = computed(() => {
  const d = new Date()
  return d.toLocaleDateString('zh-CN')
})
const weekDayStr = computed(() => {
  const w = new Date().getDay()
  return ['日', '一', '二', '三', '四', '五', '六'][w]
})

// 留言反馈
const feedbackText = ref('')
const feedbackCount = ref(0)
const submittingFeedback = ref(false)

const loadFeedbackCount = async () => {
  try {
    const { data } = await axios.get('/api/feedbacks/count')
    feedbackCount.value = data.count || 0
  } catch {
    feedbackCount.value = 0
  }
}

const submitFeedback = async () => {
  const text = feedbackText.value.trim()
  if (!text) return
  submittingFeedback.value = true
  try {
    await axios.post('/api/feedbacks', { content: text })
    feedbackText.value = ''
    await loadFeedbackCount()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '提交反馈失败')
  } finally {
    submittingFeedback.value = false
  }
}

const findDeptName = (id) => {
  const d = departments.value.find(x => x.id === id)
  return d ? d.name : id
}

// 为附件列表提供简单的图标逻辑，与文件浏览保持一致风格
const getFileIcon = (itemOrName, isDir) => {
  const is_dir = typeof itemOrName === 'object' ? !!itemOrName.is_dir : !!isDir
  const name = typeof itemOrName === 'object' ? (itemOrName.name || '') : (itemOrName || '')
  if (is_dir) return '📁'
  const lower = name.toLowerCase()
  if (lower.endsWith('.zip')) return '📦'
  if (lower.endsWith('.pdf')) return '📄'
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp') || lower.endsWith('.bmp')) return '🖼️'
  return '📃'
}

const listTopRef = ref(null)
const showBackTop = ref(false)

const getScrollEl = () => {
  return document.querySelector('.app-main') || window
}

// 统一滚动实现：目标 0.5s 左右滚完（基于距离动态调整速度）
const scrollTo = (targetTop) => {
  const el = getScrollEl()
  const start = el === window ? (window.scrollY || window.pageYOffset || 0) : el.scrollTop
  const distance = targetTop - start
  const duration = 500 // 0.5s
  if (duration <= 0 || distance === 0) {
    if (el === window) {
      window.scrollTo(0, targetTop)
    } else {
      el.scrollTop = targetTop
    }
    return
  }
  const startTime = performance.now()
  const easeInOut = (t) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t)

  const step = (now) => {
    const elapsed = now - startTime
    const t = Math.min(1, elapsed / duration)
    const eased = easeInOut(t)
    const current = start + distance * eased
    if (el === window) {
      window.scrollTo(0, current)
    } else {
      el.scrollTop = current
    }
    if (t < 1) requestAnimationFrame(step)
  }

  requestAnimationFrame(step)
}

const handleScroll = () => {
  const el = getScrollEl()
  const y = el === window ? (window.scrollY || window.pageYOffset || 0) : el.scrollTop
  showBackTop.value = y > 120
}

const scrollToTop = () => {
  scrollTo(0)
}

const scrollToListTop = () => {
  const el = getScrollEl()
  if (!el) return
  if (listTopRef.value && typeof listTopRef.value.getBoundingClientRect === 'function') {
    const rect = listTopRef.value.getBoundingClientRect()
    const containerRect = el === window ? { top: 0 } : el.getBoundingClientRect()
    const offset = rect.top - containerRect.top - 8
    const current = el === window ? (window.scrollY || window.pageYOffset || 0) : el.scrollTop
    const target = current + offset
    scrollTo(target)
  } else {
    scrollToTop()
  }
}

onMounted(async () => {
  loadCurrentUser()
  if (currentUser.value && currentUser.value.name) {
    author.value = currentUser.value.name
  }
  if (window && window.__hbcloud_refresh_user__) {
    window.__hbcloud_refresh_user__()
  }
  await loadDepartments()
  await loadPosts()
  await loadFeedbackCount()
  tipTimer = window.setInterval(() => {
    if (!tips.value.length) return
    currentTipIndex.value = (currentTipIndex.value + 1) % tips.value.length
  }, 8000) // 轮播间隔改为 8 秒
  const el = getScrollEl()
  el.addEventListener('scroll', handleScroll, { passive: true })
})

onUnmounted(() => {
  if (tipTimer) window.clearInterval(tipTimer)
  if (busyTaskTimer) window.clearInterval(busyTaskTimer)
  const el = getScrollEl()
  el.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.home-layout {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 24px;
  padding: 16px 24px;
}

.home-center {
  flex: 0 0 720px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.home-right {
  flex: 0 0 260px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.card {
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  padding: 12px 16px;
}

.card-elevated {
  box-shadow: 0 1px 6px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.card-elevated:hover {
  box-shadow: 0 3px 10px rgba(15, 23, 42, 0.1);
}

.publish-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.avatar-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #e5f0ff;
}

.publish-title {
  font-size: 20px;
  font-weight: 600;
}

.publish-sub {
  font-size: 12px;
  color: #6b7280;
}

.publish-body {
  margin-top: 4px;
}

.row {
  margin-bottom: 10px;
}

.row-inline {
  display: flex;
  gap: 12px;
}

.field {
  flex: 1 1 0;
}

.field-label {
  font-size: 13px;
  font-weight: 800;
  margin-bottom: 4px;
}

.field-label-muted {
  font-size: 13px;
  color: #6b7280;
}

.input,
.select-basic {
  width: 95%;
  border-radius: 4px;
  border: 1px solid #b7b9bb;
  padding: 6px 8px;
  font-size: 14px;
  font-family: inherit;
}

.textarea,
.content-input {
  width: 94.5%;
  border-radius: 4px;
  border: 1px solid #b7b9bb;
  padding: 8px 10px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.5;
  resize: vertical;
  min-height: 100px; /* 设置最小高度为100像素 */
  max-height: 300px;
}

.input::placeholder,
.textarea::placeholder,
.content-input::placeholder {
  font-size: 13px;
  font-family: inherit;
  color: #9ca3af;
}

.title-input {
  width: 95%;
  font-size: 14px;
}

.attachments-row .hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 8px;
}

.attach-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  background-color: #f9fafb;
  font-size: 12px;
}

.chip-close {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
}

.publish-footer {
  display: flex;
  justify-content: flex-start;
  gap: 8px;
  margin-top: 8px;
}

.btn {
  border-radius: 4px;
  padding: 6px 14px;
  font-size: 13px;
  border: 1px solid #d1d5db;
  background-color: #f9fafb;
  cursor: pointer;
}

.btn-primary {
  background-color: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: default;
}

.btn-ghost {
  background-color: transparent;
  border-color: #d1d5db;
  color: #374151;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.list-title {
  font-size: 20px;
  font-weight: 600;
}

.list-filter {
  display: flex;
  align-items: center;
  gap: 6px;
}

.posts {
  /* 不使用 flex + gap，而是普通块布局 + margin-bottom，让每个卡片有清晰的起始/结束位置 */
  display: block;
  margin-top: 4px;
}

/* 每个卡片用 margin-bottom 形成间距，方便 move 动画 */
.posts > .post-card {
  margin-bottom: 10px;
  /* 保留 hover 动画 0.15s */
  transition: box-shadow 0.15s ease, transform 0.15s ease, opacity 0.15s ease;
}

/* 新增/删除卡片时的淡入淡出 + 轻微上下浮动（0.3s） */
.post-fade-enter-active,
.post-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.post-fade-enter-from,
.post-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

/* 关键：列表中位置变化的卡片（例如删除中间一条后，下面的卡片前移）会自动套用 move-class，这里统一 0.3s transform 动画，效果与新增时“其他卡片下移”一致 */
.post-fade-move {
  transition: transform 0.3s ease;
}

/* 为动态卡片、右侧卡片统一阴影与动效 */
.post-card {
  padding: 20px 20px 12px;
  border-radius: 10px;
  border: 1px solid #c8c4be;
  background-color: #fff;
  box-shadow: 0 1px 6px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.post-card:hover {
  box-shadow: 0 3px 10px rgba(15, 23, 42, 0.1);
  transform: translateY(-1px);
}

.post-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.post-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: #e5f0ff;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.post-title {
  font-size: 14px;
  font-weight: 600;
}

.post-meta {
  font-size: 12px;
  color: #6b7280;
}

.post-content {
  margin-top: 6px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.post-attachments {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #e5e7eb;
}

.post-attachments-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.attach-title {
  font-size: 13px;
  color: #4b5563;
}

.post-attach-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.attach-item-btn {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  background-color: #f9fafb;
  font-size: 12px;
  cursor: pointer;
}

.attach-item-btn:hover {
  border-color: #2563eb66;
  background-color: #eff6ff;
}

.attach-name {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.post-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.post-footer-left {
  display: flex;
  align-items: center;
}

.post-actions {
  display: flex;
  gap: 8px;
}

/* 复用发布表单的按钮基础样式，保持大小一致 */
.btn-danger {
  border-color: #fca5a5;
  color: #b91c1c;
  background-color: #fef2f2;
}

.btn-danger:hover:enabled {
  background-color: #fee2e2;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 13px;
}

.btn[disabled],
.btn:disabled,
.btn-danger[disabled],
.btn-danger:disabled,
.btn-sm[disabled],
.btn-sm:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  filter: grayscale(0.3);
}

/* tips 渐隐渐显动画保留 */
.fade-tip-enter-active,
.fade-tip-leave-active {
  transition: opacity 0.35s ease;
}

.fade-tip-enter-from,
.fade-tip-leave-to {
  opacity: 0;
}

.right-card {
  background-color: #ffffff;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  padding: 0.6rem 0.8rem;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
}

.right-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 0.4rem;
}

.tips-card .tip-text {
  font-size: 0.85rem;
  color: #4b5563;
  min-height: 5em;
}

.calendar-placeholder {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 0.5rem;
  border-radius: 4px;
  background-color: #f3f4f6;
  font-size: 0.9rem;
}

.calendar-date {
  font-weight: 600;
}

.calendar-week {
  color: #6b7280;
}

.feedback-textarea {
  width: 100%;
  border-radius: 4px;
  border: 2px solid #d1d5db;
  padding: 0.35rem 0.45rem;
  font-size: 0.85rem;
  resize: none;
  box-sizing: border-box;
}

.feedback-btn {
  margin-top: 0.4rem;
  width: 100%;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #2563eb;
  color: #f9fafb;
  font-size: 0.85rem;
  cursor: pointer;
}

.feedback-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.feedback-meta {
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: #6b7280;
}

/* 遮罩层与对话框样式（恢复为弹窗效果） */
.mask {
  position: fixed;
  inset: 0;
  background-color: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  width: 760px;
  max-height: 80vh;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
  padding: 12px 16px 10px;
  display: flex;
  flex-direction: column;
}

.picker-pathbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.picker-list {
  flex: 1 1 auto;
  margin-top: 4px;
  margin-bottom: 6px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  overflow: auto;
}

.picker-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

.btn.btn-icon {
  padding: 4px 8px;
}

.pagination {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.picker-header-row {
  display: flex;
  gap: 12px;
}

.picker-field {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
}

.picker-list table {
  width: 100%;
  border-collapse: collapse;
}

.picker-list th,
.picker-list td {
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.9rem;
}

/* 文件名称列最小宽度 300px */
.picker-list th:nth-child(2),
.picker-list td:nth-child(2) {
  min-width: 150px;
}

/* 在末尾添加首页动态打包任务遮罩样式 */
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
  transition: width 0.2s ease;
}
.task-progress-text {
  margin-top: 4px;
  font-size: 12px;
  color: #374151;
  text-align: right;
}

/* 选择附件弹窗淡入淡出 */
.fade-dialog-enter-active,
.fade-dialog-leave-active {
  transition: opacity 0.15s ease;
}

.fade-dialog-enter-from,
.fade-dialog-leave-to {
  opacity: 0;
}

/* 任务遮罩淡入淡出 */
.fade-task-enter-active,
.fade-task-leave-active {
  transition: opacity 0.15s ease;
}

.fade-task-enter-from,
.fade-task-leave-to {
  opacity: 0;
}

/* 回到顶部按钮 */
.back-top-btn {
  position: fixed;
  right: 26px;
  bottom: 26px;
  z-index: 1100;
  padding: 0.4rem 0.7rem;
  border-radius: 999px;
  border: 1px solid #9ca3af;
  background-color: #ffffff;
  color: #111827;
  font-size: 0.85rem;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.18);
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.back-top-btn:hover {
  background-color: #2563eb;
  border-color: #2563eb;
  color: #f9fafb;
  transform: translateY(-1px);
}

.fade-back-top-enter-active,
.fade-back-top-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-back-top-enter-from,
.fade-back-top-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

/* 附件选择弹窗：名称列按钮化，避免文本选中 */
.picker-name-btn {
  width: 100%;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  text-align: left;
  user-select: none;
}

.picker-name-btn:hover {
  background-color: #f3f4f6;
  border-color: #e5e7eb;
}

.picker-name-btn:active {
  background-color: #e5e7eb;
}

.picker-name-btn.dir {
  font-weight: 600;
}

.picker-name-icon {
  flex: 0 0 auto;
}

.picker-name-text {
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.picker-enter-hint {
  flex: 0 0 auto;
  font-size: 12px;
  color: #6b7280;
  border: 1px solid #e5e7eb;
  background-color: #ffffff;
  border-radius: 999px;
  padding: 1px 8px;
}
</style>
