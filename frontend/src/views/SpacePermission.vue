<template>
  <div class="space-permission" :class="{ 'sp-mobile': isMobileShell }">
    <div v-if="isMobileShell" class="sp-mobile-top">
      <div class="sp-mobile-title">空间权限</div>
      <div class="sp-mobile-select-row">
        <select class="sp-mobile-select" v-model="mobileDeptId" @change="onMobileDeptChange">
          <option value="__public__">公共空间</option>
          <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name || d.id }}</option>
        </select>
      </div>
    </div>

    <div v-if="!isMobileShell" class="sp-left">
      <div class="sp-left-header">
        <h2>部门列表</h2>
        <div class="sp-left-tip">从左侧选择一个部门，右侧将展示其配置。</div>
      </div>
      <div class="sp-dept-list">
        <!-- 新增：固定的“公共空间”项，作为列表首项 -->
        <div
          :class="['sp-dept-item', { active: currentDeptId === '__public__' }]"
          @click="selectDept('__public__', true)"
        >
          <div class="name">公共空间</div>
          <div class="id">ID：public</div>
        </div>
        <div
          v-for="d in departments"
          :key="d.id"
          :class="['sp-dept-item', { active: d.id === currentDeptId }]"
          @click="selectDept(d.id, false)"
        >
          <div class="name">{{ d.name }}</div>
          <div class="id">ID：{{ d.id }}</div>
        </div>
      </div>
      <div v-if="!departments.length" class="sp-empty">当前尚未创建任何部门（仍可查看公共空间）。</div>
    </div>
    <div class="sp-right">
      <transition name="sp-switch" mode="out-in" @before-leave="onBeforeRightSwitch" @after-enter="onAfterRightSwitch">
        <div :key="currentDeptId || '__none__'" class="sp-right-inner">
          <div class="sp-detail">
            <div class="sp-right-header">
              <h2>空间详情</h2>
              <div class="sp-right-actions" v-if="canEditCurrent">
                <!-- 根据 hasPendingEdit 控制按钮禁用状态 -->
                <button type="button" class="sp-btn" :disabled="!hasPendingEdit" @click.prevent="onSaveEdit">保存编辑</button>
                <button type="button" class="sp-btn" :disabled="!hasPendingEdit" @click.prevent="onCancelEdit">取消编辑</button>
              </div>
            </div>
            <div class="sp-right-tip">
              空间的基础属性与配置信息概览。
            </div>
            <div v-if="!canEditCurrent && currentDeptId && currentDeptId !== '__public__'" class="sp-noedit-tip">
              当前账号无权编辑该部门的空间权限配置（仅可查看）。
              <span v-if="rolesLoaded">（可编辑条件：为该部门的部门管理员或系统管理员）</span>
            </div>
            <!-- 公共空间：直接展示固定属性，不依赖 config -->
            <div v-if="currentDeptId === '__public__'" class="sp-config">
              <div class="sp-config-block">
                <div class="sp-config-header">
                  <span class="caret">▼</span>
                  <span class="title">基础信息</span>
                </div>
                <div class="sp-config-body">
                  <div class="sp-config-row">
                    <div class="k">空间名称</div>
                    <div class="v">公共空间</div>
                  </div>
                  <div class="sp-config-row">
                    <div class="k">空间 ID</div>
                    <div class="v">public</div>
                  </div>
                  <div class="sp-config-row">
                    <div class="k">空间类型</div>
                    <div class="v">全院共享空间（所有有权限用户可访问）</div>
                  </div>
                  <div class="sp-config-row">
                    <div class="k">删除策略</div>
                    <div class="v">删除文件将统一进入公共回收站，可在回收站中恢复或彻底删除</div>
                  </div>
                </div>
              </div>
              <div class="sp-config-block">
                <div class="sp-config-header">
                  <span class="caret">▼</span>
                  <span class="title">权限与使用说明</span>
                </div>
                <div class="sp-config-body">
                  <div class="sp-config-row">
                    <div class="k">适用人群</div>
                    <div class="v">院内具备登录账号的普通用户、管理员、超级管理员等</div>
                  </div>
                  <div class="sp-config-row">
                    <div class="k">典型用途</div>
                    <div class="v">全院制度规范、模板文档、公共通知附件等统一发布与共享</div>
                  </div>
                </div>
              </div>
            </div>
            <!-- 部门空间：按原逻辑从 config.json 读取 -->
            <div v-else-if="!currentDeptId" class="sp-empty">请先在左侧选择一个部门。</div>
            <div v-else-if="!deptConfig && !loading" class="sp-empty">未能读取到该部门的配置文件。</div>
            <div v-else-if="deptConfig" class="sp-config">
              <!-- 新增：空间开放开关，占位，不做实际逻辑 -->
              <div class="sp-config-block sp-toggle-block">
                <div class="sp-config-header">
                  <span class="title">空间开放设置</span>
                </div>
                <div class="sp-config-body sp-toggle-body">
                  <label class="switch-row">
                    <span class="label">是否开放该部门空间</span>
                    <button
                      type="button"
                      class="switch"
                      :title="canEditCurrent ? '' : '无权限编辑'"
                      @click="onToggleDeptOpen"
                    >
                      <span :class="['thumb', { on: deptOpen }]"></span>
                      <span class="switch-text">{{ deptOpen ? '已开放' : '未开放' }}</span>
                    </button>
                  </label>
                  <div class="hint">用于配置空间开放状态，非开放状态下的部门空间仅本部门成员可见，详见“帮助-权限”。</div>
                </div>
              </div>

              <div class="sp-config-block">
                <div class="sp-config-header" @click="toggleSection('basic')">
                  <span class="caret">{{ openSections.basic ? '▼' : '▶' }}</span>
                  <span class="title">基础信息</span>
                </div>
                <div v-if="openSections.basic" class="sp-config-body">
                  <div class="sp-config-row">
                    <div class="k">部门名称</div>
                    <div class="v">{{ deptConfig.name || currentDeptId }}</div>
                  </div>
                  <div class="sp-config-row">
                    <div class="k">部门 ID</div>
                    <div class="v">{{ deptConfig.id || currentDeptId }}</div>
                  </div>
                  <div class="sp-config-row">
                    <div class="k">是否设置删除密码</div>
                    <div class="v">{{ deptConfig.deletePasswordProtected ? '是' : '否' }}</div>
                  </div>
                </div>
              </div>

              <div class="sp-config-block">
                <div class="sp-config-header" @click="toggleSection('creator')">
                  <span class="caret">{{ openSections.creator ? '▼' : '▶' }}</span>
                  <span class="title">创建者信息</span>
                </div>
                <div v-if="openSections.creator" class="sp-config-body">
                  <div v-if="deptConfig.creator" class="sp-config-sub">
                    <div class="sp-config-row">
                      <div class="k">创建人姓名</div>
                      <div class="v">{{ deptConfig.creator.name || '—' }}</div>
                    </div>
                    <div class="sp-config-row">
                      <div class="k">创建人手机号</div>
                      <div class="v">{{ deptConfig.creator.phone || '—' }}</div>
                    </div>
                    <div class="sp-config-row">
                      <div class="k">创建人 ID</div>
                      <div class="v">{{ deptConfig.creator.id ?? '—' }}</div>
                    </div>
                  </div>
                  <div v-else class="sp-config-empty">配置中未记录创建者信息。</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 权限组配置区域（延迟出现） -->
          <transition name="sp-roles-pop">
            <div v-if="showRolesSection" class="sp-roles-section">
              <div class="sp-roles-header">
                <h3>权限组配置</h3>
                <div class="sp-roles-tip">
                  <template v-if="currentDeptId === '__public__'">
                    公共空间：member 按部门分组展示（可展开/收起），dept 固定为 super/op（仅展示）。
                  </template>
                  <template v-else>
                    为当前空间指定部门管理员与部门成员。
                    <span v-if="canEditCurrent">修改后请点击右上角“保存编辑”提交。</span>
                    <span v-else>当前账号仅可查看。</span>
                  </template>
                </div>
              </div>

              <!-- 公共空间展示：两栏（dept=super/op，member=按部门分组） -->
              <div v-if="currentDeptId === '__public__'" class="sp-roles-body sp-roles-two-cols">
                <div class="col">
                  <div class="col-title-row">
                    <div class="col-title">部门管理员（dept）</div>
                    <button v-if="isSuper" type="button" class="col-edit-btn" @click="openOpAdminModal">
                      编辑系统管理员
                    </button>
                  </div>
                  <div class="sp-table-wrap">
                    <table class="sp-table">
                      <thead>
                        <tr>
                          <th class="c-idx">序号</th>
                          <th class="c-name">姓名</th>
                          <th class="c-phone">手机号</th>
                          <th class="c-role">全局角色</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-if="!publicDeptAdminsTableRows.length">
                          <td class="empty" colspan="4">暂无</td>
                        </tr>
                        <tr v-for="(u, idx) in publicDeptAdminsTableRows" :key="u.phone">
                          <td class="c-idx">{{ idx + 1 }}</td>
                          <td class="c-name">{{ u.name }}</td>
                          <td class="c-phone">{{ u.phone }}</td>
                          <td class="c-role">{{ u.globalRoleText }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div class="col">
                  <div class="col-title-row">
                    <div class="col-title">部门成员（member）</div>
                  </div>

                  <div class="sp-public-groups member-panel">
                    <div
                      v-for="g in publicMemberGroups"
                      :key="g.key"
                      class="sp-public-group"
                    >
                      <button
                        type="button"
                        class="sp-public-group-header"
                        @click="togglePublicGroup(g.key)"
                        :aria-expanded="isPublicGroupOpen(g.key) ? 'true' : 'false'"
                      >
                        <span class="caret">{{ isPublicGroupOpen(g.key) ? '▼' : '▶' }}</span>
                        <span class="name">{{ g.title }}</span>
                        <span class="count">({{ g.users.length }})</span>
                      </button>
                      <div v-if="isPublicGroupOpen(g.key)" class="sp-table-wrap">
                        <table class="sp-table">
                          <thead>
                            <tr>
                              <th class="c-idx">序号</th>
                              <th class="c-name">姓名</th>
                              <th class="c-phone">手机号</th>
                              <th class="c-role">全局角色</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-if="!g.users.length">
                              <td class="empty" colspan="4">暂无</td>
                            </tr>
                            <tr v-for="(u, idx) in g.users" :key="u.phone">
                              <td class="c-idx">{{ idx + 1 }}</td>
                              <td class="c-name">
                                {{ u.name }}
                                <span v-if="u.isDeptAdmin" class="sp-user-tag">部门管理员</span>
                              </td>
                              <td class="c-phone">{{ u.phone }}</td>
                              <td class="c-role">{{ u.globalRoleText }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 部门空间：原有两栏编辑区 -->
              <div v-else class="sp-roles-body sp-roles-two-cols">
                <div class="col">
                  <div class="col-title-row">
                    <div class="col-title">部门管理员（dept）</div>
                    <button type="button" class="col-edit-btn" :disabled="!canEditCurrent" @click="onEditMembers('dept')">
                      编辑成员
                    </button>
                  </div>
                  <div class="sp-table-wrap">
                    <table class="sp-table">
                      <thead>
                        <tr>
                          <th class="c-idx">序号</th>
                          <th class="c-name">姓名</th>
                          <th class="c-phone">手机号</th>
                          <th class="c-role">全局角色</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-if="!deptAdminsTableRows.length">
                          <td class="empty" colspan="4">暂无部门管理员。</td>
                        </tr>
                        <tr v-for="(u, idx) in deptAdminsTableRows" :key="u.phone">
                          <td class="c-idx">{{ idx + 1 }}</td>
                          <td class="c-name">{{ u.name }}</td>
                          <td class="c-phone">{{ u.phone }}</td>
                          <td class="c-role">{{ u.globalRoleText }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                <div class="col">
                  <div class="col-title-row">
                    <div class="col-title">部门成员（member）</div>
                    <button type="button" class="col-edit-btn" :disabled="!canEditCurrent" @click="onEditMembers('member')">
                      编辑成员
                    </button>
                  </div>
                  <div class="sp-table-wrap">
                    <table class="sp-table">
                      <thead>
                        <tr>
                          <th class="c-idx">序号</th>
                          <th class="c-name">姓名</th>
                          <th class="c-phone">手机号</th>
                          <th class="c-role">全局角色</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-if="!deptMembersTableRows.length">
                          <td class="empty" colspan="4">暂无部门成员。</td>
                        </tr>
                        <tr v-for="(u, idx) in deptMembersTableRows" :key="u.phone">
                          <td class="c-idx">{{ idx + 1 }}</td>
                          <td class="c-name">{{ u.name }}</td>
                          <td class="c-phone">{{ u.phone }}</td>
                          <td class="c-role">{{ u.globalRoleText }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </transition>
    </div>

    <!-- 新增：编辑成员弹窗（多选） -->
    <transition name="sp-modal">
      <div v-if="memberModal.visible" class="sp-mask" @click="closeMemberModal">
        <div class="sp-dialog" @click.stop>
          <div class="sp-dialog-title">
            <template v-if="memberModal.type === 'op'">编辑系统管理员（op）</template>
            <template v-else>
              编辑成员（{{ memberModal.type === 'dept' ? '部门管理员' : '部门成员' }}）
            </template>
          </div>

          <div class="sp-dialog-toolbar">
            <input
              v-model="memberModal.keyword"
              type="text"
              class="sp-search"
              placeholder="搜索姓名/手机号"
            />
            <div class="sp-toolbar-actions">
              <button type="button" class="sp-mini-btn" @click="selectAllInModal">全选</button>
              <button type="button" class="sp-mini-btn" @click="clearAllInModal">全不选</button>
            </div>
          </div>

          <div class="sp-dialog-body">
            <div v-if="memberModal.loading" class="sp-dialog-hint">加载中…</div>
            <div v-else-if="!filteredCandidates.length" class="sp-dialog-hint">无匹配用户</div>
            <div v-else class="sp-user-grid">
              <label
                v-for="u in filteredCandidates"
                :key="u.phone"
                class="sp-user-row"
                :class="{ disabled: isPhoneDisabledInModal(u.phone) }"
              >
                <input
                  type="checkbox"
                  :value="u.phone"
                  v-model="memberModal.selectedPhones"
                  :disabled="isPhoneDisabledInModal(u.phone)"
                />
                <span class="sp-user-name">{{ u.name }}</span>
                <span class="sp-user-phone">{{ u.phone }}</span>
                <span v-if="isPhoneDisabledInModal(u.phone)" class="sp-user-tag">已在另一组</span>
              </label>
            </div>
          </div>

          <div class="sp-dialog-footer">
            <div class="sp-dialog-count">已选 {{ memberModal.selectedPhones.length }} 人</div>
            <div class="sp-dialog-actions">
              <button type="button" class="sp-btn" @click="confirmMemberModal">确定</button>
              <button type="button" class="sp-btn" @click="closeMemberModal">取消</button>
            </div>
          </div>

          <div class="sp-dialog-tip">
            <template v-if="memberModal.type === 'op'">
              提示：候选用户来自 users.db（全院已注册用户），支持搜索与多选；保存后将直接更新用户全局角色（user ⇄ 系统管理员），并且不会修改超级管理员。
            </template>
            <template v-else>
              提示：候选用户来自 users.db（全院已注册用户），支持搜索与多选；修改后请点击页面右上角“保存编辑”提交。
            </template>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  listDepartments,
  getDepartmentConfig,
  updateDepartmentConfig,
  getDepartmentRoles,
  updateDepartmentRoles,
  listUsers,
  setOpUsers,
} from '../services/recycle'

const route = useRoute()
const isMobileShell = computed(() => (route.path || '').startsWith('/m'))

const departments = ref([])
const currentDeptId = ref('')

// 移动端下拉：默认公共空间，切换时复用 selectDept 的确认逻辑
const mobileDeptId = ref('__public__')

const onMobileDeptChange = async () => {
  const target = mobileDeptId.value || '__public__'
  await selectDept(target, target === '__public__')
  // 若用户取消了切换（有未保存修改），这里把下拉值恢复为当前 deptId
  mobileDeptId.value = currentDeptId.value || '__public__'
}

watch(currentDeptId, (v) => {
  mobileDeptId.value = v || '__public__'
}, { immediate: true })
const deptConfig = ref(null)
const loading = ref(false)

// 用于控制各个信息块的展开/收起状态：基础信息默认展开，创建者信息默认收起
const openSections = ref({
  basic: true,
  creator: false,
})

const toggleSection = (key) => {
  openSections.value[key] = !openSections.value[key]
}

// 空间开放开关：从后端 config.isOpen 初始化
const deptOpen = ref(true)
const originalDeptOpen = ref(true)

// 角色列表：使用真实数据
const deptAdmins = ref([]) // [{ name, phone }]
const deptMembers = ref([])

// 角色原始快照，用于取消编辑还原
const originalDeptAdmins = ref([])
const originalDeptMembers = ref([])

const hasPendingEdit = ref(false)

const isSamePhoneList = (a, b) => {
  const aa = (a || []).map((u) => u.phone).filter(Boolean)
  const bb = (b || []).map((u) => u.phone).filter(Boolean)
  if (aa.length !== bb.length) return false
  // 无序比较：按字符串排序后对比
  aa.sort()
  bb.sort()
  return aa.every((p, idx) => p === bb[idx])
}

const recomputePendingState = () => {
  if (!currentDeptId.value || currentDeptId.value === '__public__') {
    hasPendingEdit.value = false
    return
  }
  const openChanged = deptOpen.value !== originalDeptOpen.value
  const adminsChanged = !isSamePhoneList(deptAdmins.value, originalDeptAdmins.value)
  const membersChanged = !isSamePhoneList(deptMembers.value, originalDeptMembers.value)
  hasPendingEdit.value = openChanged || adminsChanged || membersChanged
}

const onToggleDeptOpen = () => {
  if (!currentDeptId.value || currentDeptId.value === '__public__') return
  if (!canEditCurrent.value) {
    // 不灰显，但禁止实际修改
    window.alert('无权限编辑该部门空间开放状态')
    return
  }
  deptOpen.value = !deptOpen.value
  recomputePendingState()
}

const prettyConfig = computed(() => {
  if (!deptConfig.value) return ''
  return JSON.stringify(deptConfig.value, null, 2)
})

const loadDepartments = async () => {
  try {
    const list = await listDepartments()
    departments.value = list
    // 默认选中公共空间
    if (!currentDeptId.value) {
      currentDeptId.value = '__public__'
      deptConfig.value = null
      hasPendingEdit.value = false
    }
  } catch (e) {
    console.error('loadDepartments failed', e)
    departments.value = []
  }
}

const rolesLoaded = ref(false)

const loadDeptRoles = async (deptId) => {
  if (!deptId || deptId === '__public__') {
    deptAdmins.value = []
    deptMembers.value = []
    originalDeptAdmins.value = []
    originalDeptMembers.value = []
    currentDeptRole.value = null
    rolesLoaded.value = false
    recomputePendingState()
    return
  }
  try {
    const roles = await getDepartmentRoles(deptId)
    deptAdmins.value = roles.dept || []
    deptMembers.value = roles.member || []
    // 记录原始快照
    originalDeptAdmins.value = (roles.dept || []).map((u) => ({ ...u }))
    originalDeptMembers.value = (roles.member || []).map((u) => ({ ...u }))

    // 基于“后端返回的角色列表快照”计算当前用户在该部门的角色
    currentDeptRole.value = computeCurrentDeptRole(originalDeptAdmins.value)
    rolesLoaded.value = true

    recomputePendingState()
  } catch (e) {
    console.error('getDepartmentRoles failed', e)
    deptAdmins.value = []
    deptMembers.value = []
    originalDeptAdmins.value = []
    originalDeptMembers.value = []
    currentDeptRole.value = null
    rolesLoaded.value = true
    recomputePendingState()
  }
}

const loadDeptConfig = async (deptId) => {
  if (!deptId || deptId === '__public__') {
    // 公共空间不读取 config
    deptConfig.value = null
    deptOpen.value = true
    originalDeptOpen.value = true
    // 清空角色
    deptAdmins.value = []
    deptMembers.value = []
    originalDeptAdmins.value = []
    originalDeptMembers.value = []
    recomputePendingState()
    return
  }
  loading.value = true
  try {
    const cfg = await getDepartmentConfig(deptId)
    deptConfig.value = cfg
    const isOpen = cfg && typeof cfg.isOpen === 'boolean' ? cfg.isOpen : true
    deptOpen.value = isOpen
    originalDeptOpen.value = isOpen
    // 加载角色列表及快照
    await loadDeptRoles(deptId)
    recomputePendingState()
  } catch (e) {
    console.error('getDepartmentConfig failed', e)
    deptConfig.value = null
    deptOpen.value = true
    originalDeptOpen.value = true
    deptAdmins.value = []
    deptMembers.value = []
    originalDeptAdmins.value = []
    originalDeptMembers.value = []
    recomputePendingState()
  } finally {
    loading.value = false
  }
}

const selectDept = async (deptId, isPublic = false) => {
  if (deptId === currentDeptId.value) return
  // 若当前存在未保存修改，提示确认
  if (hasPendingEdit.value) {
    const ok = window.confirm('当前空间配置有未保存的修改，切换部门将丢弃这些更改，是否继续？')
    if (!ok) return
  }
  currentDeptId.value = deptId
  if (isPublic) {
    deptConfig.value = null
    deptOpen.value = true
    originalDeptOpen.value = true
    deptAdmins.value = []
    deptMembers.value = []
    originalDeptAdmins.value = []
    originalDeptMembers.value = []
    recomputePendingState()
  } else {
    await loadDeptConfig(deptId)
  }
}

const markPendingByRoles = () => {
  // 编辑成员后重新计算是否有未保存变更
  recomputePendingState()
}

// ===========
// 编辑成员弹窗（多选）
// ===========
const memberModal = ref({
  visible: false,
  type: 'dept', // 'dept' | 'member' | 'op'
  keyword: '',
  loading: false,
  candidates: [], // [{phone,name}]
  selectedPhones: [], // string[]
})

const normalizePhone = (p) => (p || '').toString().trim()
const uniqByPhone = (list) => {
  const m = new Map()
  ;(list || []).forEach((u) => {
    const phone = normalizePhone(u && u.phone)
    if (!phone) return
    m.set(phone, { phone, name: (u && u.name) || phone })
  })
  return Array.from(m.values())
}

const getLocalLoginUserAsCandidate = () => {
  const raw = localStorage.getItem('hbcloud_user')
  if (!raw) return null
  try {
    const u = JSON.parse(raw)
    if (!u || !u.phone) return null
    return { phone: normalizePhone(u.phone), name: u.name || normalizePhone(u.phone) }
  } catch {
    return null
  }
}

// 全量用户缓存（来自 users.db），用于弹窗候选列表
const allUsersCache = ref(null) // null | Array<{phone,name}>

const ensureAllUsersLoaded = async () => {
  if (allUsersCache.value && Array.isArray(allUsersCache.value)) return allUsersCache.value
  const all = await listUsers()
  allUsersCache.value = (all || []).map((u) => ({ phone: u.phone, name: u.name || u.phone }))
  return allUsersCache.value
}

const buildCandidatesForModal = async (deptId) => {
  const candidates = []

  // 强制优先：全院注册用户（users.db）
  try {
    const all = await ensureAllUsersLoaded()
    candidates.push(...(all || []))
  } catch (e) {
    console.warn('ensureAllUsersLoaded failed, will fallback to local candidates', e)
  }

  // 合并：当前已加载/快照/本机登录信息（用于补齐 name 与兼容异常情况）
  candidates.push(...(deptAdmins.value || []))
  candidates.push(...(deptMembers.value || []))
  candidates.push(...(originalDeptAdmins.value || []))
  candidates.push(...(originalDeptMembers.value || []))

  const localUser = getLocalLoginUserAsCandidate()
  if (localUser) candidates.push(localUser)

  // 兜底：若部门 roles 尚未加载，尝试补拉一次
  if (deptId && deptId !== '__public__' && (!deptAdmins.value.length && !deptMembers.value.length)) {
    try {
      const roles = await getDepartmentRoles(deptId)
      candidates.push(...(roles.dept || []), ...(roles.member || []))
    } catch {
      // ignore
    }
  }

  return uniqByPhone(candidates).sort((a, b) => (a.phone || '').localeCompare(b.phone || ''))
}

const filteredCandidates = computed(() => {
  const kw = (memberModal.value.keyword || '').trim().toLowerCase()
  const list = memberModal.value.candidates || []
  if (!kw) return list
  return list.filter((u) => {
    const name = (u.name || '').toLowerCase()
    const phone = (u.phone || '').toLowerCase()
    return name.includes(kw) || phone.includes(kw)
  })
})

const disabledPhonesInModal = computed(() => {
  const t = memberModal.value.type
  if (t === 'op') return new Set()
  if (t === 'dept') {
    // 编辑 dept：禁用已在 member 的手机号
    return new Set((deptMembers.value || []).map((u) => normalizePhone(u.phone)).filter(Boolean))
  }
  if (t === 'member') {
    // 编辑 member：禁用已在 dept 的手机号
    return new Set((deptAdmins.value || []).map((u) => normalizePhone(u.phone)).filter(Boolean))
  }
  return new Set()
})

const isPhoneDisabledInModal = (phone) => {
  const p = normalizePhone(phone)
  return disabledPhonesInModal.value.has(p)
}

// 确保打开弹窗时，不会把“被禁用项”错误地留在已选列表里
const sanitizeSelectedPhonesForModal = () => {
  const dis = disabledPhonesInModal.value
  memberModal.value.selectedPhones = (memberModal.value.selectedPhones || []).filter((p) => !dis.has(normalizePhone(p)))
}

const openMemberModal = async (type) => {
  if (!currentDeptId.value) return
  if (currentDeptId.value === '__public__') return

  memberModal.value.visible = true
  memberModal.value.type = type
  memberModal.value.keyword = ''
  memberModal.value.loading = true

  // 初始化已选手机号
  const selected = (type === 'dept' ? deptAdmins.value : deptMembers.value).map((u) => normalizePhone(u.phone)).filter(Boolean)
  memberModal.value.selectedPhones = Array.from(new Set(selected))

  try {
    // 预热全量用户，确保候选是“全院可选”
    try {
      await ensureAllUsersLoaded()
    } catch {
      // ignore
    }

    memberModal.value.candidates = await buildCandidatesForModal(currentDeptId.value)

    // 应用互斥禁选规则
    sanitizeSelectedPhonesForModal()
  } finally {
    memberModal.value.loading = false
  }
}

const closeMemberModal = () => {
  memberModal.value.visible = false
  memberModal.value.keyword = ''
  memberModal.value.loading = false
  memberModal.value.candidates = []
  memberModal.value.selectedPhones = []
}

const selectAllInModal = () => {
  memberModal.value.selectedPhones = (filteredCandidates.value || []).map((u) => u.phone)
}

const clearAllInModal = () => {
  memberModal.value.selectedPhones = []
}

const confirmMemberModal = async () => {
  const t = memberModal.value.type

  // op 模式：提交系统管理员名单
  if (t === 'op') {
    try {
      const dis = disabledPhonesInModal.value
      const phones = (memberModal.value.selectedPhones || [])
        .map(normalizePhone)
        .filter((p) => p && !dis.has(p))

      // 更新 users.db（op<->user），后端会忽略 super
      const updatedUsers = await setOpUsers(phones)
      allUsersForPublic.value = updatedUsers || []

      // 立即生效：刷新当前登录用户信息，更新本地缓存
      try {
        const { data } = await (await import('axios')).default.get('/api/auth/me')
        if (data && data.phone) {
          localStorage.setItem('hbcloud_user', JSON.stringify(data))
          currentUser.value = data
        }
      } catch {
        // ignore
      }

      closeMemberModal()
      alert('已更新系统管理员')
    } catch (e) {
      console.error('setOpUsers failed', e)
      alert('更新失败，请稍后重试')
    }
    return
  }

  // 过滤掉被禁用项，避免边界情况下写入冲突数据
  const dis = disabledPhonesInModal.value
  const phones = (memberModal.value.selectedPhones || [])
    .map(normalizePhone)
    .filter((p) => p && !dis.has(p))

  const phoneSet = new Set(phones)
  const byPhone = new Map((memberModal.value.candidates || []).map((u) => [normalizePhone(u.phone), u]))
  const mapped = Array.from(phoneSet).map((p) => {
    const u = byPhone.get(p)
    return { phone: p, name: (u && u.name) || p }
  })

  if (memberModal.value.type === 'dept') {
    deptAdmins.value = mapped
  } else {
    deptMembers.value = mapped
  }

  markPendingByRoles()
  closeMemberModal()
}

// 覆盖原先 prompt 入口
const onEditMembers = (type) => {
  if (!canEditCurrent.value) return
  openMemberModal(type)
}

const onSaveEdit = async () => {
  if (!hasPendingEdit.value) return
  if (!currentDeptId.value || currentDeptId.value === '__public__') return
  try {
    // 1) 提交 isOpen
    const cfgPayload = { isOpen: !!deptOpen.value }
    const updatedCfg = await updateDepartmentConfig(currentDeptId.value, cfgPayload)
    const isOpen = updatedCfg && typeof updatedCfg.isOpen === 'boolean' ? updatedCfg.isOpen : !!deptOpen.value
    deptOpen.value = isOpen
    originalDeptOpen.value = isOpen

    // 2) 提交角色列表（手机号数组）
    const admins = (deptAdmins.value || []).map((u) => u.phone)
    const members = (deptMembers.value || []).map((u) => u.phone)
    const updatedRoles = await updateDepartmentRoles(currentDeptId.value, { admins, members })
    // 更新原始快照为后端返回结果
    originalDeptAdmins.value = (updatedRoles.dept || []).map((u) => ({ ...u }))
    originalDeptMembers.value = (updatedRoles.member || []).map((u) => ({ ...u }))

    recomputePendingState()
    alert('已保存')
  } catch (e) {
    console.error('save space config failed', e)
    alert('保存失败，请稍后重试')
  }
}

const onCancelEdit = () => {
  if (!hasPendingEdit.value) return
  // 还原到最近一次从后端加载/保存的状态
  deptOpen.value = originalDeptOpen.value
  deptAdmins.value = originalDeptAdmins.value.map((u) => ({ ...u }))
  deptMembers.value = originalDeptMembers.value.map((u) => ({ ...u }))
  recomputePendingState()
}

const currentUser = ref(null) // { phone, role, name }

const loadCurrentUserFromLocal = () => {
  const raw = localStorage.getItem('hbcloud_user')
  if (!raw) return null
  try {
    const u = JSON.parse(raw)
    if (!u) return null
    return {
      phone: (u.phone || '').toString().trim(),
      role: u.role || 'user',
      name: u.name || '',
    }
  } catch {
    return null
  }
}

// 当前用户在当前部门的角色（用于前端编辑态判断）
const currentDeptRole = ref(null) // 'dept' | 'member' | null

const computeCurrentDeptRole = (deptAdminsList) => {
  const u = currentUser.value
  if (!u) return null
  const myPhone = normalizePhone(u.phone)
  if (!myPhone) return null
  // dept 角色来自后端 dept_roles；前端这里用“当前部门 roles.dept 列表”判断
  const isDept = (deptAdminsList || []).some((x) => normalizePhone(x.phone) === myPhone)
  return isDept ? 'dept' : null
}

// 重新定义可编辑判断：
// - super/op：按本地登录信息的 role 判断（用于 UI 友好控制）；
// - 只要后端 roles.dept 返回包含自己手机号：即可编辑（不依赖本地 role，也不依赖 users 表 role 字段）。
const canEditCurrent = computed(() => {
  if (!currentDeptId.value || currentDeptId.value === '__public__') return false

  const u = currentUser.value
  const myPhone = u ? normalizePhone(u.phone) : ''

  // super/op：直接放开
  if (u && (u.role === 'super' || u.role === 'op')) return true

  // roles 未加载完成前，不放开编辑，避免误判
  if (!rolesLoaded.value) return false

  // 本部门 dept：admin 列包含自己即可
  if (myPhone && (originalDeptAdmins.value || []).some((x) => normalizePhone(x.phone) === myPhone)) {
    return true
  }

  return false
})

const allUsersForPublic = ref([]) // [{phone,name,role,is_active}]
const publicDeptRoleMap = ref({}) // { [deptId]: {dept: Set(phone), member: Set(phone)} }

// 公共空间 member 分组：手风琴（一次仅展开一个）
const publicOpenGroupKey = ref(null) // string | null

const togglePublicGroup = (key) => {
  publicOpenGroupKey.value = publicOpenGroupKey.value === key ? null : key
}

// 兼容：模板里原先用 publicGroupOpen[g.key]
const isPublicGroupOpen = (key) => publicOpenGroupKey.value === key

const loadPublicSpaceData = async () => {
  try {
    const all = await listUsers()
    allUsersForPublic.value = all || []
  } catch {
    allUsersForPublic.value = []
  }

  // 聚合：遍历所有部门的 roles
  const deptIds = (departments.value || []).map((d) => d.id)
  const map = {}
  for (const deptId of deptIds) {
    try {
      const roles = await getDepartmentRoles(deptId)
      const deptSet = new Set((roles.dept || []).map((u) => normalizePhone(u.phone)).filter(Boolean))
      const memSet = new Set((roles.member || []).map((u) => normalizePhone(u.phone)).filter(Boolean))
      map[deptId] = { dept: deptSet, member: memSet }
    } catch {
      map[deptId] = { dept: new Set(), member: new Set() }
    }
  }
  publicDeptRoleMap.value = map

  // 初始化：默认打开未分配
  if (!publicOpenGroupKey.value) publicOpenGroupKey.value = '__unassigned__'
}

const publicDeptAdmins = computed(() => {
  // 公共空间 dept 列：super + op
  return (allUsersForPublic.value || [])
    .filter((u) => u && (u.role === 'super' || u.role === 'op'))
    .map((u) => ({ phone: normalizePhone(u.phone), name: u.name || u.phone }))
    .filter((u) => u.phone)
    .sort((a, b) => a.phone.localeCompare(b.phone))
})

const rolePriority = (role) => {
  const r = (role || '').toString().toLowerCase()
  if (r === 'super') return 4
  if (r === 'op') return 3
  if (r === 'dept') return 2
  return 1 // user/unknown
}

const roleText = (role) => {
  const r = (role || '').toString().toLowerCase()
  if (r === 'super') return '超级管理员'
  if (r === 'op') return '系统管理员'
  if (r === 'dept') return '部门管理员'
  return '用户'
}

const buildGlobalRoleMap = (users) => {
  const m = new Map() // phone -> { role, text }
  ;(users || []).forEach((u) => {
    const phone = normalizePhone(u && u.phone)
    if (!phone) return
    const r = (u && u.role) || 'user'
    const prev = m.get(phone)
    if (!prev || rolePriority(r) > rolePriority(prev.role)) {
      m.set(phone, { role: r, text: roleText(r) })
    }
  })
  return m
}

const globalRoleByPhone = computed(() => buildGlobalRoleMap(allUsersForPublic.value || []))

const withGlobalRole = (list) => {
  const map = globalRoleByPhone.value
  return (list || []).map((u) => {
    const phone = normalizePhone(u && u.phone)
    const info = map.get(phone)
    return {
      ...u,
      phone,
      name: (u && u.name) || phone,
      globalRole: info ? info.role : 'user',
      globalRoleText: info ? info.text : '用户',
    }
  })
}

const deptAdminsTableRows = computed(() => withGlobalRole(deptAdmins.value).filter((u) => u.phone))
const deptMembersTableRows = computed(() => withGlobalRole(deptMembers.value).filter((u) => u.phone))

const publicDeptAdminsTableRows = computed(() => withGlobalRole(publicDeptAdmins.value).filter((u) => u.phone))

// publicMemberGroups 中 users 也补齐全局角色显示
const publicMemberGroups = computed(() => {
  const users = (allUsersForPublic.value || []).map((u) => ({
    phone: normalizePhone(u.phone),
    name: u.name || u.phone,
    role: u.role || 'user',
  })).filter((u) => u.phone)

  const phoneToUser = new Map(users.map((u) => [u.phone, u]))

  const deptIds = (departments.value || []).map((d) => d.id)
  const groups = []
  const assignedPhones = new Set()

  for (const deptId of deptIds) {
    const role = publicDeptRoleMap.value[deptId]
    const deptSet = role ? role.dept : new Set()
    const memSet = role ? role.member : new Set()

    const allPhones = new Set([...(deptSet || []), ...(memSet || [])])

    const list = withGlobalRole(
      Array.from(allPhones).map((p) => {
        const base = phoneToUser.get(p) || { phone: p, name: p }
        return {
          phone: base.phone,
          name: base.name,
          isDeptAdmin: deptSet ? deptSet.has(p) : false,
        }
      })
    ).sort((a, b) => a.phone.localeCompare(b.phone))

    list.forEach((x) => assignedPhones.add(x.phone))

    const deptName = (departments.value || []).find((d) => d.id === deptId)?.name || deptId
    groups.push({ key: deptId, title: deptName, users: list })
  }

  const unassigned = withGlobalRole(users.filter((u) => !assignedPhones.has(u.phone)))
    .sort((a, b) => a.phone.localeCompare(b.phone))

  groups.unshift({ key: '__unassigned__', title: '未分配部门成员', users: unassigned })

  return groups
})

// 当切换到公共空间时，拉取所需数据
watch(
  () => currentDeptId.value,
  async (v) => {
    if (v === '__public__') {
      await loadPublicSpaceData()
    }
  }
)

onMounted(async () => {
  currentUser.value = loadCurrentUserFromLocal()
  await loadDepartments()
})

// 默认权限组定义（占位，仅用于展示）
const defaultGroups = [
  {
    key: 'super',
    name: '超级管理员',
    desc: '系统级最高权限，一般对应全院信息科或系统维护人员，可访问和管理所有空间与配置。',
  },
  {
    key: 'op',
    name: '管理员',
    desc: '系统运维/业务管理员，具备大部分管理能力（如用户管理、公告、部分空间配置），但可与 super 做适当权限隔离。',
  },
  {
    key: 'user',
    name: '普通用户',
    desc: '默认登录用户，拥有个人保险库及对开放空间的基础访问/操作权限（具体粒度后续在此处细化）。',
  },
  {
    key: 'dept',
    name: '部门管理员',
    desc: '负责本部门空间的日常管理（如目录结构规划、文件归档、部门内权限调整等），需要与对应部门空间绑定。',
  },
  {
    key: 'member',
    name: '部门成员',
    desc: '本部门普通成员，在本部门空间内具备日常使用权限（浏览、上传、协同等），同样需要与对应部门空间绑定。',
  },
]

// ===========
// 系统管理员(op)编辑（公共空间、仅 super）
// ===========
const isSuper = computed(() => {
  const r = (currentUser.value && currentUser.value.role) || ''
  return r.toLowerCase() === 'super'
})

const openOpAdminModal = async () => {
  if (!isSuper.value) return

  // 复用 memberModal
  memberModal.value.visible = true
  memberModal.value.type = 'op'
  memberModal.value.keyword = ''
  memberModal.value.loading = true

  try {
    // 拉最新 users，保证角色实时
    const all = await listUsers()
    allUsersForPublic.value = all || []

    // 候选：全量用户（排除 super）
    const candidates = (allUsersForPublic.value || [])
      .map((u) => ({ phone: normalizePhone(u.phone), name: u.name || u.phone, role: u.role || 'user' }))
      .filter((u) => u.phone && (u.role || '').toLowerCase() !== 'super')

    memberModal.value.candidates = uniqByPhone(candidates)

    // 已选：当前 op 用户
    memberModal.value.selectedPhones = (allUsersForPublic.value || [])
      .filter((u) => (u.role || '').toLowerCase() === 'op')
      .map((u) => normalizePhone(u.phone))
      .filter(Boolean)
  } finally {
    memberModal.value.loading = false
  }
}

// 新增：控制权限组配置延迟出现
const showRolesSection = ref(true)
let rolesDelayTimer = null

const onBeforeRightSwitch = () => {
  // 切换时先隐藏权限组配置，避免与空间详情同步出现
  showRolesSection.value = false
  if (rolesDelayTimer) {
    clearTimeout(rolesDelayTimer)
    rolesDelayTimer = null
  }
}

const onAfterRightSwitch = () => {
  // 切换完成后延迟 0.02s 再显示权限组配置
  if (rolesDelayTimer) clearTimeout(rolesDelayTimer)
  rolesDelayTimer = setTimeout(() => {
    showRolesSection.value = true
  }, 20)
}
</script>

<style scoped>
.space-permission {
  display: flex;
  height: 100%;
  gap: 0.75rem;
  align-items: stretch; /* 左右两列等高 */
  min-height: 0;
}

.sp-left {
  flex: 0 0 260px;
  display: flex;
  flex-direction: column;
  background-color: #111827;
  color: #e5e7eb;
  border-radius: 4px;
  padding: 0.5rem 0.5rem 0.6rem;
  min-height: 0;
}

.sp-left-header h2 {
  margin: 0;
  font-size: 0.95rem;
}

.sp-left-tip {
  margin-top: 0.15rem;
  font-size: 0.78rem;
  color: #9ca3af;
}

.sp-dept-list {
  margin-top: 0.5rem;
  flex: 1 1 auto;
  overflow-y: auto;
}

.sp-dept-item {
  padding: 0.3rem 0.4rem;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 0.2rem;
}

.sp-dept-item:hover {
  background-color: #1f2937;
}

.sp-dept-item.active {
  background-color: #2563eb;
  color: #f9fafb;
}

.sp-dept-item .name {
  font-size: 0.9rem;
}

.sp-dept-item .id {
  margin-top: 0.05rem;
  font-size: 0.78rem;
  color: #9ca3af;
}

.sp-empty {
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: #9ca3af;
}

.sp-right {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 0;
}

/* 空间详情：随内容变化，但不允许被下方区域挤压 */
.sp-detail {
  background-color: #ffffff;
  border-radius: 4px;
  padding: 0.6rem 0.75rem 0.8rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  overflow: auto;
  flex: 0 0 auto;
  flex-shrink: 0;
  min-height: 0;
}

.sp-right-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sp-right-header h2 {
  margin: 0;
  font-size: 1rem;
}

.sp-right-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.sp-btn {
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #e5e7eb;
  color: #111827;
  font-size: 0.8rem;
  cursor: pointer;
}

.sp-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.sp-right-tip {
  margin-top: 0.2rem;
  font-size: 0.8rem;
  color: #6b7280;
}

.sp-config {
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: #374151;
}

.sp-config-block {
  margin-bottom: 0.9rem;
}

.sp-config-header {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 0.25rem 0.4rem;
  border-radius: 4px;
  background-color: #f3f4f6;
}

.sp-config-header .caret {
  width: 1rem;
  margin-right: 0.2rem;
}

.sp-config-header .title {
  font-size: 0.9rem;
  font-weight: 600;
}

.sp-config-body {
  margin-top: 0.3rem;
  padding: 0 0.2rem;
}

.sp-config-row {
  display: flex;
  margin-bottom: 0.2rem;
}

.sp-config-row .k {
  width: 120px;
  color: #6b7280;
}

.sp-config-row .v {
  flex: 1 1 auto;
}

.sp-config-empty {
  font-size: 0.8rem;
  color: #9ca3af;
}

.sp-roles-section {
  background-color: #ffffff;
  border-radius: 4px;
  padding: 0.6rem 0.75rem 0.8rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden; /* 防止外层被内容撑高 */
  display: flex;
  flex-direction: column;
}

.sp-roles-header h3 {
  margin: 0;
  font-size: 0.95rem;
}

.sp-roles-tip {
  margin-top: 0.2rem;
  font-size: 0.8rem;
  color: #6b7280;
}

.sp-roles-body {
  margin-top: 0.4rem;
  flex: 1 1 auto;
  min-height: 0;
}

/* 两列容器可以吃满高度 */
.sp-roles-two-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  height: 100%;
}

/* 每一列改为纵向布局：标题固定，列表区域滚动 */
.sp-roles-two-cols > .col {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.sp-roles-groups {
  margin-bottom: 0.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}

.group-row {
  display: grid;
  grid-template-columns: 80px 100px 1fr;
  gap: 0.3rem;
  padding: 0.3rem 0.45rem;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.82rem;
}

.group-row:last-child {
  border-bottom: none;
}

.g-key {
  font-family: Consolas, Menlo, Monaco, monospace;
  color: #374151;
}

.g-name {
  font-weight: 500;
}

.g-desc {
  color: #4b5563;
}

.sp-roles-placeholder .line {
  font-size: 0.82rem;
  color: #4b5563;
  margin-bottom: 0.15rem;
}

/* 空间开放开关样式 */
.sp-toggle-block {
  margin-bottom: 0.75rem;
}

.sp-toggle-body {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.85rem;
}

.switch-row .label {
  color: #374151;
}

.switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.1rem 0.35rem;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background-color: #f9fafb;
  cursor: pointer;
}

.switch .thumb {
  width: 26px;
  height: 14px;
  border-radius: 999px;
  background-color: #d1d5db;
  position: relative;
  transition: background-color 0.15s ease;
}

.switch .thumb::after {
  content: '';
  position: absolute;
  top: 1px;
  left: 1px;
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background-color: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.25);
  transition: transform 0.15s ease;
}

.switch .thumb.on {
  background-color: #22c55e;
}

.switch .thumb.on::after {
  transform: translateX(12px);
}

.switch-text {
  font-size: 0.8rem;
  color: #374151;
}

.sp-toggle-body .hint {
  font-size: 0.78rem;
  color: #9ca3af;
}

/* 权限组左右两栏布局 */
.sp-roles-section .sp-roles-two-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  height: 100%;
}

