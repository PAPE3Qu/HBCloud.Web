<template>
  <div class="file-browser" @click.self="detailVisible = false">
    <div class="file-browser-body" @click.self="favoriteVisible = false">
      <!-- 固定工具栏 -->
      <div class="toolbar-sticky">
      <div class="toolbar-row top-row" ref="topRow" :class="{ 'compact-row': topRowCompact }">
        <div class="toolbar-left">
          <!-- 空间 & 部门选择，使用更简洁的下拉样式 -->
          <label class="field">
            <span class="field-label">空间：</span>
            <select class="select-basic" v-model="spaceType" @change="onSpaceTypeChange">
              <option v-for="s in spaces" :key="s" :value="s">
                {{ s === 'public' ? '公共空间' : s === 'department' ? '部门空间' : '个人保险库' }}
              </option>
            </select>
          </label>
          <label v-if="spaceType === 'department'" class="field">
            <span class="field-label">部门：</span>
            <select class="select-basic" v-model="departmentId" @change="reload">
              <option disabled value="">请选择部门</option>
              <option v-for="d in departments" :key="d.id" :value="d.id">
                {{ d.name }}
              </option>
            </select>
          </label>
        </div>
        <div class="toolbar-right" ref="topRight">
          <div class="toolbar-actions">
            <button class="btn" type="button" @click="onRefreshClick" title="刷新"><span class="btn-icon">🔄</span><span class="btn-text">刷新</span></button>
            <button class="btn" type="button" @click="onDownloadZip" :disabled="selectedItems.length === 0" title="打包下载"><span class="btn-icon">📦</span><span class="btn-text">打包下载</span></button>
            <button class="btn" type="button" @click="openMoveDialog" :disabled="selectedItems.length === 0" title="移动到"><span class="btn-icon">📤</span><span class="btn-text">移动到</span></button>
            <button class="btn" type="button" @click="openCopyDialog" :disabled="selectedItems.length === 0" title="复制到"><span class="btn-icon">📋</span><span class="btn-text">复制到</span></button>
            <button class="btn btn-danger" type="button" @click="onDeleteSelected" :disabled="selectedItems.length === 0" title="删除"><span class="btn-icon">🗑️</span><span class="btn-text">删除</span></button>
            <button class="btn" type="button" @click="onCreateDept" title="新建部门"><span class="btn-icon">🏢</span><span class="btn-text">新建部门</span></button>
            <button class="btn btn-danger" type="button" @click="onDeleteDept" :disabled="spaceType !== 'department' || !departmentId" title="删除部门"><span class="btn-icon">❌</span><span class="btn-text">删除部门</span></button>
            <button class="btn" type="button" @click="onCreateFolder" title="新建文件夹"><span class="btn-icon">📁</span><span class="btn-text">新建文件夹</span></button>
            <button class="btn" type="button" @click="onUploadClick" title="上传文件"><span class="btn-icon">⬆️</span><span class="btn-text">上传文件</span></button>
          </div>
        </div>
      </div>

      <div class="toolbar-row second-row" ref="secondRow" :class="{ 'compact-row': secondRowCompact }">
        <div class="toolbar-left second-left">
          <div class="nav-group" ref="navGroup">
            <button class="nav-btn" type="button" @click="goBack" :disabled="!canGoBack" title="返回上一个访问位置">◀</button>
            <button class="nav-btn" type="button" @click="goRoot" title="返回空间根目录">⚑</button>
            <button class="nav-btn" type="button" @click="goUp" :disabled="!canGoUp" title="返回上级目录">▲</button>
          </div>
          <div class="breadcrumb-container" ref="breadcrumbContainer">
            <div class="breadcrumb-scroll" ref="breadcrumbScroll">
              <button class="breadcrumb-btn root-btn" type="button" @click="goRoot" title="根目录">/</button>
              <template v-for="(bc, idx) in breadcrumbDisplay" :key="idx">
                <span class="breadcrumb-sep">/</span>
                <!-- 普通目录段 -->
                <button
                  v-if="bc.type === 'segment'"
                  class="breadcrumb-btn"
                  :class="{ 'current-crumb': bc.index === breadcrumbs.length - 1 }"
                  type="button"
                  @click="navigateToBreadcrumb(bc.index)"
                  :title="bc.name"
                >{{ bc.name }}</button>
                <!-- 折叠段 "..."，不可点击 -->
                <span v-else class="breadcrumb-ellipsis">...</span>
              </template>
            </div>
          </div>
        </div>
        <div class="toolbar-right second-right" ref="secondRight">
          <div class="toolbar-actions">
            <button class="btn" type="button" @click="openLinkDialog" :disabled="selectedItems.length === 0 || hasLinkInSelection" title="链接到"><span class="btn-icon">🔗</span><span class="btn-text">链接到</span></button>
            <button class="btn" type="button" @click="onShare" :disabled="spaceType === 'safe'" title="分享"><span class="btn-icon">📤</span><span class="btn-text">分享</span></button>
            <button class="btn" type="button" @click="addCurrentOrSelectedToFavorite" :disabled="!canAddFavorite" title="快速访问"><span class="btn-icon">📌</span><span class="btn-text">快速访问</span></button>
            <button class="btn" type="button" @click="onCompress" :disabled="!canCompress" title="压缩"><span class="btn-icon">🗜️</span><span class="btn-text">压缩</span></button>
            <button class="btn" type="button" @click="onUnzipSelected" :disabled="!canUnzip" title="解压缩"><span class="btn-icon">📂</span><span class="btn-text">解压缩</span></button>
          </div>
          <div class="search-bar">
            <div class="select-wrapper">
              <input
                v-model="searchKeyword"
                type="text"
                placeholder="搜索当前目录及子目录"
                @keyup.enter="onSearch"
              />
            </div>
            <button class="btn" type="button" @click="onSearch" title="搜索"><span class="btn-icon">🔍</span><span class="btn-text">搜索</span></button>
            <button class="btn" type="button" @click="onClearSearch" v-if="inSearchMode" title="清除搜索"><span class="btn-icon">✖️</span><span class="btn-text">清除搜索</span></button>
          </div>
        </div>
      </div>
      </div><!-- 关闭 toolbar-sticky -->

      <input
        ref="fileInput"
        type="file"
        multiple
        style="display: none"
        @change="onFilesChosen"
      />

      <div class="content" ref="listWrapper" @click.stop>
        <div class="file-list">
          <table>
            <thead>
              <tr>
                <th
                  style="width: 32px; text-align: center"
                >
                  <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
                </th>
                <th
                  v-for="(col, index) in headerCols"
                  :key="col.key"
                  :style="headerStyle(index)"
                  @mousedown.prevent="startResize($event, index)"
                >
                  <span class="th-label">{{ col.label }}</span>
                  <span
                    v-if="!col.isOps"
                    class="col-resizer"
                    @mousedown.stop.prevent="startResize($event, index)"
                  ></span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in displayedItems"
                :key="itemKey(item)"
                :class="['clickable', { dir: item.is_dir, highlight: isHighlight(item) }]"
                @click="onRowClick(item, $event)"
                @dblclick.stop="onItemDblClick(item)"
              >
                <td style="text-align: center" @click.stop>
                  <input type="checkbox" :checked="isSelected(item)" @change="toggleSelect(item)" />
                </td>
                <td @dblclick.stop="onItemDblClick(item)">
                  <span>{{ fileIcon(item) }}</span>
                  <span class="name">{{ item.name }}</span>
                </td>
                <td>{{ item._is_link ? '快捷链接' : (item.is_dir ? '文件夹' : '文件') }}</td>
                <td>{{ item.is_dir ? '-' : formatSize(item.size) }}</td>
                <td>{{ formatTime(item.modified_time) }}</td>
                <td class="ops-cell">
                  <button
                    v-if="!item.is_dir"
                    class="op-btn"
                    type="button"
                    @click.stop="downloadSingle(item)"
                  >
                    下载
                  </button>
                  <button
                    class="op-btn"
                    type="button"
                    @click.stop="onRenameSingle(item)"
                  >
                    重命名
                  </button>
                  <button
                    class="op-btn op-danger"
                    type="button"
                    @click.stop="onDeleteSingle(item)"
                  >
                    删除
                  </button>
                  <button
                    class="op-btn"
                    type="button"
                    @click.stop="openDetail(item)"
                  >
                    详情
                  </button>
                </td>
              </tr>
              <tr v-if="!loading && displayedItems.length === 0">
                <td colspan="6" class="empty">{{ inSearchMode ? '未找到匹配结果' : '此目录下暂无文件或文件夹' }}</td>
              </tr>
              <tr v-if="loading">
                <td colspan="6" class="loading">加载中...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="showImagePreview" class="image-preview-mask" @click="closeImagePreview">
        <div class="image-preview-dialog" @click.stop>
          <img v-if="previewImage" :src="previewImage" alt="预览" />
        </div>
      </div>
      <div v-if="uploading" class="upload-mask">
        <div class="upload-dialog">
          <div class="upload-title">{{ uploadProgress.active ? uploadProgress.text : '正在上传，请稍候…' }}</div>
          <div class="upload-tip">根据文件大小和数量，可能需要一些时间。请勿关闭页面或重复操作。</div>
          <div v-if="uploadProgress.active" class="upload-progress-bar">
            <div class="upload-progress-inner" :style="{ width: uploadProgress.percent + '%' }"></div>
          </div>
          <div v-if="uploadProgress.active" class="upload-progress-text">{{ uploadProgress.percent }}%</div>
        </div>
      </div>
      <div v-if="compressing" class="upload-mask">
        <div class="upload-dialog">
          <div class="upload-title">正在压缩，请稍候…</div>
          <div class="upload-tip">根据文件大小和数量，可能需要一些时间。请勿关闭页面或重复操作。</div>
        </div>
      </div>

      <!-- 移动文件/文件夹弹窗 -->
      <transition name="fade-dialog">
        <div v-if="showMove" class="move-mask" @click="closeMoveDialog">
          <div class="move-dialog" @click.stop>
            <div class="move-header">移动到</div>
            <div class="move-body">
              <div class="move-row move-target-row">
                <div class="field move-field">
                  <span class="field-label">目标空间</span>
                  <select class="select-basic select-sm" v-model="moveSpaceType" @change="onMoveSpaceChange">
                    <option value="public">公共空间</option>
                    <option value="department">部门空间</option>
                    <option value="safe">个人保险库</option>
                  </select>
                </div>
                <div class="field move-field" v-if="moveSpaceType === 'department'">
                  <span class="field-label">目标部门</span>
                  <select class="select-basic select-sm" v-model="moveDepartmentId" @change="loadMoveList">
                    <option disabled value="">请选择部门</option>
                    <option v-for="d in allDepartments" :key="d.id" :value="d.id">{{ d.name }}</option>
                  </select>
                </div>
              </div>
              <div class="row">
                <div class="picker-pathbar">
                  <button class="btn btn-icon btn-sm" type="button" @click="moveGoRoot">首页</button>
                  <button class="btn btn-icon btn-sm" type="button" @click="moveGoUp" :disabled="!moveCanGoUp">上级</button>
                  <span class="path">目标路径：/{{ movePath }}</span>
                </div>
              </div>
              <div class="row move-toolbar">
                <button class="btn btn-sm" type="button" @click="onMoveNewFolder">新建文件夹</button>
                <div class="overwrite-group">
                  <div class="overwrite-title">同名处理：</div>
                  <label :class="['overwrite-option', { active: moveOverwriteMode === 'skip' }]">
                    <input type="radio" value="skip" v-model="moveOverwriteMode" />
                    跳过（推荐）
                  </label>
                  <label :class="['overwrite-option', { active: moveOverwriteMode === 'overwrite' }]">
                    <input type="radio" value="overwrite" v-model="moveOverwriteMode" />
                    覆盖（谨慎）
                  </label>
                </div>
              </div>
              <div class="overwrite-tip">当目标目录中已存在同名文件/文件夹时，请务必确认选择“跳过”还是“覆盖”，覆盖会删除原有文件后再移动。</div>
              <div class="move-list">
                <table>
                  <thead>
                    <tr>
                      <th>名称</th>
                      <th style="width:80px">类型</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="it in moveItems"
                      :key="it.name"
                      :class="{ dir: it.is_dir }"
                      @dblclick="onMoveDblClick(it)"
                    >
                      <td>
                        <span>{{ it.is_dir ? '📁' : '📄' }}</span>
                        <span class="name">{{ it.name }}</span>
                      </td>
                      <td>{{ it.is_dir ? '文件夹' : '文件' }}</td>
                    </tr>
                    <tr v-if="!moveItems.length && !moveLoading">
                      <td colspan="2" class="empty">该目录下暂无子文件夹/文件</td>
                    </tr>
                    <tr v-if="moveLoading">
                      <td colspan="2" class="loading">加载中...</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div class="move-footer">
              <button class="btn btn-primary btn-sm" type="button" @click="confirmMove">确定</button>
              <button class="btn btn-sm" type="button" @click="closeMoveDialog">取消</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- 复制 文件/文件夹 弹窗 -->
      <transition name="fade-dialog">
        <div v-if="showCopy" class="move-mask" @click="closeCopyDialog">
          <div class="move-dialog" @click.stop>
            <div class="move-header">复制到</div>
            <div class="move-body">
              <div class="move-row move-target-row">
                <div class="field move-field">
                  <span class="field-label">目标空间</span>
                  <select class="select-basic select-sm" v-model="copySpaceType" @change="onCopySpaceChange">
                    <option value="public">公共空间</option>
                    <option value="department">部门空间</option>
                    <option value="safe">个人保险库</option>
                  </select>
                </div>
                <div class="field move-field" v-if="copySpaceType === 'department'">
                  <span class="field-label">目标部门</span>
                  <select class="select-basic select-sm" v-model="copyDepartmentId" @change="loadCopyList">
                    <option disabled value="">请选择部门</option>
                    <option v-for="d in allDepartments" :key="d.id" :value="d.id">{{ d.name }}</option>
                  </select>
                </div>
              </div>
              <div class="row">
                <div class="picker-pathbar">
                  <button class="btn btn-icon btn-sm" type="button" @click="copyGoRoot">首页</button>
                  <button class="btn btn-icon btn-sm" type="button" @click="copyGoUp" :disabled="!copyCanGoUp">上级</button>
                  <span class="path">目标路径：/{{ copyPath }}</span>
                </div>
              </div>
              <div class="row move-toolbar">
                <button class="btn btn-sm" type="button" @click="onCopyNewFolder">新建文件夹</button>
                <div class="overwrite-group">
                  <div class="overwrite-title">同名处理：</div>
                  <label :class="['overwrite-option', { active: copyOverwriteMode === 'skip' }]">
                    <input type="radio" value="skip" v-model="copyOverwriteMode" />
                    跳过（推荐）
                  </label>
                  <label :class="['overwrite-option', { active: copyOverwriteMode === 'overwrite' }]">
                    <input type="radio" value="overwrite" v-model="copyOverwriteMode" />
                    覆盖（谨慎）
                  </label>
                </div>
              </div>
              <div class="overwrite-tip">当目标目录中已存在同名文件/文件夹时，复制操作将遵循此处的“跳过/覆盖”策略。</div>
              <div class="move-list">
                <table>
                  <thead>
                    <tr>
                      <th>名称</th>
                      <th style="width:80px">类型</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="it in copyItems"
                      :key="it.name"
                      :class="{ dir: it.is_dir }"
                      @dblclick="onCopyDblClick(it)"
                    >
                      <td>
                        <span>{{ it.is_dir ? '📁' : '📄' }}</span>
                        <span class="name">{{ it.name }}</span>
                      </td>
                      <td>{{ it.is_dir ? '文件夹' : '文件' }}</td>
                    </tr>
                    <tr v-if="!copyItems.length && !copyLoading">
                      <td colspan="2" class="empty">该目录下暂无子文件夹/文件</td>
                    </tr>
                    <tr v-if="copyLoading">
                      <td colspan="2" class="loading">加载中...</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div class="move-footer">
              <button class="btn btn-primary btn-sm" type="button" @click="confirmCopy">确定</button>
              <button class="btn btn-sm" type="button" @click="closeCopyDialog">取消</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- 链接到 文件/文件夹 弹窗 -->
      <transition name="fade-dialog">
        <div v-if="showLink" class="move-mask" @click="closeLinkDialog">
          <div class="move-dialog" @click.stop>
            <div class="move-header">链接到（创建快捷方式）</div>
            <div class="move-body">
              <div class="link-tip">将在目标位置创建快捷链接，双击链接可跳转到源文件位置。</div>
              <div class="move-row move-target-row">
                <div class="field move-field">
                  <span class="field-label">目标空间</span>
                  <select class="select-basic select-sm" v-model="linkSpaceType" @change="onLinkSpaceChange">
                    <option value="public">公共空间</option>
                    <option value="department">部门空间</option>
                    <option value="safe">个人保险库</option>
                  </select>
                </div>
                <div class="field move-field" v-if="linkSpaceType === 'department'">
                  <span class="field-label">目标部门</span>
                  <select class="select-basic select-sm" v-model="linkDepartmentId" @change="loadLinkList">
                    <option disabled value="">请选择部门</option>
                    <option v-for="d in allDepartments" :key="d.id" :value="d.id">{{ d.name }}</option>
                  </select>
                </div>
              </div>
              <div class="row">
                <div class="picker-pathbar">
                  <button class="btn btn-icon btn-sm" type="button" @click="linkGoRoot">首页</button>
                  <button class="btn btn-icon btn-sm" type="button" @click="linkGoUp" :disabled="!linkCanGoUp">上级</button>
                  <span class="path">目标路径：/{{ linkPath }}</span>
                </div>
              </div>
              <div class="row move-toolbar">
                <button class="btn btn-sm" type="button" @click="onLinkNewFolder">新建文件夹</button>
              </div>
              <div class="move-list">
                <table>
                  <thead>
                    <tr>
                      <th>名称</th>
                      <th style="width:80px">类型</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="it in linkItems"
                      :key="it.name"
                      :class="{ dir: it.is_dir }"
                      @dblclick="onLinkDblClick(it)"
                    >
                      <td>
                        <span>{{ it.is_dir ? '📁' : '📄' }}</span>
                        <span class="name">{{ it.name }}</span>
                      </td>
                      <td>{{ it.is_dir ? '文件夹' : '文件' }}</td>
                    </tr>
                    <tr v-if="!linkItems.length && !linkLoading">
                      <td colspan="2" class="empty">该目录下暂无子文件夹/文件</td>
                    </tr>
                    <tr v-if="linkLoading">
                      <td colspan="2" class="loading">加载中...</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div class="move-footer">
              <button class="btn btn-primary btn-sm" type="button" @click="confirmLink">确定</button>
              <button class="btn btn-sm" type="button" @click="closeLinkDialog">取消</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- 文件详情侧滑面板 -->
      <div v-if="detailVisible" class="detail-overlay">
        <div class="detail-mask" @click="detailVisible = false"></div>
        <div class="detail-panel" @click.stop>
          <div class="detail-header">
            <span class="detail-title">文件详情</span>
            <button class="detail-close" type="button" @click="detailVisible = false">✕</button>
          </div>
          <div class="detail-body" v-if="detailFile">
            <div class="detail-row"><span class="k">名称：</span><span class="v">{{ detailFile.name }}</span></div>
            <div class="detail-row"><span class="k">路径：</span><span class="v">/{{ currentPath }}</span></div>
            <div class="detail-row"><span class="k">空间：</span><span class="v">{{ spaceType === 'public' ? '公共空间' : spaceType === 'department' ? '部门空间' : '个人保险库' }}</span></div>
            <div class="detail-row"><span class="k">下载次数：</span><span class="v">{{ detailStat?.downloadCount ?? 0 }}</span></div>
            <div class="detail-row"><span class="k">最后访问时间：</span><span class="v">{{ formatDetailTime(detailStat?.lastAccessTs) }}</span></div>
            <div class="detail-row"><span class="k">最后编辑人：</span><span class="v">{{ detailStat?.lastEditUser || '—' }}</span></div>
            <div class="detail-row"><span class="k">最后编辑时间：</span><span class="v">{{ formatDetailTime(detailStat?.lastEditTs) }}</span></div>
          </div>
        </div>
      </div>
      <transition name="fade-task">
        <div v-if="busyTask.active" class="task-mask">
          <div class="task-dialog">
            <div class="task-title">{{ busyTask.text }}</div>
            <div class="task-tip">请勿频繁重复操作，耐心等待当前任务完成。</div>
            <div class="task-progress-bar">
              <div class="task-progress-inner" :style="{ width: busyTask.percent + '%' }"></div>
            </div>
            <div class="task-progress-text">{{ busyTask.percent }}%</div>
          </div>
        </div>
      </transition>

      <!-- 右侧：收藏路径侧拉面板 -->
      <transition name="fade-fav">
        <div v-if="favoriteVisible" class="fav-panel" @click.stop>
          <div class="fav-header">
            <span class="title">快速访问</span>
            <button type="button" class="close-btn" @click="favoriteVisible = false">✕</button>
          </div>
          <div class="fav-toolbar">
            <button class="btn btn-sm" type="button" @click="loadFavorites">刷新</button>
          </div>
          <div class="fav-list">
            <div
              v-for="fav in favoriteList"
              :key="fav.id || fav.spaceType + ':' + (fav.departmentId || '') + ':' + fav.path"
              class="fav-item"
            >
              <div class="fav-main" @click="goFavorite(fav)">
                <div class="fav-name">{{ fav.displayName || lastSegment(fav.path) || '根目录' }}</div>
                <div class="fav-meta">{{ describeSpace(fav) }} / {{ fav.path || '.' }}</div>
              </div>
              <button class="pin-btn" type="button" @click.stop="removeFavorite(fav)">
                ❌
              </button>
            </div>
            <div v-if="!favoriteList.length" class="fav-empty">暂无收藏路径，可在右上角“固定到快速访问”。</div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { parseFileBrowserQuery, copyToClipboard } from '../services/share'
