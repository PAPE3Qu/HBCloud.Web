// 文件分享相关的前端辅助函数
// 构造内部直链 /files?...，并解析 URL 查询参数，供 FileBrowser 复用

// 目前 FileBrowser.vue 在分享时已改为使用 /api/share 返回的 shareId 生成短链接，
// buildShareLink 仅保留兼容用途（例如后续可能的其他功能），不再依赖于在 URL 中携带大量文件名。

export function buildShareLink({ spaceType, departmentId, path, anchorName, selectedNames }) {
  const params = new URLSearchParams()
  params.set('spaceType', spaceType || 'public')
  if (spaceType === 'department' && departmentId) {
    params.set('departmentId', departmentId)
  }
  if (path && path !== '.' && path !== './') {
    params.set('path', path)
  }
  if (anchorName) {
    params.set('name', anchorName)
  }
  if (selectedNames && selectedNames.length) {
    params.set('selected', selectedNames.join(','))
  }
  return `${window.location.origin}/files?${params.toString()}`
}

export function parseFileBrowserQuery(route) {
  const q = route.query || {}
  const rawSpace = typeof q.spaceType === 'string' ? q.spaceType : ''
  const qSpaceType = rawSpace === 'department' || rawSpace === 'safe' ? rawSpace : 'public'
  const qDeptId = typeof q.departmentId === 'string' ? q.departmentId : ''
  const qPath = typeof q.path === 'string' ? q.path : ''
  const qName = typeof q.name === 'string' ? q.name : ''
  const qSelected = typeof q.selected === 'string' && q.selected
    ? q.selected.split(',').filter(Boolean)
    : []
  const qShareId = typeof q.shareId === 'string' ? q.shareId : ''
  return { qSpaceType, qDeptId, qPath, qName, qSelected, qShareId }
}

export async function copyToClipboard(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch (e) {
    // ignore and try fallback
  }

  // 旧浏览器降级方案
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch (e) {
    return false
  }
}