.sp-roles-two-cols .col-title {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 0.3rem;
}

.user-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  min-height: 80px;
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.user-item {
  display: flex;
  flex-direction: column;
  padding: 0.3rem 0.45rem;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.82rem;
}

.user-item:last-child {
  border-bottom: none;
}

.user-item .name {
  font-weight: 500;
}

.user-item .info {
  font-size: 0.78rem;
  color: #6b7280;
}

.user-list .empty {
  padding: 0.4rem 0.5rem;
  font-size: 0.8rem;
  color: #9ca3af;
}

/* 新增：列标题行和“编辑成员”按钮样式 */
.col-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.3rem;
}

.col-title {
  font-size: 0.9rem;
  font-weight: 600;
}

.col-edit-btn {
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #e5e7eb;
  color: #111827;
  font-size: 0.78rem;
  cursor: pointer; /* 现在按钮提供实际交互 */
}

.col-edit-btn:disabled {
  opacity: 0.6;
}

/* 编辑成员弹窗 */
.sp-mask {
  position: fixed;
  inset: 0;
  background-color: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.sp-dialog {
  width: 720px;
  max-width: calc(100vw - 24px);
  max-height: calc(70vh - 64px);
  background-color: #ffffff;
  border-radius: 8px;
  padding: 10px 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sp-dialog-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}

.sp-dialog-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.sp-search {
  flex: 1 1 auto;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  padding: 5px 10px;
  font-size: 13px;
}

.sp-toolbar-actions {
  display: flex;
  gap: 6px;
}

.sp-mini-btn {
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  font-size: 12px;
  cursor: pointer;
}

.sp-dialog-body {
  flex: 1 1 auto;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px;
}

.sp-dialog-hint {
  font-size: 13px;
  color: #6b7280;
}

.sp-user-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 10px;
}