import axios from 'axios'
import SparkMD5 from 'spark-md5'

const route = useRoute()
const router = useRouter()

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

const spaces = ref([])
const spaceType = ref('public')
const departments = ref([])
const departmentId = ref('')
const currentPath = ref('.')
const items = ref([])
const loading = ref(false)
const selectedItems = ref([])
const fileInput = ref(null)
const searchKeyword = ref('')
const searchResults = ref([])
const inSearchMode = ref(false)
const previewImage = ref(null)
const showImagePreview = ref(false)
const uploading = ref(false)
const compressing = ref(false)
const uploadProgress = ref({ active: false, text: '', percent: 0 })

// 顶部两行工具栏 DOM 引用，用于根据实际宽度动态调整布局
const topRow = ref(null)
const topRight = ref(null)
const secondRow = ref(null)
const secondRight = ref(null)
const navGroup = ref(null)
const breadcrumbContainer = ref(null)
const breadcrumbScroll = ref(null)

// 工具栏紧凑模式（按钮仅显示图标）
const topRowCompact = ref(false)
const secondRowCompact = ref(false)

// 新增：统一的耗时任务遮罩状态（用于压缩/解压/移动/复制/打包下载等）
const busyTask = ref({ active: false, text: '', percent: 0 })
// 估算型进度相关状态：用于打包/压缩/解压等后台任务
let busyTaskTimer = null
const busyTaskMeta = ref({ startTime: 0, totalBytes: 0, basePercent: 0, maxPercent: 99 })

