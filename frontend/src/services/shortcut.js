import axios from 'axios'

export async function listShortcuts(spaceType, departmentId, path) {
  const params = { spaceType, path }
  if (spaceType === 'department') params.departmentId = departmentId
  const { data } = await axios.get('/api/shortcut/list', { params })
  return data || []
}

export async function addShortcut(spaceType, departmentId, path, shortcut) {
  const payload = { spaceType, departmentId, path, shortcut }
  const { data } = await axios.post('/api/shortcut/add', payload)
  return data
}

export async function removeShortcut(spaceType, departmentId, path, shortcut_id) {
  const payload = { spaceType, departmentId, path, shortcut_id }
  const { data } = await axios.post('/api/shortcut/remove', payload)
  return data
}