.sp-user-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
  cursor: pointer;
}

.sp-user-row input {
  margin: 0;
}

.sp-user-row.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.sp-user-row.disabled input {
  cursor: not-allowed;
}

.sp-user-tag {
  margin-left: 8px;
  font-size: 12px;
  color: #9ca3af;
}

.sp-user-name {
  font-size: 12.5px;
  color: #111827;
}

.sp-user-phone {
  margin-left: auto;
  font-size: 11.5px;
  color: #6b7280;
  font-family: Consolas, Menlo, Monaco, monospace;
}

.sp-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
}

.sp-dialog-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sp-dialog-count {
  font-size: 12px;
  color: #6b7280;
}

.sp-dialog-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #9ca3af;
}

.sp-modal-enter-active,
.sp-modal-leave-active {
  transition: opacity 0.15s ease;
}

.sp-modal-enter-from,
.sp-modal-leave-to {
  opacity: 0;
}

.sp-noedit-tip {
  margin-top: 0.4rem;
  font-size: 0.82rem;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #f59e0b;
  padding: 0.35rem 0.5rem;
  border-radius: 6px;
}

/* 新增：公共空间权限组展示样式 */
.sp-public-groups {
  display: block;
  flex: 1 1 auto;
  min-height: 0;
  overflow: visible;
}