const startEstimatedBusyTask = (text, basePercent, maxPercent, totalBytes) => {
  busyTask.value = { active: true, text, percent: basePercent }
  busyTaskMeta.value = {
    startTime: Date.now(),
    totalBytes: totalBytes || 0,
    basePercent,
    maxPercent,
  }
  if (busyTaskTimer) {
    clearInterval(busyTaskTimer)
    busyTaskTimer = null
  }
  // 基于时间与总大小粗略推进进度：假设 50MB/s 的“打包速率”
  const SPEED = 50 * 1024 * 1024 // 50MB/s
  busyTaskTimer = setInterval(() => {
    if (!busyTask.value.active) return
    const meta = busyTaskMeta.value
    if (!meta.totalBytes || meta.totalBytes <= 0) {
      // 若不知道总大小，则按固定速度缓慢前进
      if (busyTask.value.percent < meta.maxPercent) {
        busyTask.value.percent = Math.min(meta.maxPercent, busyTask.value.percent + 1)
      }
      return
    }
    const elapsed = (Date.now() - meta.startTime) / 1000
    const estimatedDoneBytes = elapsed * SPEED
    const ratio = Math.min(1, estimatedDoneBytes / meta.totalBytes)
    const span = meta.maxPercent - meta.basePercent
    const estPercent = meta.basePercent + Math.round(span * ratio)
    if (estPercent > busyTask.value.percent && busyTask.value.percent < meta.maxPercent) {
      busyTask.value.percent = Math.min(meta.maxPercent, estPercent)
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

const onDownloadZip = async () => {
  if (!selectedItems.value.length) return
  const total = selectedItems.value.length
  const totalSize = selectedItems.value.reduce((sum, it) => sum + (Number(it.size) || 0), 0)
  
  // 启动打包任务遮罩：按文件总大小估算进度，最高到 99%
  startEstimatedBusyTask(`正在打包 ${total} 个项目，请稍候…`, 5, 99, totalSize)
  try {
    const payload = {
      // 不设置业务 title，沿用后端默认 hbcloud_YYYYMMDD_HHMMSS.zip 命名
      title: '',
      items: selectedItems.value.map((it) => ({
        spaceType: spaceType.value,
        departmentId: spaceType.value === 'department' ? departmentId.value : null,
        path: getApiPathForList(),
        name: it.name,
      })),
    }
    // 创建异步打包任务并轮询状态
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
    setTimeout(() => {
      // 优先显示后端返回的结构化错误信息；否则显示异常消息
      const errorMsg = (e.response && e.response.data && e.response.data.detail) || e.message || String(e)
      if (errorMsg && (errorMsg.includes('超过') || errorMsg.includes('大小限制') || errorMsg.includes('1G') || errorMsg.includes('1GB'))) {
        alert(errorMsg)
      } else {
        alert(errorMsg || '打包下载失败')
      }
    }, 100)
  }
}

const showMove = ref(false)
const moveSpaceType = ref('public')
const moveDepartmentId = ref('')
const movePath = ref('')
const moveItems = ref([])
const moveLoading = ref(false)
const moveOverwriteMode = ref('skip') // skip / overwrite

const showCopy = ref(false)
const copySpaceType = ref('public')
const copyDepartmentId = ref('')
const copyPath = ref('')
const copyItems = ref([])
const copyLoading = ref(false)
const copyOverwriteMode = ref('skip')

const showLink = ref(false)
const linkSpaceType = ref('public')
const linkDepartmentId = ref('')
const linkPath = ref('')
const linkItems = ref([])
const linkLoading = ref(false)

const allDepartments = ref([])

const detailVisible = ref(false)
const detailFile = ref(null)
const detailStat = ref(null)

// 浏览历史记录栈（用于"返回"功能）
const browseHistory = ref([])
const isNavigatingBack = ref(false)  // 标记是否正在执行返回操作，避免重复记录

const canGoUp = computed(() => currentPath.value && currentPath.value !== '.')

// 面包屑导航计算属性
const breadcrumbs = computed(() => {
  const p = currentPath.value
  if (!p || p === '.' || p === '') return []
  // 分割路径，过滤空字符串
  return p.split('/').filter(seg => seg && seg !== '.')
})
// 根据实际可用宽度动态决定从第几个目录开始显示（左侧目录逐步隐藏）
const breadcrumbVisibleStart = ref(0)

// 对外提供的面包屑展示列表：
// - 当 breadcrumbVisibleStart > 0 且可见段多于 1 个时，在最左侧插入一个不可点击的 "..."
// - 始终保证最后一级目录可见
const breadcrumbDisplay = computed(() => {
  const list = breadcrumbs.value
  const total = list.length
  if (!total) return []

  let start = breadcrumbVisibleStart.value
  if (start < 0) start = 0
  // 至少保留 2 层目录（如果总数不足 2，则按实际数量保留）
  if (total <= 2) {
    if (start > total - 1) start = total - 1
  } else {
    if (start > total - 2) start = total - 2
  }

  const visible = list.slice(start)
  const result = []

  if (start > 0 && visible.length > 1) {
    result.push({ type: 'ellipsis' })
  }

  visible.forEach((name, idx) => {
    result.push({ type: 'segment', name, index: start + idx })
  })

  return result
})

// 导航到面包屑指定位置
const navigateToBreadcrumb = (index) => {
  if (index < 0) {
    goRoot()
    return
  }
  const crumbs = breadcrumbs.value
  if (index >= crumbs.length - 1) {
    // 点击最后一个（当前目录），不做跳转
    return
  }
  // 构建目标路径
  const targetPath = crumbs.slice(0, index + 1).join('/')
  pushHistory()
  currentPath.value = targetPath
  loadList()
}
const moveCanGoUp = computed(() => movePath.value && movePath.value !== '')
const copyCanGoUp = computed(() => copyPath.value && copyPath.value !== '')
const linkCanGoUp = computed(() => linkPath.value && linkPath.value !== '')

// 是否可以返回上一个位置
const canGoBack = computed(() => browseHistory.value.length > 0)

// 判断选中项是否包含链接（链接不能创建链接的链接）
const hasLinkInSelection = computed(() => selectedItems.value.some(it => it._is_link))

const isSuperAdmin = computed(() => currentUser.value && currentUser.value.role === 'super')

// safe 空间的“前端显示路径”与“后端 API path 参数”存在差异：
// - 普通用户：后端 resolve_root 已经是 SAFE_ROOT/<phone>，因此 API 的 path 参数应是相对 phone 根目录的路径。
//   - 根目录：传 '' 或 '.'
//   - 子目录：传 'a/b'
// - 超管：后端根为 SAFE_ROOT，path 直接相对 /safe
const normalizePath = (p) => String(p || '').replace(/^\/+|\/+$/g, '')

const ensureSafePathForUser = () => {
  if (spaceType.value !== 'safe') return

  if (!currentUser.value || !currentUser.value.phone) {
    alert('当前用户未登录或缺少手机号信息，无法访问个人保险库。')
    spaceType.value = 'public'
    reload()
    return
  }

  // 超管：允许从 /safe 根开始
  if (isSuperAdmin.value) {
    if (currentPath.value == null) currentPath.value = ''
    return
  }

  // 普通用户：UI 上固定显示 phone 作为“用户根”
  const phone = String(currentUser.value.phone)
  const p = normalizePath(currentPath.value)

  if (p === '' || p === '.') {
    currentPath.value = phone
    return
  }
  if (p === phone || p.startsWith(phone + '/')) return

  // 若外部把路径带成了不含 phone 的形式（例如 '1/abc'），则补齐到 phone 下用于显示
  currentPath.value = `${phone}/${p}`
}

// 将 currentPath（UI 展示路径）转换为后端 list API 的 path 参数
const getApiPathForList = () => {
  // public/department：沿用 '.' 语义
  if (spaceType.value !== 'safe') return currentPath.value || '.'

  // safe：超管直接相对 /safe
  if (isSuperAdmin.value) {
    const p = normalizePath(currentPath.value)
    return p === '' ? '.' : p
  }

  // safe：普通用户，API path 必须相对 phone 根
  const phone = String(currentUser.value?.phone || '')
  const p = normalizePath(currentPath.value)
  if (p === '' || p === '.' || p === phone) return '.'
  if (p.startsWith(phone + '/')) return p.slice(phone.length + 1) || '.'

  // 兜底：如果 currentPath 不含 phone，则认为它已经是相对 phone 的路径
  return p || '.'
}

// 搜索态 item._path 在前端保存的是“展示路径”（safe 普通用户为 phone/xxx）。
// 这里把它转成后端可接受的 path 参数（safe 普通用户需要去掉 phone 前缀）。
const getApiPathForItem = (item) => {
  const p = normalizePath(item?._path)
  if (spaceType.value !== 'safe') return p || (currentPath.value || '.')

  if (isSuperAdmin.value) return p || '.'

  const phone = String(currentUser.value?.phone || '')
  if (!p || p === '.' || p === phone) return '.'
  if (p.startsWith(phone + '/')) return p.slice(phone.length + 1) || '.'
  return p || '.'
}

const fileIcon = (item) => {
  // 链接项显示特殊图标
  if (item._is_link) {
    return item.is_dir ? '📁🔗' : '📄🔗'
  }
  if (item.is_dir) return '📁'
  const lower = (item.name || '').toLowerCase()
  if (lower.endsWith('.zip')) return '📦'
  if (lower.endsWith('.pdf')) return '📄'
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp') || lower.endsWith('.bmp')) return '🖼️'
  return '📃'
}

// 生成列表项唯一 key：链接使用 _link_id，普通文件使用 name-type
const itemKey = (item) => {
  if (item._is_link && item._link_id) {
    return `link-${item._link_id}`
  }
  return `${item.name}-${item.is_dir ? 'd' : 'f'}`
}

// 判断项是否被选中：链接使用 _link_id 判断
const isSelected = (item) => {
  if (item._is_link && item._link_id) {
    return selectedItems.value.some((s) => s._link_id === item._link_id)
  }
  // 普通文件排除链接项
  return selectedItems.value.some((s) => s.name === item.name && s.is_dir === item.is_dir && !s._is_link)
}

const isAllSelected = computed(() => {
  return items.value.length > 0 && selectedItems.value.length === items.value.length
})

const listWrapper = ref(null)
const highlightName = ref('')
const preSelectedNames = ref([])
let hasAppliedShareRedirect = false

const displayedItems = computed(() => {
  if (inSearchMode.value) {
    return searchResults.value.map((r) => ({
      name: r.name,
      is_dir: r.is_dir,
      size: r.size,
      modified_time: r.modified_time,
      _path: r.path,
    }))
  }
  return items.value
})

const isHighlight = (item) => {
  if (preSelectedNames.value && preSelectedNames.value.length) {
    return preSelectedNames.value.includes(item.name)
  }
  return !!highlightName.value && item.name === highlightName.value
}

const toggleSelect = (item) => {
  if (isSelected(item)) {
    // 取消选中：链接使用 _link_id，普通文件使用 name+is_dir
    if (item._is_link && item._link_id) {
      selectedItems.value = selectedItems.value.filter((s) => s._link_id !== item._link_id)
    } else {
      selectedItems.value = selectedItems.value.filter((s) => !(s.name === item.name && s.is_dir === item.is_dir && !s._is_link))
    }
  } else {
    selectedItems.value.push({ ...item })
  }
}

const toggleSelectAll = (e) => {
  if (e.target.checked) {
    selectedItems.value = items.value.map((it) => ({ ...it }))
  } else {
    selectedItems.value = []
  }
}

const loadSpaces = async () => {
  const { data } = await axios.get('/api/files/spaces')
  spaces.value = data || []
  // 确保前端空间列表包含 safe
  if (!spaces.value.includes('safe')) {
    spaces.value.push('safe')
  }
  if (!spaces.value.includes(spaceType.value) && spaces.value.length > 0) {
    spaceType.value = spaces.value[0]
  }
}

const loadDepartments = async () => {
  if (spaceType.value !== 'department') return
  const current = departmentId.value
  const { data } = await axios.get('/api/files/departments')
  departments.value = data || []
  if (current && departments.value.some(d => d.id === current)) {
    // 仅当当前选择的部门仍然存在时保留原值
    departmentId.value = current
  } else {
    // 否则不自动选择任何部门，提示用户手动选择
    departmentId.value = ''
  }
}

const loadAllDepartments = async () => {
  try {
    const { data } = await axios.get('/api/files/departments')
    allDepartments.value = data || []
  } catch {
    allDepartments.value = []
  }
}

const loadList = async () => {
  if (spaceType.value === 'department' && !departmentId.value) {
    items.value = []
    loading.value = false
    return
  }
  if (spaceType.value === 'safe') {
    ensureSafePathForUser()
  }
  loading.value = true
  try {
    const pathParam = getApiPathForList()
    const params = { spaceType: spaceType.value, path: pathParam }
    if (spaceType.value === 'department') params.departmentId = departmentId.value
    const { data } = await axios.get('/api/files/list', { params })
    items.value = data.items || []
  } catch (e) {
    console.error('loadList failed', e)
    items.value = []
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
    }
  } finally {
    loading.value = false
    // 列表加载完成后，根据当前宽度和路径重新计算工具栏布局
    nextTick(() => {
      updateToolbarLayout()
    })
  }
}

const reload = async () => {
  pushHistory()  // 记录当前位置（部门切换时调用）
  await loadList()
}

const onRefreshClick = async () => {
  highlightName.value = ''
  preSelectedNames.value = []
  router.replace({ path: '/files', query: {} })
  await reload()
}

const onSpaceTypeChange = async () => {
  // 切空间时先清理搜索/选择，避免“看起来没刷新”
  pushHistory()  // 记录当前位置
  inSearchMode.value = false
  searchResults.value = []
  selectedItems.value = []
  highlightName.value = ''
  preSelectedNames.value = []

  if (spaceType.value === 'department') {
    await loadDepartments()
    // 部门空间不自动选部门：让用户选；此时不要 reloadToRoot，否则会直接清空列表造成“没刷新”的错觉
    currentPath.value = '.'
    items.value = []
    return
  }

  // 非部门空间：回到空间根并刷新
  departmentId.value = ''
  await reloadToRoot()
}

const reloadToRoot = async () => {
  // 切换空间时，回到该空间的“根”
  if (spaceType.value === 'safe') {
    // safe：根是手机号目录（非超管）/ 或 ''（超管）
    currentPath.value = '.'
    ensureSafePathForUser()
  } else {
    currentPath.value = '.'
  }

  await loadList()
}

const onRowClick = (item, event) => {
  toggleSelect(item)
}

const onItemDblClick = async (item) => {
  // 如果是链接项，先检查源文件是否存在，再跳转
  if (item._is_link && item._link_source) {
    const source = item._link_source
    
    // 检查源文件是否存在
    try {
      const { data } = await axios.post('/api/files/links/check-source', {
        spaceType: source.spaceType,
        departmentId: source.departmentId,
        path: source.path,
        name: source.name,
      })
      
      if (!data.exists) {
        // 源文件不存在，提示用户
        let reason = '源文件可能已被删除、移动或重命名。'
        if (data.reason === 'no_permission') {
          reason = '您没有访问源文件所在空间的权限。'
        }
        
        const deleteLink = window.confirm(
          `⚠️ 无法访问链接目标\n\n${reason}\n\n链接指向：${source.spaceType === 'department' ? `部门空间/${source.departmentId}` : source.spaceType === 'safe' ? '个人保险库' : '公共空间'}/${source.path === '.' ? '' : source.path + '/'}${source.name}\n\n是否删除此快捷链接？`
        )
        
        if (deleteLink) {
          // 删除链接
          try {
            await axios.delete('/api/files/links', {
              data: {
                spaceType: spaceType.value,
                departmentId: spaceType.value === 'department' ? departmentId.value : null,
                path: getApiPathForList(),
                linkId: item._link_id,
              },
            })
            await loadList()
            alert('链接已删除')
          } catch (e) {
            alert((e.response && e.response.data && e.response.data.detail) || '删除链接失败')
          }
        }
        return
      }
    } catch (e) {
      console.error('检查链接源失败', e)
      // 检查失败时仍尝试跳转
    }
    
    pushHistory()  // 记录当前位置
    // 先切换空间和部门（如果需要）
    if (source.spaceType !== spaceType.value) {
      spaceType.value = source.spaceType
    }
    if (source.spaceType === 'department' && source.departmentId) {
      departmentId.value = source.departmentId
    }
    // 计算目标路径：如果源是文件夹，直接进入；如果是文件，进入其父目录
    if (item.is_dir) {
      // 链接指向文件夹，进入该文件夹
      const basePath = source.path && source.path !== '.' ? source.path : ''
      currentPath.value = basePath ? `${basePath}/${source.name}` : source.name
    } else {
      // 链接指向文件，进入其父目录
      currentPath.value = source.path && source.path !== '.' ? source.path : ''
    }
    loadList()
    return
  }
  
  if (item.is_dir) {
    pushHistory()  // 记录当前位置
    if (spaceType.value === 'safe') {
      ensureSafePathForUser()
    }
    // 修复BUG：进入新目录时清空选中项
    selectedItems.value = []
    const base = currentPath.value && currentPath.value !== '.' ? currentPath.value : ''
    currentPath.value = base ? `${base}/${item.name}` : item.name
    loadList()
    return
  }
  openPreview(item)
}

const openPreview = (item) => {
  const lower = item.name.toLowerCase()
  const url = buildDownloadUrl(item, true)
  if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif') || lower.endsWith('.webp')) {
    previewImage.value = url
    showImagePreview.value = true
  } else if (lower.endsWith('.pdf') || lower.endsWith('.md')) {
    window.open(url, '_blank')
  } else {
  }
}

const closeImagePreview = () => {
  showImagePreview.value = false
  previewImage.value = null
}

const buildDownloadUrl = (item, inline = false) => {
  const params = new URLSearchParams()
  params.append('spaceType', spaceType.value)
  if (spaceType.value === 'department') {
    params.append('departmentId', departmentId.value)
  }

  // 关键：下载时要与 list 的 path 规则一致。
  // 搜索态会有 item._path，需要转换；非搜索态用当前目录。
  const pathParam = inSearchMode.value && item?._path != null ? getApiPathForItem(item) : getApiPathForList()
  params.append('path', pathParam)

  params.append('name', item.name)
  if (inline) {
    params.append('disposition', 'inline')
  }
  return `/api/files/download?${params.toString()}`
}

const onUploadClick = () => {
  if (!fileInput.value) return
  fileInput.value.value = ''
  fileInput.value.click()
}

const BIG_THRESHOLD = 500 * 1024 * 1024 // 500MB

const computeFileMd5 = (file) => {
  return new Promise((resolve, reject) => {
    const chunkSize = 2 * 1024 * 1024 // 2MB
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

const estimateMd5TimeText = (size) => {
  const speed = 200 * 1024 * 1024 // 200MB/s
  if (!size || size <= 0) return ''
  const seconds = size / speed
  if (seconds <= 10) return '预计校验时间小于 10 秒'
  if (seconds <= 60) return '预计校验时间小于 1 分钟'
  const minutes = Math.round(seconds / 60)
  if (minutes <= 10) return `预计校验时间约 ${minutes} 分钟`
  return '预计校验时间较长，请耐心等待'
}

const onFilesChosen = async (e) => {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  if (files.length === 1 && files[0].size > BIG_THRESHOLD) {
    await uploadBigFile(files[0])
  } else {
    await uploadSmallFiles(files)
  }
  if (fileInput.value) fileInput.value.value = ''
}

const uploadSmallFiles = async (files) => {
  uploading.value = true
  const totalSize = files.reduce((sum, f) => sum + (f.size || 0), 0)
  const estText = estimateMd5TimeText(totalSize)
  uploadProgress.value = {
    active: true,
    text: estText ? `正在计算文件校验码…（${estText}）` : '正在计算文件校验码…',
    percent: 0,
  }
  try {
    const md5List = []
    for (let i = 0; i < files.length; i++) {
      const md5 = await computeFileMd5(files[i])
      md5List.push(md5)
      uploadProgress.value.percent = Math.round(((i + 1) / files.length) * 30)
    }
    const form = new FormData()
    form.append('spaceType', spaceType.value)
    if (spaceType.value === 'department') form.append('departmentId', departmentId.value)
    form.append('path', getApiPathForList())
    files.forEach((f, idx) => {
      form.append('files', f)
      form.append('md5', md5List[idx])
    })
    uploadProgress.value.text = '正在上传小文件…'
    await axios.post('/api/files/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (evt) => {
        if (!evt.total) return
        const p = 30 + Math.round((evt.loaded / evt.total) * 70)
        uploadProgress.value.percent = Math.min(100, p)
      },
    })
    uploadProgress.value.text = '上传完成，正在刷新列表…'
    uploadProgress.value.percent = 100
    await loadList()
    setTimeout(() => {
      alert('上传成功')
    }, 100)
  } catch (err) {
    console.error('uploadSmallFiles failed', err)
    uploadProgress.value.text = '上传失败'
    uploadProgress.value.percent = 100
    setTimeout(() => {
      alert((err.response && err.response.data && err.response.data.detail) || '上传失败')
    }, 100)
  } finally {
    setTimeout(() => {
      uploading.value = false
      uploadProgress.value = { active: false, text: '', percent: 0 }
    }, 200)
  }
}

const uploadBigFile = async (file) => {
  uploading.value = true
  const estText = estimateMd5TimeText(file.size || 0)
  uploadProgress.value = {
    active: true,
    text: estText ? `正在计算大文件校验码…（${estText}）` : '正在计算大文件校验码…',
    percent: 0,
  }
  try {
    const fileMd5 = await computeFileMd5(file)
    uploadProgress.value.text = '正在初始化大文件上传…'
    uploadProgress.value.percent = 10
    const initResp = await axios.post('/api/files/big/init', {
      spaceType: spaceType.value,
      departmentId: spaceType.value === 'department' ? departmentId.value : null,
      path: getApiPathForList(),
      fileName: file.name,
      size: file.size,
      fileMd5,
    })
    const uploadId = initResp.data.uploadId
    const chunkSize = initResp.data.chunkSize || 50 * 1024 * 1024
    const total = Math.ceil(file.size / chunkSize)

    let index = 0
    let offset = 0
    while (offset < file.size) {
      const end = Math.min(offset + chunkSize, file.size)
      const blob = file.slice(offset, end)
      const form = new FormData()
      form.append('uploadId', uploadId)
      form.append('index', String(index))
      form.append('total', String(total))
      form.append('chunk', blob, file.name)
      uploadProgress.value.text = `正在上传大文件分片 ${index + 1} / ${total}…`
      const base = 10 + Math.round((index / total) * 80)
      uploadProgress.value.percent = Math.min(99, base)
      await axios.post('/api/files/big/chunk', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      index += 1
      offset = end
    }

    uploadProgress.value.text = '正在合并分片并校验文件…'
    uploadProgress.value.percent = 99
    await axios.post('/api/files/big/complete', { uploadId })
    uploadProgress.value.percent = 100
    await loadList()
    setTimeout(() => {
      alert('大文件上传完成')
    }, 100)
  } catch (err) {
    console.error('uploadBigFile failed', err)
    uploadProgress.value.text = '大文件上传失败'
    uploadProgress.value.percent = 100
    setTimeout(() => {
      alert((err.response && err.response.data && err.response.data.detail) || '大文件上传失败')
    }, 100)
  } finally {
    setTimeout(() => {
      uploading.value = false
      uploadProgress.value = { active: false, text: '', percent: 0 }
    }, 200)
  }
}

const onDeleteSelected = async () => {
  if (!selectedItems.value.length) return
  const ok = window.confirm(`将把选中的 ${selectedItems.value.length} 个项目移入回收站，可在回收站中恢复或彻底删除，是否继续？`)
  if (!ok) return
  try {
    const pathParam = getApiPathForList()
    const itemsPayload = selectedItems.value.map((it) => ({
      spaceType: spaceType.value,
      departmentId: spaceType.value === 'department' ? departmentId.value : null,
      path: pathParam,
      name: it.name,
      is_dir: it.is_dir,
    }))
    await axios.delete('/api/files', { data: { items: itemsPayload } })
    selectedItems.value = []
    await loadList()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '删除失败')
  }
}

const onRename = async () => {
  if (selectedItems.value.length !== 1) return
  const item = selectedItems.value[0]
  let defaultName = item.name
  let selectEnd = defaultName.length
  const dotIndex = defaultName.lastIndexOf('.')
  if (!item.is_dir && dotIndex > 0) {
    selectEnd = dotIndex
  }
  const newName = window.prompt('请输入新名称：（如非需要请勿更改文件拓展名 “.xxx”）', defaultName)
  if (!newName || newName === item.name) return
  try {
    await axios.put('/api/files/rename', {
      spaceType: spaceType.value,
      departmentId: spaceType.value === 'department' ? departmentId.value : null,
      path: inSearchMode.value && item._path != null ? getApiPathForItem(item) : getApiPathForList(),
      oldName: item.name,
      newName,
      isDir: item.is_dir,
    })
    selectedItems.value = []
    if (inSearchMode.value) {
      await onSearch()
    } else {
      await loadList()
    }
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '重命名失败')
  }
}

const onSearch = async () => {
  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    inSearchMode.value = false
    searchResults.value = []
    await loadList()
    return
  }
  loading.value = true
  try {
    const params = {
      spaceType: spaceType.value,
      path: getApiPathForList(),
      keyword,
    }
    if (spaceType.value === 'department') params.departmentId = departmentId.value
    const { data } = await axios.get('/api/files/search', { params })
    searchResults.value = data || []
    inSearchMode.value = true
    selectedItems.value = []
  } finally {
    loading.value = false
  }
}

const onClearSearch = async () => {
  searchKeyword.value = ''
  inSearchMode.value = false
  searchResults.value = []
  selectedItems.value = []
  await loadList()
}

const onItemClick = (item) => {
  if (!item.is_dir) return

  if (spaceType.value === 'safe') {
    ensureSafePathForUser()
  }

  const base = currentPath.value && currentPath.value !== '.' ? currentPath.value : ''
  currentPath.value = base ? `${base}/${item.name}` : item.name
  loadList()
}

// 记录当前位置到历史栈（在导航前调用）
const pushHistory = () => {
  if (isNavigatingBack.value) return  // 返回操作时不记录
  browseHistory.value.push({
    spaceType: spaceType.value,
    departmentId: departmentId.value,
    path: currentPath.value,
  })
  // 限制历史记录数量，避免内存过大
  if (browseHistory.value.length > 50) {
    browseHistory.value.shift()
  }
}

// 返回上一个访问位置
const goBack = async () => {
  if (browseHistory.value.length === 0) return
  const prev = browseHistory.value.pop()
  isNavigatingBack.value = true
  try {
    // 切换空间
    if (prev.spaceType !== spaceType.value) {
      spaceType.value = prev.spaceType
    }
    // 切换部门
    if (prev.spaceType === 'department') {
      departmentId.value = prev.departmentId || ''
    }
    // 切换路径
    currentPath.value = prev.path || '.'
    await loadList()
  } finally {
    isNavigatingBack.value = false
  }
}

const goUp = () => {
  if (!currentPath.value || currentPath.value === '.' ) return
  pushHistory()  // 记录当前位置
  const parts = currentPath.value.split('/')
  parts.pop()
  currentPath.value = parts.length ? parts.join('/') : '.'
  loadList()
}

const goRoot = () => {
  pushHistory()  // 记录当前位置
  // safe 空间根目录：普通用户为手机号目录（展示），但 list API 仍使用 '.'
  if (spaceType.value === 'safe') {
    currentPath.value = '.'
    ensureSafePathForUser()
  } else {
    currentPath.value = '.'
  }
  inSearchMode.value = false
  searchResults.value = []
  selectedItems.value = []
  loadList()
}

const downloadSingle = (item) => {
  const url = buildDownloadUrl(item, false)
  window.open(url, '_blank')
}

const onRenameSingle = async (item) => {
  selectedItems.value = [item]
  await onRename()
}

const onDeleteSingle = async (item) => {
  // 如果是链接项，调用链接删除API（不影响源文件）
  if (item._is_link && item._link_id) {
    const ok = window.confirm(`将删除快捷链接"${item.name}"，源文件不受影响，是否继续？`)
    if (!ok) return
    try {
      await axios.delete('/api/files/links', {
        data: {
          spaceType: spaceType.value,
          departmentId: spaceType.value === 'department' ? departmentId.value : null,
          path: getApiPathForList(),
          linkId: item._link_id,
        },
      })
      selectedItems.value = []
      await loadList()
    } catch (e) {
      alert((e.response && e.response.data && e.response.data.detail) || '删除链接失败')
    }
    return
  }
  
  // 普通文件/文件夹删除
  const ok = window.confirm(`将把"${item.name}"移入回收站，可在回收站中恢复或彻底删除，是否继续？`)
  if (!ok) return
  try {
    const payload = {
      items: [
        {
          spaceType: spaceType.value,
          departmentId: spaceType.value === 'department' ? departmentId.value : null,
          path: inSearchMode.value && item._path != null ? getApiPathForItem(item) : getApiPathForList(),
          name: item.name,
          is_dir: item.is_dir,
        },
      ],
    }
    await axios.delete('/api/files', { data: payload })
    selectedItems.value = []
    if (inSearchMode.value) {
      await onSearch()
    } else {
      await loadList()
    }
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '删除失败')
  }
}
const canCompress = computed(() => selectedItems.value.length >= 1)
const canUnzip = computed(() => {
  if (selectedItems.value.length !== 1) return false
  const it = selectedItems.value[0]
  return !it.is_dir && it.name.toLowerCase().endsWith('.zip')
})

