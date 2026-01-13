<template>
  <div class="user-manage">
    <header class="page-header">
      <h2>人员管理</h2>
      <div class="actions">
        <input
          v-model="keyword"
          type="text"
          class="search-input"
          placeholder="按手机号或姓名搜索"
        />
        <!-- 预留：后续可以在这里加“新增成员”按钮 -->
      </div>
    </header>

    <section class="table-wrapper" v-if="filteredUsers.length">
      <table class="user-table">
        <thead>
          <tr>
            <th>手机号</th>
            <th>姓名</th>
            <th>角色</th>
            <th>状态</th>
            <th style="width: 220px;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in filteredUsers" :key="u.phone">
            <td>{{ u.phone }}</td>
            <td>{{ u.name }}</td>
            <td>
              <span class="tag" :class="'role-' + u.role.toLowerCase()">
                {{ roleLabel(u.role) }}
              </span>
            </td>
            <td>
              <span class="tag" :class="u.is_active ? 'status-active' : 'status-disabled'">
                {{ u.is_active ? '正常' : '已禁用' }}
              </span>
            </td>
            <td>
              <button
                class="btn-sm"
                :disabled="u.role.toLowerCase() === 'super'"
                @click="onDisable(u)"
              >
                禁用
              </button>
              <button
                class="btn-sm danger"
                :disabled="u.role.toLowerCase() === 'super'"
                @click="onHardDelete(u)"
              >
                硬删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
    <p v-else class="empty-text">暂无用户数据。</p>

    <!-- 简单的确认提示 -->
    <div v-if="confirmVisible" class="confirm-mask">
      <div class="confirm-dialog">
        <h3>确认操作</h3>
        <p class="confirm-text">{{ confirmText }}</p>
        <div class="confirm-actions">
          <button class="btn-sm" @click="confirmVisible = false">取消</button>
          <button class="btn-sm danger" @click="doConfirm">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const users = ref([])
const loading = ref(false)
const keyword = ref('')

const confirmVisible = ref(false)
const confirmText = ref('')
let confirmAction = null

const fetchUsers = async () => {
  loading.value = true
  try {
    const resp = await fetch('/api/users/', {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!resp.ok) throw new Error('加载用户列表失败')
    const data = await resp.json()
    users.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.error(e)
    alert('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchUsers()
})

const filteredUsers = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return users.value
  return users.value.filter((u) => {
    return (
      (u.phone && u.phone.includes(kw)) ||
      (u.name && u.name.includes(kw))
    )
  })
})

const roleLabel = (role) => {
  const r = (role || '').toLowerCase()
  if (r === 'super') return '超级管理员'
  if (r === 'op') return '管理员'
  return '普通用户'
}

const onDisable = (u) => {
  confirmText.value = `确定要禁用账号：${u.phone} 吗？`
  confirmVisible.value = true
  confirmAction = async () => {
    try {
      const resp = await fetch(`/api/users/disable/${encodeURIComponent(u.phone)}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!resp.ok) throw new Error('禁用失败')
      await fetchUsers()
    } catch (e) {
      console.error(e)
      alert('禁用失败')
    }
  }
}

const onHardDelete = (u) => {
  confirmText.value = `【危险操作】确定要硬删除账号：${u.phone} 吗？\n此操作会删除账号、清理其部门权限，并重命名其个人保密空间目录。`
  confirmVisible.value = true
  confirmAction = async () => {
    try {
      const resp = await fetch(`/api/users/${encodeURIComponent(u.phone)}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!resp.ok) throw new Error('硬删除失败')
      await fetchUsers()
    } catch (e) {
      console.error(e)
      alert('硬删除失败')
    }
  }
}

const doConfirm = async () => {
  if (typeof confirmAction === 'function') {
    await confirmAction()
  }
  confirmVisible.value = false
}
</script>

<style scoped>
.user-manage {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.page-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.search-input {
  padding: 0.35rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #d1d5db;
  font-size: 0.9rem;
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.user-table th,
.user-table td {
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}

.user-table thead {
  background-color: #f9fafb;
}

.tag {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  font-size: 0.75rem;
}

.role-super {
  background-color: #1f2937;
  color: #f9fafb;
}

.role-op {
  background-color: #2563eb;
  color: #f9fafb;
}

.role-user {
  background-color: #e5e7eb;
  color: #111827;
}

.status-active {
  background-color: #dcfce7;
  color: #166534;
}

.status-disabled {
  background-color: #fee2e2;
  color: #991b1b;
}

.btn-sm {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  margin-right: 0.4rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #f9fafb;
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-sm.danger {
  border-color: #ef4444;
  color: #b91c1c;
}

.btn-sm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-text {
  margin-top: 1rem;
  color: #6b7280;
}

.confirm-mask {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.confirm-dialog {
  background-color: #fff;
  padding: 1rem 1.2rem;
  border-radius: 4px;
  width: 360px;
  max-width: 90vw;
}

.confirm-dialog h3 {
  margin: 0 0 0.5rem 0;
}

.confirm-text {
  white-space: pre-line;
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.confirm-actions {
  text-align: right;
}
</style>