.sp-public-group {
  flex: 0 0 auto;
  margin-bottom: 8px;
}

.sp-public-group-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;

  /* 清掉 button 默认样式 */
  appearance: none;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  color: inherit;
  font: inherit;
  text-align: left;

  /* 交互 */
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  -ms-user-select: none;
}

/* 保留你之前的吸顶逻辑 */
.member-panel .sp-public-group-header {
  position: sticky;
  top: 0;
  z-index: 2;
  border-radius: 6px;
  padding: 6px 8px;
}

/* 键盘可访问性：给 focus 一个可见轮廓 */
.sp-public-group-header:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

/* 公共空间 member 列外边框：与左侧列表对称 */
.member-panel {
  border: none;
  border-radius: 0;
  padding: 0;
  /* 保持原有滚动与弹性行为 */
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

/* member-panel 内部的分组本身已有边框，这里稍微拉开间距 */
.member-panel .sp-public-group:last-child {
  margin-bottom: 0;
}

/* 让“公共空间 member 分组”的分组头在 member-panel 滚动时吸顶，便于随时关闭当前已展开分组 */
.member-panel .sp-public-group-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #f9fafb; /* 避免内容滚动到 header 下方时透出 */
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 6px 8px;
}

/* 复用现有 tag 样式，让公共空间“部门管理员”标签更醒目一点 */
.user-item .sp-user-tag {
  margin-top: 2px;
  align-self: flex-start;
  font-size: 12px;
  color: #2563eb;
}