const onCompress = async () => {
  if (!canCompress.value) return
  const name = window.prompt('请输入压缩文件名称（不含扩展名）：')
  if (!name) return
  const zipName = name.endsWith('.zip') ? name : name + '.zip'
  const total = selectedItems.value.length
  const totalSize = selectedItems.value.reduce((sum, it) => sum + (it.size || 0), 0)
  startEstimatedBusyTask(`正在压缩 ${total} 个项目，请稍候…`, 5, 99, totalSize)
  try {
    const payload = {
      spaceType: spaceType.value,
      departmentId: spaceType.value === 'department' ? departmentId.value : null,
      path: getApiPathForList(),
      zipName,
      items: selectedItems.value.map((it) => ({
        name: it.name,
        is_dir: it.is_dir,
      })),
    }
    await axios.post('/api/files/compress', payload)
    finishBusyTask('压缩完成，正在刷新列表…', 100, 500)
    await loadList()
    setTimeout(() => {
      alert('压缩完成')
    }, 100)
  } catch (e) {
    finishBusyTask('压缩失败', 100, 500)
    setTimeout(() => {
      alert((e.response && e.response.data && e.response.data.detail) || '压缩失败')
    }, 100)
  }
}

const onUnzipSelected = async () => {
  if (!canUnzip.value) return
  const item = selectedItems.value[0]
  const overwrite = window.confirm('是否在遇到同名文件时覆盖？\n“确定”=覆盖，“取消”=跳过已有文件。')
  const totalSize = item.size || 0
  startEstimatedBusyTask('正在解压缩文件，请稍候…', 10, 99, totalSize)
  try {
    await axios.post('/api/files/unzip', {
      spaceType: spaceType.value,
      departmentId: spaceType.value === 'department' ? departmentId.value : null,
      path: inSearchMode.value && item._path != null ? getApiPathForItem(item) : getApiPathForList(),
      name: item.name,
      overwrite,
    })
    finishBusyTask('解压完成，正在刷新列表…', 100, 500)
    if (inSearchMode.value) {
      await onSearch()
    } else {
      await loadList()
    }
    setTimeout(() => {
      alert('解压完成')
    }, 100)
  } catch (e) {
    finishBusyTask('解压失败', 100, 500)
    setTimeout(() => {
      alert((e.response && e.response.data && e.response.data.detail) || '解压失败')
    }, 100)
  }
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

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const pad = (n) => (n < 10 ? '0' + n : '' + n)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const formatDetailTime = (ts) => {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  const pad = (n) => (n < 10 ? '0' + n : '' + n)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const openDetail = async (item) => {
  detailFile.value = item
  detailVisible.value = true
  try {
    const pathParam = currentPath.value && currentPath.value !== '.' ? currentPath.value : ''
    const params = {
      spaceType: spaceType.value,
      departmentId: spaceType.value === 'department' ? departmentId.value : undefined,
      path: pathParam,
      name: item.name,
    }
    const { data } = await axios.get('/api/audit/file-detail', { params })
    if (data && data.item) {
      detailStat.value = data.item
    } else {
      detailStat.value = {
        downloadCount: 0,
        lastAccessTs: null,
        lastEditUser: null,
        lastEditTs: null,
      }
    }
  } catch (e) {
    console.error('openDetail failed', e)
    detailStat.value = {
      downloadCount: 0,
      lastAccessTs: null,
      lastEditUser: null,
      lastEditTs: null,
    }
  }
}

const onCreateDept = async () => {
  const id = window.prompt('请输入部门 ID（仅英文和数字，1~16 位）：')
  if (!id) return
  const trimmedId = id.trim()
  if (!/^[A-Za-z0-9]{1,16}$/.test(trimmedId)) {
    alert('部门 ID 仅支持英文和数字，长度 1~16 位。')
    return
  }
  const name = window.prompt('请输入部门名称（显示名，可中文，可与 ID 不同）：')
  if (!name || !name.trim()) {
    alert('部门名称不能为空。')
    return
  }
  const pwd = window.prompt('请为该部门设置 6 位数字删除密码：') || ''
  if (!pwd || !/^[0-9]{6}$/.test(pwd)) {
    alert('部门删除密码必须为 6 位数字。')
    return
  }
  try {
    await axios.post('/api/files/departments', { id: trimmedId, name: name.trim(), deletePassword: pwd })
    spaceType.value = 'department'
    await loadDepartments()
    departmentId.value = trimmedId
    await reload()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '创建部门失败')
  }
}

const onDeleteDept = async () => {
  if (spaceType.value !== 'department' || !departmentId.value) return

  let pwd = ''
  if (!isSuperAdmin.value) {
    pwd = window.prompt(`删除部门 "${departmentId.value}" 需要输入 6 位删除密码：`) || ''
    if (!pwd || pwd.length !== 6) {
      alert('删除密码必须为 6 位。')
      return
    }
  }

  const ok = window.confirm(`将删除部门 "${departmentId.value}" 下的所有文件，不可恢复，是否确认？`)
  if (!ok) return
  try {
    await axios.delete('/api/files/departments', { data: { id: departmentId.value, deletePassword: pwd } })
    departmentId.value = ''
    await loadDepartments()
    if (!departments.value.length) {
      spaceType.value = 'public'
    }
    await reload()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '删除部门失败')
  }
}

