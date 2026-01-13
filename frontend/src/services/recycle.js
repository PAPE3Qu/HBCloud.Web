import axios from 'axios'

// 回收站相关 API
export async function listTrash() {
  const { data } = await axios.get('/api/files/trash')
  return data || []
}

export async function restoreFile(fileId) {
  if (!fileId) return null
  const { data } = await axios.post(`/api/files/trash/${encodeURIComponent(fileId)}/restore`)
  return data
}

// ========================
// 空间 / 部门配置相关 API
// ========================

export async function listDepartments() {
  const { data } = await axios.get('/api/files/departments')
  return data || []
}

export async function getDepartmentConfig(deptId) {
  if (!deptId) return null
  const { data } = await axios.get(`/api/files/departments/${encodeURIComponent(deptId)}/config`)
  return data
}

// 新增：获取部门管理员/成员列表
export async function getDepartmentRoles(deptId) {
  if (!deptId) return { dept: [], member: [] }
  const { data } = await axios.get(`/api/files/departments/${encodeURIComponent(deptId)}/roles`)
  return data || { dept: [], member: [] }
}

// 新增：更新部门管理员/成员列表
export async function updateDepartmentRoles(deptId, payload) {
  if (!deptId) return null
  const { data } = await axios.put(`/api/files/departments/${encodeURIComponent(deptId)}/roles`, payload)
  return data
}

// 新增：更新部门配置（目前仅支持 isOpen，后续可扩展 payload 字段）
export async function updateDepartmentConfig(deptId, payload) {
  if (!deptId) return null
  const { data } = await axios.put(`/api/files/departments/${encodeURIComponent(deptId)}/config`, payload)
  return data
}

// ========================
// 用户相关（用于空间权限成员选择）
// ========================

// 直接使用现有 /api/users 接口（后端从 users.db 读取）获取用户列表
export async function listUsers() {
  // 后端路由定义为 "/"，在实际运行中 /api/users 会出现 307 跳转到 /api/users/
  // 直接请求带尾斜杠的路径，避免重定向导致的认证丢失问题。
  const { data } = await axios.get('/api/users/')
  return data || []
}

// ========================
// 系统管理员(op)维护（仅 super）
// ========================

export async function setOpUsers(phones) {
  const { data } = await axios.put('/api/users/op-set', { phones: phones || [] })
  return data || []
}

// 文件操作相关 API
export async function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await axios.post('/api/files/upload', formData)
  return data
}

export async function deleteFile(fileId) {
  if (!fileId) return null
  const { data } = await axios.delete(`/api/files/${encodeURIComponent(fileId)}`)
  return data
}