.sp-table-wrap {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}

.sp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.sp-table thead th {
  position: sticky;
  top: 0;
  background: #f9fafb;
  z-index: 1;
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid #e5e7eb;
  color: #374151;
  font-weight: 600;
}

.sp-table tbody td {
  padding: 8px 10px;
  border-bottom: 1px solid #eef2f7;
  vertical-align: top;
}

.sp-table tbody tr:last-child td {
  border-bottom: none;
}

.sp-table .empty {
  color: #9ca3af;
  text-align: left;
  padding: 10px;
}

.c-idx { width: 56px; color: #6b7280; }
.c-phone { width: 140px; font-family: Consolas, Menlo, Monaco, monospace; }
.c-role { width: 110px; }

/* 表格里的“部门管理员”标签复用现有的 sp-user-tag 颜色，但更紧凑 */
.sp-table .sp-user-tag {
  margin-left: 6px;
  font-size: 12px;
  color: #2563eb;
}

/* 原先 list 风格保留给弹窗，避免影响其它样式 */

/* 右侧区域切换动画：淡入 + 轻微位移 */
.sp-right-inner {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 0;
  flex: 1 1 auto;
}

.sp-switch-enter-active,
.sp-switch-leave-active {
  transition: opacity 0.05s ease, transform 0.05s ease;
}

.sp-switch-enter-from,
.sp-switch-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.sp-switch-enter-to,
.sp-switch-leave-from {
  opacity: 1;
  transform: translateY(0);
}

/* 权限组配置：单独的进入/离开动画 */
.sp-roles-pop-enter-active,
.sp-roles-pop-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.sp-roles-pop-enter-from,
.sp-roles-pop-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.sp-roles-pop-enter-to,
.sp-roles-pop-leave-from {
  opacity: 1;
  transform: translateY(0);
}

/* ============
 * 移动端适配（/m）
 * ============ */
.sp-mobile-top {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
  margin-bottom: 10px;
}

.sp-mobile-title {
  font-weight: 800;
  color: #111827;
  margin-bottom: 8px;
}

.sp-mobile-select-row {
  display: flex;
  gap: 10px;
}

.sp-mobile-select {
  flex: 1;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  padding: 10px 12px;
  background: #fff;
}

.sp-mobile .sp-right {
  width: 100%;
}

/* 移动端：部门管理员/成员/空间详情纵向排列 */
.sp-mobile .sp-roles-two-cols {
  display: flex;
  flex-direction: column;
}

.sp-mobile .sp-roles-two-cols .col {
  width: 100%;
}

/* 移动端：成员选择弹窗改为单列 */
.sp-mobile .sp-user-grid {
  grid-template-columns: 1fr;
}
</style>