const onCreateFolder = async () => {
  const name = window.prompt('请输入新建文件夹名称：')
  if (!name) return
  try {
    await axios.post('/api/files/folder', {
      spaceType: spaceType.value,
      departmentId: spaceType.value === 'department' ? departmentId.value : null,
      path: getApiPathForList(),
      folderName: name,
    })
    await loadList()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '新建文件夹失败')
  }
}

const openMoveDialog = async () => {
  showMove.value = true
  moveSpaceType.value = spaceType.value
  if (!allDepartments.value.length) {
    await loadAllDepartments()
  }
  moveDepartmentId.value = spaceType.value === 'department' ? departmentId.value : ''
  movePath.value = ''
  moveOverwriteMode.value = 'skip'
  await loadMoveList()
}

const closeMoveDialog = () => {
  showMove.value = false
}

const onMoveSpaceChange = async () => {
  if (moveSpaceType.value === 'department') {
    if (!allDepartments.value.length) {
      await loadAllDepartments()
    }
    moveDepartmentId.value = ''
  } else {
    moveDepartmentId.value = ''
  }
  movePath.value = ''
  await loadMoveList()
}

const loadMoveList = async () => {
  if (moveSpaceType.value === 'department' && !moveDepartmentId.value) {
    moveItems.value = []
    return
  }
  moveLoading.value = true
  try {
    const params = {
      spaceType: moveSpaceType.value,
      path: movePath.value || ''
    }
    if (moveSpaceType.value === 'department') {
      params.departmentId = moveDepartmentId.value
    }
    const { data } = await axios.get('/api/files/list', { params })
    moveItems.value = data.items || []
  } catch (e) {
    console.error('loadMoveList failed', e)
    moveItems.value = []
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
    }
  } finally {
    moveLoading.value = false
  }
}

const moveGoRoot = async () => {
  movePath.value = ''
  await loadMoveList()
}

const moveGoUp = async () => {
  if (!movePath.value) return
  const parts = movePath.value.split('/')
  parts.pop()
  movePath.value = parts.join('/')
  await loadMoveList()
}

const onMoveDblClick = async (it) => {
  if (!it.is_dir) return
  const parts = movePath.value ? movePath.value.split('/'): []
  parts.push(it.name)
  movePath.value = parts.join('/')
  await loadMoveList()
}

const onMoveNewFolder = async () => {
  const name = window.prompt('请输入新建文件夹名称：')
  if (!name) return
  try {
    const payload = {
      spaceType: moveSpaceType.value,
      departmentId: moveSpaceType.value === 'department' ? moveDepartmentId.value : null,
      path: movePath.value || '',
      folderName: name,
    }
    await axios.post('/api/files/folder', payload)
    await loadMoveList()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '新建文件夹失败')
  }
}

const confirmMove = async () => {
  if (!selectedItems.value.length) return
  const total = selectedItems.value.length
  const totalSize = selectedItems.value.reduce((sum, it) => sum + (it.size || 0), 0)
  startEstimatedBusyTask(`正在移动 ${total} 个项目，请稍候…`, 10, 99, totalSize)
  try {
    const srcPath = getApiPathForList()
    const payload = {
      items: selectedItems.value.map((it) => ({
        spaceType: spaceType.value,
        departmentId: spaceType.value === 'department' ? departmentId.value : null,
        path: srcPath,
        name: it.name,
        is_dir: it.is_dir,
      })),
      targetSpaceType: moveSpaceType.value,
      targetDepartmentId: moveSpaceType.value === 'department' ? moveDepartmentId.value : null,
      targetPath: movePath.value || '',
      overwrite: moveOverwriteMode.value === 'overwrite',
    }
    await axios.post('/api/files/move', payload)
    finishBusyTask('移动完成，正在刷新列表…', 100, 500)
    showMove.value = false
    selectedItems.value = []
    await goToPath(payload.targetSpaceType, payload.targetDepartmentId, payload.targetPath || '.')
  } catch (e) {
    finishBusyTask('移动失败', 100, 500)
    const msg = (e.response && e.response.data && e.response.data.detail) || '移动失败'
    setTimeout(() => {
      alert(msg)
    }, 100)
  }
}

const openCopyDialog = async () => {
  showCopy.value = true
  copySpaceType.value = spaceType.value
  if (!allDepartments.value.length) {
    await loadAllDepartments()
  }
  copyDepartmentId.value = spaceType.value === 'department' ? departmentId.value : ''
  copyPath.value = ''
  copyOverwriteMode.value = 'skip'
  await loadCopyList()
}

const openLinkDialog = async () => {
  showLink.value = true
  linkSpaceType.value = spaceType.value
  if (!allDepartments.value.length) {
    await loadAllDepartments()
  }
  linkDepartmentId.value = spaceType.value === 'department' ? departmentId.value : ''
  linkPath.value = ''
  await loadLinkList()
}

const closeCopyDialog = () => {
  showCopy.value = false
}

const onCopySpaceChange = async () => {
  if (copySpaceType.value === 'department') {
    if (!allDepartments.value.length) {
      await loadAllDepartments()
    }
    copyDepartmentId.value = ''
  } else {
    copyDepartmentId.value = ''
  }
  copyPath.value = ''
  await loadCopyList()
}

const loadCopyList = async () => {
  if (copySpaceType.value === 'department' && !copyDepartmentId.value) {
    copyItems.value = []
    return
  }
  copyLoading.value = true
  try {
    const params = {
      spaceType: copySpaceType.value,
      path: copyPath.value || ''
    }
    if (copySpaceType.value === 'department') {
      params.departmentId = copyDepartmentId.value
    }
    const { data } = await axios.get('/api/files/list', { params })
    copyItems.value = data.items || []
  } catch (e) {
    console.error('loadCopyList failed', e)
    copyItems.value = []
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
    }
  } finally {
    copyLoading.value = false
  }
}

const copyGoRoot = async () => {
  copyPath.value = ''
  await loadCopyList()
}

const copyGoUp = async () => {
  if (!copyPath.value) return
  const parts = copyPath.value.split('/')
  parts.pop()
  copyPath.value = parts.join('/')
  await loadCopyList()
}

const onCopyDblClick = async (it) => {
  if (!it.is_dir) return
  const parts = copyPath.value ? copyPath.value.split('/'): []
  parts.push(it.name)
  copyPath.value = parts.join('/')
  await loadCopyList()
}

const onCopyNewFolder = async () => {
  const name = window.prompt('请输入新建文件夹名称：')
  if (!name) return
  try {
    const payload = {
      spaceType: copySpaceType.value,
      departmentId: copySpaceType.value === 'department' ? copyDepartmentId.value : null,
      path: copyPath.value || '',
      folderName: name,
    }
    await axios.post('/api/files/folder', payload)
    await loadCopyList()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '新建文件夹失败')
  }
}

const confirmCopy = async () => {
  if (!selectedItems.value.length) return
  const total = selectedItems.value.length
  const totalSize = selectedItems.value.reduce((sum, it) => sum + (it.size || 0), 0)
  startEstimatedBusyTask(`正在复制 ${total} 个项目，请稍候…`, 10, 99, totalSize)
  try {
    const srcPath = getApiPathForList()
    const payload = {
      items: selectedItems.value.map((it) => ({
        spaceType: spaceType.value,
        departmentId: spaceType.value === 'department' ? departmentId.value : null,
        path: srcPath,
        name: it.name,
        is_dir: it.is_dir,
      })),
      targetSpaceType: copySpaceType.value,
      targetDepartmentId: copySpaceType.value === 'department' ? copyDepartmentId.value : null,
      targetPath: copyPath.value || '',
      overwrite: copyOverwriteMode.value === 'overwrite',
    }
    await axios.post('/api/files/copy', payload)
    finishBusyTask('复制完成', 100, 500)
    showCopy.value = false
    await goToPath(payload.targetSpaceType, payload.targetDepartmentId, payload.targetPath || '.')
  } catch (e) {
    finishBusyTask('复制失败', 100, 500)
    const msg = (e.response && e.response.data && e.response.data.detail) || '复制失败'
    setTimeout(() => {
      alert(msg)
    }, 100)
  }
}

// ==================== 链接功能 ====================

const closeLinkDialog = () => {
  showLink.value = false
}

const onLinkSpaceChange = async () => {
  if (linkSpaceType.value === 'department') {
    if (!allDepartments.value.length) {
      await loadAllDepartments()
    }
    linkDepartmentId.value = ''
  } else {
    linkDepartmentId.value = ''
  }
  linkPath.value = ''
  await loadLinkList()
}

const loadLinkList = async () => {
  if (linkSpaceType.value === 'department' && !linkDepartmentId.value) {
    linkItems.value = []
    return
  }
  linkLoading.value = true
  try {
    const params = {
      spaceType: linkSpaceType.value,
      path: linkPath.value || ''
    }
    if (linkSpaceType.value === 'department') {
      params.departmentId = linkDepartmentId.value
    }
    const { data } = await axios.get('/api/files/list', { params })
    // 过滤掉链接项（不显示现有链接）
    linkItems.value = (data.items || []).filter(it => !it._is_link)
  } catch (e) {
    console.error('loadLinkList failed', e)
    linkItems.value = []
    if (e.response && e.response.status === 403) {
      alert('空间未开放或无访问权限，请联系管理员')
    }
  } finally {
    linkLoading.value = false
  }
}

const linkGoRoot = async () => {
  linkPath.value = ''
  await loadLinkList()
}

const linkGoUp = async () => {
  if (!linkPath.value) return
  const parts = linkPath.value.split('/')
  parts.pop()
  linkPath.value = parts.join('/')
  await loadLinkList()
}

const onLinkDblClick = async (it) => {
  if (!it.is_dir) return
  const parts = linkPath.value ? linkPath.value.split('/') : []
  parts.push(it.name)
  linkPath.value = parts.join('/')
  await loadLinkList()
}

const onLinkNewFolder = async () => {
  const name = window.prompt('请输入新建文件夹名称：')
  if (!name) return
  try {
    const payload = {
      spaceType: linkSpaceType.value,
      departmentId: linkSpaceType.value === 'department' ? linkDepartmentId.value : null,
      path: linkPath.value || '',
      folderName: name,
    }
    await axios.post('/api/files/folder', payload)
    await loadLinkList()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '新建文件夹失败')
  }
}

const confirmLink = async () => {
  if (!selectedItems.value.length) return
  // 过滤掉链接项（不能链接链接）
  const itemsToLink = selectedItems.value.filter(it => !it._is_link)
  if (!itemsToLink.length) {
    alert('无法为链接创建链接')
    return
  }
  
  try {
    const srcPath = getApiPathForList()
    const payload = {
      items: itemsToLink.map((it) => ({
        spaceType: spaceType.value,
        departmentId: spaceType.value === 'department' ? departmentId.value : null,
        path: srcPath,
        name: it.name,
        is_dir: it.is_dir,
      })),
      targetSpaceType: linkSpaceType.value,
      targetDepartmentId: linkSpaceType.value === 'department' ? linkDepartmentId.value : null,
      targetPath: linkPath.value || '',
    }
    const { data } = await axios.post('/api/files/links', payload)
    showLink.value = false
    
    // 显示结果
    const successCount = (data.results || []).filter(r => r.success).length
    const failCount = (data.results || []).filter(r => !r.success).length
    if (failCount > 0) {
      const failMsgs = (data.results || []).filter(r => !r.success).map(r => `${r.name}: ${r.error}`).join('\n')
      alert(`创建链接完成：${successCount} 成功，${failCount} 失败\n\n失败详情：\n${failMsgs}`)
    } else {
      alert(`成功创建 ${successCount} 个链接`)
    }
    
    // 跳转到目标位置
    await goToPath(payload.targetSpaceType, payload.targetDepartmentId, payload.targetPath || '.')
  } catch (e) {
    const msg = (e.response && e.response.data && e.response.data.detail) || '创建链接失败'
    alert(msg)
  }
}

const headerCols = ref([
  { key: 'name', label: '名称', width: 260, min: 140 },
  { key: 'type', label: '类型', width: 50, min: 50 },
  { key: 'size', label: '大小', width: 90, min: 80 },
  { key: 'mtime', label: '修改时间', width: 80, min: 80 },
  { key: 'ops', label: '操作', width: 120, min: 120, isOps: true },
])

const resizing = ref({ active: false, index: -1, startX: 0, startWidth: 0, nextWidth: 0 })

const headerStyle = (index) => {
  const col = headerCols.value[index]
  return {
    width: col.width + 'px',
    maxWidth: col.width + 'px',
    minWidth: col.min + 'px',
    textAlign: col.isOps ? 'center' : 'left',
  }
}

const startResize = (e, index) => {
  const col = headerCols.value[index]
  const nextCol = headerCols.value[index + 1]
  if (col.isOps || !nextCol) return
  resizing.value = {
    active: true,
    index,
    startX: e.clientX,
    startWidth: col.width,
    nextWidth: nextCol.width,
  }
}

const onMouseMove = (e) => {
  if (!resizing.value.active) return
  const delta = e.clientX - resizing.value.startX
  const idx = resizing.value.index
  const col = headerCols.value[idx]
  const nextCol = headerCols.value[idx + 1]
  if (!nextCol) return

  const total = resizing.value.startWidth + resizing.value.nextWidth
  let newWidth = Math.max(col.min, resizing.value.startWidth + delta)
  let newNextWidth = total - newWidth
  if (newNextWidth < nextCol.min) {
    newNextWidth = nextCol.min
    newWidth = total - newNextWidth
  }
  col.width = newWidth
  nextCol.width = newNextWidth
}

const onMouseUp = () => {
  if (!resizing.value.active) return
  resizing.value = { active: false, index: -1, startX: 0, startWidth: 0, nextWidth: 0 }
}

const goToPath = async (space, deptId, path) => {
  pushHistory()  // 记录当前位置
  spaceType.value = space
  if (space === 'department') {
    await loadDepartments()
    departmentId.value = deptId && departments.value.some(d => d.id === deptId) ? deptId : ''
  } else {
    departmentId.value = ''
  }
  currentPath.value = path && path !== '' ? path : '.'
  inSearchMode.value = false
  searchResults.value = []
  selectedItems.value = []
  highlightName.value = ''
  preSelectedNames.value = []
  await loadList()
}

// 顶部工具栏（空间/部门 + 按钮）保持原样，不参与与面包屑的碰撞计算。
// 这里只保留占位函数，避免后续扩展时改动过大。
const updateTopRowLayout = () => {
  topRowCompact.value = false
}

// 第二行工具栏（导航 + 面包屑 + 搜索/分享等）布局调整：
// 1）先尝试在“正常按钮尺寸”下，按实际宽度逐步隐藏左侧目录，确保最后一级不会被右侧区域挡住；
// 2）当仅剩最后一级仍然放不下时，再将本行按钮切换为紧凑模式重新尝试；
// 3）如果在紧凑模式下仍然放不下，则不再强制收缩，允许右侧按钮整体向外溢出。
const updateSecondRowLayout = async () => {
  const rowEl = secondRow.value
  const rightEl = secondRight.value
  const navEl = navGroup.value
  const bcEl = breadcrumbContainer.value
  if (!rowEl || !rightEl || !navEl || !bcEl) return

  const crumbs = breadcrumbs.value
  const total = crumbs.length

  if (!total) {
    breadcrumbVisibleStart.value = 0
    secondRowCompact.value = false
    return
  }

  // 从“非紧凑模式 + 全部目录可见”开始
  secondRowCompact.value = false
  breadcrumbVisibleStart.value = 0
  await nextTick()

  // 工具函数：在当前按钮模式下，尽可能多隐藏左侧目录，直到不再溢出
  const shrinkBreadcrumbsToFit = async () => {
    let safety = 0
    while (safety < total) {
      const el = breadcrumbScroll.value || breadcrumbContainer.value
      if (!el) break
      const scrollWidth = el.scrollWidth
      const clientWidth = el.clientWidth

      // 不再溢出，停止收缩
      if (!clientWidth || scrollWidth <= clientWidth) break

      // 至少保留 2 层目录（如果总数本身小于 2，则保留全部）
      const minVisible = Math.min(2, total)
      const remaining = total - breadcrumbVisibleStart.value
      if (remaining <= minVisible) break

      breadcrumbVisibleStart.value += 1
      safety += 1
      await nextTick()
    }
  }

  await shrinkBreadcrumbsToFit()

  // 如果在正常按钮尺寸下，已经解决溢出，则直接结束
  {
    const el = breadcrumbScroll.value || breadcrumbContainer.value
    if (!el) return
    if (!el.clientWidth || el.scrollWidth <= el.clientWidth) {
      return
    }
  }

  // 尝试切换当前行按钮为紧凑模式（仅图标），再收缩一次
  secondRowCompact.value = true
  await nextTick()
  await shrinkBreadcrumbsToFit()

  // 紧凑模式下即使只剩最后一级仍然放不下，也不再强行调整，
  // 交由整体布局产生水平溢出，让按钮向右侧超出视口。
}

// 统一入口：根据当前窗口宽度、路径和按钮数量，动态调整两行工具栏布局
const updateToolbarLayout = () => {
  updateTopRowLayout()
  updateSecondRowLayout()
}

let resizeTimer = null
const handleResize = () => {
  if (resizeTimer) {
    clearTimeout(resizeTimer)
  }
  resizeTimer = setTimeout(() => {
    nextTick(() => {
      updateToolbarLayout()
    })
  }, 120)
}

const applyPreSelectionAndScroll = async () => {
  if (preSelectedNames.value && preSelectedNames.value.length && !inSearchMode.value) {
    const set = new Set(preSelectedNames.value)
    selectedItems.value = items.value.filter((it) => set.has(it.name)).map((it) => ({ ...it }))
  }
  await nextTick()
  if (!highlightName.value && (!preSelectedNames.value || !preSelectedNames.value.length)) return
  const wrapper = listWrapper.value
  if (!wrapper) return
  const row = wrapper.querySelector('tr.clickable.highlight')
  if (!row) return
  const rect = row.getBoundingClientRect()
  const wrapRect = wrapper.getBoundingClientRect()
  const offset = rect.top - wrapRect.top
  wrapper.scrollTop += offset - 40
}

const onShare = async () => {
  if (spaceType.value === 'safe') {
    alert('个人保险库不支持分享，请在公共或部门空间使用分享功能')
    return
  }
  const base = {
    spaceType: spaceType.value,
    departmentId: spaceType.value === 'department' ? departmentId.value : '',
    path: currentPath.value === '.' ? '' : currentPath.value,
  }
  const selected = selectedItems.value.map((it) => it.name)
  let anchorName = ''
  let selectedNames = []
  if (selected.length) {
    anchorName = selected[0]
    selectedNames = selected
  }

  try {
    // 1）先向后台创建分享短码 shareId
    const { data: shareResp } = await axios.post('/api/share', {
      spaceType: base.spaceType,
      departmentId: base.departmentId || null,
      path: base.path || '',
      anchorName,
      selectedNames,
    })
    const shareId = shareResp.shareId
    // 使用短码构造精简链接（不再在 URL 中携带所有文件名等长参数）
    const link = `${window.location.origin}/#/files?shareId=${encodeURIComponent(shareId)}`

    // 构造更友好的分享文案
    const count = selectedNames.length
    const titlePart = count === 0
      ? '一些文件/文件夹'
      : count === 1
        ? `文件“${anchorName}”`
        : `共 ${count} 个文件/文件夹，例如“${anchorName}”等`
    const shareText = [
      '我在 HBCloud 河北分院网盘分享了新的文件：',
      titlePart,
      '',
      '请在内网环境登录系统后使用本链接。',
      '',
      link,
    ].join('\n')

    // 2）记录分享审计日志（保持原有格式不变）
    try {
      await axios.post('/api/audit/share', {
        spaceType: base.spaceType,
        departmentId: base.departmentId || null,
        path: base.path || '',
        anchorName,
        selectedNames,
      })
    } catch (e) {
      console.error('record share audit failed', e)
      // 审计失败不影响分享链接复制
    }

    // 3）复制分享文案+短链接
    const ok = await copyToClipboard(shareText)
    if (ok) {
      alert('已复制分享说明及链接，可直接粘贴发送给同事')
    } else {
      alert('复制失败，请手动复制地址栏或联系管理员')
    }
  } catch (e) {
    console.error('create share failed', e)
    alert((e.response && e.response.data && e.response.data.detail) || '创建分享失败，请稍后重试')
  }
}

// 收藏路径相关逻辑
const favoriteVisible = ref(false)
const favoriteList = ref([])

const loadFavorites = async () => {
  try {
    const { data } = await axios.get('/api/files/favorites')
    favoriteList.value = data || []
  } catch (e) {
    console.error('loadFavorites failed', e)
  }
}

const toggleFavoritePanel = async () => {
  if (favoriteVisible.value) {
    favoriteVisible.value = false
    return
  }
  favoriteVisible.value = true
  await loadFavorites()
}

const openFavoritePanel = async () => {
  favoriteVisible.value = true
  await loadFavorites()
}

const describeSpace = (fav) => {
  if (fav.spaceType === 'public') return '公共空间'
  if (fav.spaceType === 'department') return `部门空间${fav.departmentId ? ' / ' + fav.departmentId : ''}`
  if (fav.spaceType === 'safe') return '个人保险库'
  return fav.spaceType
}

const lastSegment = (p) => {
  if (!p || p === '.' || p === '/') return ''
  const parts = p.split('/').filter(Boolean)
  return parts[parts.length - 1] || ''
}

const goFavorite = (fav) => {
  // 如果当前不在文件浏览页，先路由跳转并把目标作为 query 传入，FileBrowser 在 mounted 时会处理该 query
  if (!route.name || route.name !== 'Files') {
    router.push({ path: '/files', query: { fav_space: fav.spaceType, fav_dept: fav.departmentId || '', fav_path: fav.path || '.', fav_open: '1', fav_name: lastSegment(fav.path) } })
  } else {
    // 已在文件页，直接切换路径
    goToPath(fav.spaceType, fav.departmentId || null, fav.path || '.')
    // 仅打开详情弹窗（不预选目标文件/文件夹）
    detailFile.value = null
    detailVisible.value = true
  }
  // 点击收藏后关闭快速访问弹窗
  favoriteVisible.value = false
}

const canAddFavorite = computed(() => {
  if (selectedItems.value.length === 0) return true
  return selectedItems.value.every((it) => it.is_dir)
})

const addCurrentOrSelectedToFavorite = async () => {
  try {
    if (!selectedItems.value.length) {
      // 收藏当前目录
      await axios.post('/api/files/favorites', {
        spaceType: spaceType.value,
        departmentId: spaceType.value === 'department' ? departmentId.value : null,
        path: getApiPathForList(),
        displayName: '',
      })
    } else {
      // 仅收藏选中的文件夹
      for (const it of selectedItems.value) {
        if (!it.is_dir) continue
        const base = currentPath.value && currentPath.value !== '.' ? currentPath.value + '/' : ''
        const p = base + it.name
        await axios.post('/api/files/favorites', {
          spaceType: spaceType.value,
          departmentId: spaceType.value === 'department' ? departmentId.value : null,
          path: p,
          displayName: it.name,
        })
      }
    }
    await loadFavorites()
    alert('已添加到快速访问')
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '添加失败')
  }
}

const removeFavorite = async (fav) => {
  if (!window.confirm('确认从快速访问中移除此路径？')) return
  try {
    await axios.delete('/api/files/favorites', {
      data: {
        spaceType: fav.spaceType,
        departmentId: fav.departmentId,
        path: fav.path,
      },
    })
    await loadFavorites()
  } catch (e) {
    alert((e.response && e.response.data && e.response.data.detail) || '移除失败')
  }
}

// 监听来自 App.vue 的打开事件
const onOpenFavorites = () => {
  toggleFavoritePanel()
}

onMounted(async () => {
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  window.addEventListener('hbcloud-open-favorites', onOpenFavorites)
  window.addEventListener('resize', handleResize)
  loadCurrentUser()
  if (window && window.__hbcloud_refresh_user__) {
    window.__hbcloud_refresh_user__()
  }
  await loadSpaces()

  const { qSpaceType, qDeptId, qPath, qName, qSelected, qShareId } = parseFileBrowserQuery(route)

  // 1）如存在 shareId，则优先根据 shareId 还原分享上下文
  if (qShareId) {
    try {
      const { data } = await axios.get(`/api/share/${encodeURIComponent(qShareId)}`)
      // data: { shareId, spaceType, departmentId, path, anchorName, selectedNames }
      spaceType.value = data.spaceType || 'public'
      if (spaceType.value === 'department') {
        await loadDepartments()
        if (data.departmentId && departments.value.some((d) => d.id === data.departmentId)) {
          departmentId.value = data.departmentId
        } else {
          departmentId.value = ''
        }
      } else {
        departmentId.value = ''
      }
      if (spaceType.value === 'safe') {
        // 出于安全考虑，禁止通过分享链接直接打开个人保险库
        alert('分享链接指向的是个人保险库内容，已自动切换为公共空间根目录。')
        spaceType.value = 'public'
        currentPath.value = '.'
      }

      // 根据分享数据设置路径或高亮
      if (!data.anchorName && !(data.selectedNames && data.selectedNames.length)) {
        // 未指定锚点或选中项：直接进入目录
        currentPath.value = data.path && data.path !== '' ? data.path : '.'
        highlightName.value = ''
        preSelectedNames.value = []
      } else {
        currentPath.value = data.path && data.path !== '' ? data.path : '.'
        highlightName.value = data.anchorName || ''
        preSelectedNames.value = Array.isArray(data.selectedNames) ? data.selectedNames : []
      }

      await loadList()
      await loadAllDepartments()
      await applyPreSelectionAndScroll()

      // 使用一次后清理地址栏中的 shareId，避免后续刷新重复请求
      if (!hasAppliedShareRedirect) {
        hasAppliedShareRedirect = true
        router.replace({ path: '/files', query: {} })
      }
      return
    } catch (e) {
      console.error('load share by shareId failed', e)
      alert('分享链接已失效或不存在，请联系分享人重新生成。')
      // 继续走原有 qSpaceType 等逻辑，回退到普通浏览
    }
  }

  // 2）兼容旧版本：使用 URL 中的空间/路径/名称参数
  // 处理快速访问传入的 fav_* query（外部点击快速访问会跳转到 /files?fav_space=... ）
  if (route.query && (route.query.fav_space || route.query.fav_path)) {
    try {
      const fq = route.query || {}
      const s = fq.fav_space || 'public'
      const d = fq.fav_dept || ''
      const p = fq.fav_path || '.'
      await goToPath(s, d || null, p || '.')
      if (fq.fav_open) {
        // 仅打开详情弹窗，不预选任何目标文件/文件夹
        detailFile.value = null
        detailVisible.value = true
      }
      router.replace({ path: route.path, query: {} })
    } catch (e) {
      // ignore
    }
  }

  // 处理通过路由 query 请求打开快速访问面板的情况
  if (route.query && route.query.fav_panel) {
    try {
      // 打开快速访问面板并加载数据
      await openFavoritePanel()
      // 清理 query
      router.replace({ path: route.path, query: {} })
    } catch (e) {
      // ignore
    }
  }
  spaceType.value = qSpaceType
  if (spaceType.value === 'department') {
    await loadDepartments()
    if (qDeptId && departments.value.some((d) => d.id === qDeptId)) {
      departmentId.value = qDeptId
    }
  }
  if (spaceType.value === 'safe') {
    ensureSafePathForUser()
  } else {
    currentPath.value = qPath || '.'
  }
  highlightName.value = qName || ''
  preSelectedNames.value = qSelected || []

  await loadList()
  await loadAllDepartments()
  await applyPreSelectionAndScroll()

  // 初始加载完成后，根据实际宽度计算一次工具栏布局
  updateToolbarLayout()

  if (!hasAppliedShareRedirect && (qName || (qSelected && qSelected.length))) {
    hasAppliedShareRedirect = true
    router.replace({ path: '/files', query: {} })
  }
})

watch(
  () => route.fullPath,
  () => {
    // 分享 URL 在首次 onMounted 中解析并高亮后会被 replace 掉
    // 这里不再根据 URL 变更去覆盖 highlightName / preSelectedNames，
    // 以避免地址栏被清理后高亮状态丢失。
  }
)

// 当路径层级变化时，重置面包屑起始位置，并根据最新宽度重新计算布局
watch(
  () => breadcrumbs.value.join('/'),
  () => {
    breadcrumbVisibleStart.value = 0
    nextTick(() => {
      updateSecondRowLayout()
    })
  }
)

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('hbcloud-open-favorites', onOpenFavorites)
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.file-browser {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative; /* 让左侧局部弹窗定位在文件列表区域 */
}

/* 包一层主体，方便用 @click.self 关闭弹窗 */
.file-browser-body {
  position: relative;
  flex: 1;
  height: 100%;
  overflow: auto;
}

/* 固定工具栏 */
.toolbar-sticky {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #fff;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 0.5rem;
}

.toolbar-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
  flex-wrap: nowrap;
  gap: 0.5rem;
  width: 100%;
}

.top-row {
  margin-bottom: 0.5rem;
}

.second-row {
  margin-bottom: 0.75rem;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.toolbar-left.second-left {
  flex: 1 1 auto;
  flex-shrink: 1;
  min-width: 0;
  overflow: hidden;
  gap: 0.5rem;
}

.second-left .nav-btn {
  flex-shrink: 0;
}

.toolbar-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.second-right {
  flex-shrink: 0;
}

.field {
  display: flex;
  align-items: center;
  font-size: 0.9rem;
}

.field-label {
  margin-right: 0.25rem;
}

.select-basic {
  min-width: 120px;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #e5e7eb;
  color: #111827;
  font-size: 0.9rem;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: nowrap;
  flex-shrink: 0;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  min-width: auto;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #6b7280;
  background-color: #f9fafb;
  color: #111827;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  height: 2rem;
}

.btn-icon {
  font-size: 1rem;
  line-height: 1;
}

.btn-text {
  font-size: 0.85rem;
}

.btn:hover:enabled {
  background-color: #e5e7eb;
  border-color: #4b5563;
}

.btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  background-color: #f3f4f6;
  color: #9ca3af;
  border-color: #d1d5db;
}

.btn-danger {
  border-color: #dc2626;
  color: #dc2626;
  background-color: #fef2f2;
}

.btn-danger:hover:enabled {
  background-color: #fee2e2;
  border-color: #b91c1c;
}

.btn-danger:disabled {
  opacity: 0.35;
  color: #f87171;
  border-color: #fecaca;
  background-color: #fef2f2;
}

.icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #e5e7eb;
  font-size: 0.9rem;
  cursor: pointer;
}

.icon-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

/* 导航按钮统一样式 */
.nav-btn {
  width: 28px;
  height: 28px;
  min-width: 28px;
  border-radius: 4px;
  border: 1px solid #6b7280;
  background: linear-gradient(180deg, #ffffff 0%, #f3f4f6 100%);
  font-size: 12px;
  font-weight: bold;
  color: #374151;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  line-height: 1;
  padding: 0;
}

.nav-btn:hover:enabled {
  background: linear-gradient(180deg, #f9fafb 0%, #e5e7eb 100%);
  border-color: #4b5563;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.nav-btn:active:enabled {
  background: #e5e7eb;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.1);
}

.nav-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  background: #f3f4f6;
  color: #9ca3af;
  border-color: #d1d5db;
}

.nav-group {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.search-bar .select-wrapper {
  padding: 0.2rem 0.75rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  min-width: 260px;
}

.search-bar input {
  border: none;
  outline: none;
  background-color: transparent;
  color: #111827;
  font-size: 0.9rem;
}

.path {
  font-size: 0.85rem;
  color: #6b6e75;
}

/* 面包屑导航样式 */
.breadcrumb-container {
  flex: 1 1 0;
  min-width: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding-right: 4px; /* 与右侧按钮之间保持一个“缓冲区”，避免视觉碰撞 */
}

.breadcrumb-scroll {
  display: flex;
  align-items: center;
  overflow: hidden;
  width: 100%;
}

.breadcrumb-btn {
  background: #e5e7eb;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 0.15rem 0.5rem;
  font-size: 0.8rem;
  color: #374151;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background-color 0.15s, color 0.15s;
}

.breadcrumb-btn:hover {
  background: #d1d5db;
  color: #111827;
}

.breadcrumb-btn.root-btn {
  padding: 0.15rem 0.35rem;
  font-weight: bold;
}

.breadcrumb-btn.current-crumb {
  background: #7c9dd5;
  color: #111827;
  font-weight: 500;
  cursor: default;
}

.breadcrumb-sep {
  color: #9ca3af;
  font-size: 0.8rem;
  margin: 0 0.15rem;
  flex-shrink: 0;
}

.breadcrumb-ellipsis {
  font-size: 0.8rem;
  color: #6b7280;
  padding: 0.15rem 0.3rem;
  white-space: nowrap;
  flex-shrink: 0;
}

.second-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.8rem;
  flex-shrink: 0;
}

/* 行级紧凑模式：仅显示图标，隐藏文字，减小按钮占宽度 */
.toolbar-row.compact-row .btn-text {
  display: none;
}

.toolbar-row.compact-row .btn {
  min-width: 2rem;
  width: 2rem;
  padding: 0.3rem;
}

.ops-head {
  width: 170px;
  max-width: 170px;
  min-width: 170px;
  text-align: center;
}

.ops-cell {
  text-align: right;
  white-space: nowrap;
}

.op-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  margin-left: 0.15rem;
  border-radius: 4px;
  border: 1px solid #9ca3af;
  background-color: #e5e7eb;
  color: #111827;
  font-size: 0.78rem;
  cursor: pointer;
}

.op-icon-btn.op-danger {
  border-color: #fca5a5;
  color: #b91c1c;
}

.op-icon-btn:hover {
  background-color: #d1d5db;
}

.th-label {
  position: relative;
  padding-right: 4px;
}

.col-resizer {
  position: absolute;
  top: 4px;
  bottom: 4px;
  right: 0;
  width: 6px;
  cursor: col-resize;
  user-select: none;
}

.col-resizer::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 2.5px;
  width: 1px;
  background-color: #d1d5db;
}

.file-list th {
  position: relative;
}

.file-list table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  background-color: #ffffff;
}

.file-list th,
.file-list td {
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.9rem;
}

.file-list th:first-child,
.file-list td:first-child {
  text-align: center;
  padding-right: 0.25rem;
}

.file-list td:nth-child(2) {
  text-align: left;
}

.clickable {
  cursor: pointer;
}

.clickable:hover {
  background-color: #f3f4f6;
}

.file-list .name {
  margin-left: 0.3rem;
}

.empty,
.loading {
  text-align: center;
  color: #6b7280;
}

.op-btn {
  display: inline-block;
  margin-left: 5px;
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

.image-preview-mask {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.image-preview-dialog {
  max-width: 80vw;
  max-height: 80vh;
  background-color: #111827;
  padding: 0.5rem;
  border-radius: 4px;
}

.image-preview-dialog img {
  max-width: 100%;
  max-height: 80vh;
  display: block;
}

.upload-mask {
  position: fixed;
  inset: 0;
  background-color: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.upload-dialog {
  min-width: 260px;
  max-width: 360px;
  background-color: #ffffff;
  border-radius: 4px;
  padding: 12px 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
}

.upload-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
}

.upload-tip {
  font-size: 12px;
  color: #6b7280;
}

.upload-progress-bar {
  margin-top: 6px;
  width: 100%;
  height: 6px;
  background-color: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
}

.upload-progress-inner {
  height: 100%;
  background-color: #2563eb;
  transition: width 0.2s ease;
}

.upload-progress-text {
  margin-top: 4px;
  font-size: 12px;
  color: #374151;
  text-align: right;
}

.move-mask {
  position: fixed;
  inset: 0;
  background-color: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 998;
}

.move-dialog {
  width: 720px;
  max-height: 80vh;
  background-color: #ffffff;
  border-radius: 4px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
  padding: 12px 16px 10px;
  display: flex;
  flex-direction: column;
}

.move-header {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.move-body {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.move-list {
  margin-top: 6px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  /* 关键：限制高度并启用滚动 */
  max-height: 320px;
  overflow-y: auto;
}

.move-footer {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.move-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.overwrite-group {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #4b5563;
}

.overwrite-title {
  font-weight: 500;
}

.overwrite-option {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  border: 1px solid transparent;
  cursor: pointer;
}

.overwrite-option.active {
  border-color: #2563eb;
  background-color: #eff6ff;
  color: #1d4ed8;
}

.overwrite-option input[type='radio'] {
  margin: 0;
}

.overwrite-tip {
  margin: 4px 0 2px;
  font-size: 12px;
  color: #b91c1c;
}

.link-tip {
  margin: 0 0 10px;
  padding: 8px 12px;
  font-size: 12px;
  color: #1e40af;
  background: #eff6ff;
  border-radius: 4px;
  border-left: 3px solid #3b82f6;
}

.move-row.move-target-row {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 6px;
}

.move-field {
  display: flex;
  flex-direction: column;
}

.select-sm {
  height: 30px;
  padding: 4px 8px;
  font-size: 13px;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 13px;
}

.btn-icon.btn-sm {
  height: 30px;
  min-width: 60px;
}

.move-list table {
  width: 100%;
  border-collapse: collapse;
}

.move-list th,
.move-list td {
  padding: 0.35rem 0.5rem;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.9rem;
}

.move-list tr.dir {
  cursor: pointer;
}

.move-list tr.dir:hover {
  background-color: #f3f4f6;
}

.detail-panel {
  position: fixed;
  top: 3.2rem;
  right: 0;
  bottom: 0;
  width: 260px;
  background-color: #ffffff;
  border-left: 1px solid #e5e7eb;
  box-shadow: -4px 0 10px rgba(15, 23, 42, 0.08);
  padding: 10px 12px;
  z-index: 900;
}

.detail-overlay {
  position: fixed;
  top: 3.2rem;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 899;
}

.detail-mask {
  position: absolute;
  inset: 0 260px 0 0; /* mask covers the page left of the panel */
  background: rgba(0,0,0,0.03);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.detail-title {
  font-size: 14px;
  font-weight: 600;
}

.detail-close {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
}

.detail-body {
  font-size: 12px;
  color: #374151;
}

.detail-row {
  margin-bottom: 4px;
}

.detail-row .k {
  color: #6b7280;
}

.detail-row .v {
  margin-left: 4px;
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

/* 弹窗淡入淡出 0.15s，统一到全局使用 */
.fade-dialog-enter-active,
.fade-dialog-leave-active {
  transition: opacity 0.15s ease;
}
.fade-dialog-enter-from,
.fade-dialog-leave-to {
  opacity: 0;
}

/* 任务遮罩淡入淡出 0.15s */
.fade-task-enter-active,
.fade-task-leave-active {
  transition: opacity 0.15s ease;
}
.fade-task-enter-from,
.fade-task-leave-to {
  opacity: 0;
}

.clickable.highlight {
  background-color: #fef3c7;
}

.content {
  flex: 1 1 auto;
  overflow: auto;
}

.fav-panel {
  /* 原样保持你现在的位置和大小设置，只把 absolute 换成 fixed */
  position: fixed;
  top: 4rem;   /* 与页面头部对齐，保持现在的纵向位置 */
  bottom: 10px;     /* 占满头部以下的高度 */
  left: 210px;   /* 保持当前在左侧边栏右侧的位置（侧边栏宽度是 260px） */
  width: 260px;
  background: #111827;           /* 贴近侧边栏底色 */
  color: #e5e7eb;
  border-right: 1px solid #1f2937;
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  z-index: 20;
  border-radius: 6px; /* 新增：给快速访问弹窗加圆角 */
}

.fav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid #1f2937;
  font-size: 0.95rem;
  font-weight: 500;
}

.fav-toolbar {
  display: flex;
  gap: 0.4rem;
  padding: 0.4rem 0.8rem;
  border-bottom: 1px solid #1f2937;
}

.fav-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.4rem 0.6rem 0.6rem;
}

/* 其余样式保持原来的，只是背景/文字颜色略调，与侧边栏接近 */
.fav-item {
  display: flex;
  align-items: center;
  padding: 0.35rem 0.3rem;
  border-radius: 4px;
  transition: background-color 0.15s ease;
}

.fav-item:hover {
  background-color: #1f2937;
}

.fav-main {
  flex: 1;
  cursor: pointer;
}

.fav-name {
  font-size: 0.9rem;
  color: #f9fafb;
}

.fav-meta {
  font-size: 0.75rem;
  color: #9ca3af;
}

.pin-btn {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 0.9rem;
  color: #e5e7eb;
}

.fav-empty {
  margin-top: 0.8rem;
  font-size: 0.8rem;
  color: #9ca3af;
}

/* 左侧弹出动画，从左侧轻微滑入/出 */
.fade-fav-enter-active,
.fade-fav-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.fade-fav-enter-from,
.fade-fav-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* 响应式：窄屏时隐藏按钮文字，只显示图标 */
@media (max-width: 1200px) {
  .btn-text {
    display: none;
  }
  .btn {
    min-width: 2rem;
    width: 2rem;
    padding: 0.3rem;
  }
  .search-bar input {
    width: 100px;
  }
}

@media (max-width: 900px) {
  .search-bar input {
    width: 80px;
  }
  .breadcrumb-container {
    min-width: 40px;
  }
}
</style>
