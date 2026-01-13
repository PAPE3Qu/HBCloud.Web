<template>
  <div class="help-layout">
    <!-- 左侧：目录 -->
    <aside class="help-nav">
      <div class="help-nav-title">帮助中心</div>

      <div class="help-nav-group">
        <button class="help-nav-toggle" type="button" @click="toggleGroup('getting-started')">
          <span class="caret" :class="{ open: openGroups['getting-started'] }">▸</span>
          <span class="text">快速上手</span>
        </button>
        <div v-show="openGroups['getting-started']" class="help-nav-items">
          <button
            v-for="it in navGroups.gettingStarted"
            :key="it.id"
            type="button"
            class="help-nav-item"
            :class="{ active: activeId === it.id }"
            @click="select(it.id)"
          >
            {{ it.title }}
          </button>
        </div>
      </div>

      <div class="help-nav-group">
        <button class="help-nav-toggle" type="button" @click="toggleGroup('file-ops')">
          <span class="caret" :class="{ open: openGroups['file-ops'] }">▸</span>
          <span class="text">文件与回收站</span>
        </button>
        <div v-show="openGroups['file-ops']" class="help-nav-items">
          <button
            v-for="it in navGroups.fileOps"
            :key="it.id"
            type="button"
            class="help-nav-item"
            :class="{ active: activeId === it.id }"
            @click="select(it.id)"
          >
            {{ it.title }}
          </button>
        </div>
      </div>

      <div class="help-nav-group">
        <button class="help-nav-toggle" type="button" @click="toggleGroup('more')">
          <span class="caret" :class="{ open: openGroups.more }">▸</span>
          <span class="text">更多功能</span>
        </button>
        <div v-show="openGroups.more" class="help-nav-items">
          <button
            v-for="it in navGroups.more"
            :key="it.id"
            type="button"
            class="help-nav-item"
            :class="{ active: activeId === it.id }"
            @click="select(it.id)"
          >
            {{ it.title }}
          </button>
        </div>
      </div>
    </aside>

    <!-- 右侧：阅读区 -->
    <main class="help-content">
      <div class="help-content-inner">
        <div class="help-breadcrumb">
          <span class="crumb">帮助中心</span>
          <span class="sep">/</span>
          <span class="crumb strong">{{ activeTitle }}</span>
        </div>

        <article class="md" v-html="renderedHtml"></article>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const docs = [
  {
    id: 'intro',
    group: 'getting-started',
    title: '概览',
    md: `# HBCloud 开放网盘使用帮助

欢迎使用 **HBCloud 河北分院开放网盘**。

这里汇总了日常最常见的操作方式与注意事项，帮助你更快完成：**上传、下载、共享、整理、找回误删文件**。

> **重要**：请优先使用系统内的「移动/重命名/删除」等功能进行管理，避免在系统外直接改动文件位置，否则可能导致统计信息与附件引用不一致。
`,
  },
  {
    id: 'account',
    group: 'getting-started',
    title: '登录与账号',
    md: `# 登录与账号

## 登录
- 使用 **手机号 + 密码** 登录。
- 右上角点击 **登出** 可退出当前账号。

## 注册与修改密码
- 初次使用可在登录页通过邀请码完成注册（如业务已开放）。
- 支持在登录页入口进行 **修改密码**。

## 常见问题
- **连续输错密码多次**：账号可能会暂时锁定，稍后再试或联系管理员。
- **提示登录过期**：重新登录即可继续使用。
`,
  },
  {
    id: 'spaces',
    group: 'getting-started',
    title: '空间说明',
    md: `# 空间说明

系统提供三类空间，满足不同共享与隐私需求：

## 公共空间
用于全院共享的制度、模板、流程等资料。

## 部门空间
用于部门内部协作的资料区，每个部门有独立目录。

## 个人保险库
按手机号划分的个人私有空间，通常仅本人可见，适合存放与个人相关或较敏感的工作资料。

## 如何切换空间
在「文件浏览」页面顶部可切换空间类型；选择部门空间时，需要再选择具体部门。
`,
  },
  {
    id: 'permission-matrix',
    group: 'getting-started',
    title: '权限与角色（矩阵）',
    md: `# 权限与角色（矩阵）

本节以“你在页面上能做什么”为主，帮助你判断：为什么看得到/看不到、为什么能改/不能改。

---

## 一、你会遇到的几类身份（用户视角）

> 说明：系统里存在“系统管理员 / 运维管理员 / 普通用户”等不同角色；
> 在用户帮助里我们只用“管理员/普通用户/部门管理员/部门成员”的说法，便于理解。

- **普通用户**：默认账号。
- **部门成员**：被加入到某个部门空间后，能在该部门空间内读写。
- **部门管理员**：除了读写，还能在“空间权限”里管理本部门成员（把同事加入/移出部门成员）。
- **管理员**：对全局拥有更高权限（例如能访问更多空间、处理更复杂的维护类操作）。

> **重要**：权限以“空间”为单位生效。你在公共空间可做的事，不等于你在部门空间也可以；反过来也一样。

---

## 二、空间与权限的关系（先记住这三条）

1. **公共空间**：面向全院共享，通常“人人可看”。
2. **部门空间**：分部门管理。是否能进入，和该部门空间是否“开放”有关。
3. **个人保险库**：通常只有自己能看到。

---

## 三、详尽矩阵：读/写/管理能力

### 1) 公共空间（Public）

| 你处于公共空间时 | 普通用户 | 部门成员/部门管理员 | 管理员 |
|---|---:|---:|---:|
| 浏览目录、搜索、打开文件夹 | ✅ | ✅ | ✅ |
| 下载单个文件 / 打包下载 | ✅ | ✅ | ✅ |
| 上传、新建文件夹、重命名、移动、复制、删除 | ✅（按当前系统开放口径） | ✅ | ✅ |

> **提示**：如果未来某天公共空间“写入”被收紧，你会看到相关按钮变灰或提示无权限——这属于管理员配置策略。

### 2) 部门空间（Department）

部门空间多一个关键开关：**是否开放（开放/非开放）**。

#### A. 部门空间：读取（能不能进、能不能看）

| 部门空间读取 | 普通用户（非本部门成员） | 本部门成员/本部门管理员 | 管理员 |
|---|---:|---:|---:|
| 当部门空间为“开放” | ✅ 可浏览/下载 | ✅ 可浏览/下载 | ✅ 可浏览/下载 |
| 当部门空间为“非开放” | ❌ 看不到/进不去 | ✅ 可浏览/下载 | ✅ 可浏览/下载 |

#### B. 部门空间：写入（能不能上传/删除/移动等）

| 部门空间写入 | 普通用户（非本部门成员） | 本部门成员/本部门管理员 | 管理员 |
|---|---:|---:|---:|
| 上传 / 新建 / 重命名 / 移动 / 复制 / 删除 / 压缩解压 | ❌ | ✅ | ✅ |

> **结论**：
> - 你在部门空间“能写”的前提，通常是 **你属于该部门**（成员或部门管理员）。
> - “是否开放”更多影响 **能不能看**，不影响部门成员的写入能力。

### 3) 个人保险库（Safe）

| 个人保险库 | 普通用户 | 部门成员/部门管理员 | 管理员 |
|---|---:|---:|---:|
| 浏览、上传、重命名、删除、移动、复制、压缩解压 | ✅（仅自己） | ✅（仅自己） | ✅（通常可处理全部，但一般不建议依赖） |

---

## 四、回收站权限（很重要）

| 回收站操作 | 谁可以看到 | 谁可以还原 | 谁可以彻底删除 |
|---|---|---|---|
| 公共空间删除的文件/文件夹 | 一般登录用户可见 | 对目标空间有写权限的人 | 对目标空间有写权限的人 |
| 部门空间删除的文件/文件夹 | 视部门权限而定 | 必须对该部门空间有写权限 | 必须对该部门空间有写权限 |
| 个人保险库删除的内容 | 通常仅自己可见 | 通常仅自己可还原 | 通常仅自己可彻底删除 |

> **重要**：
> - **还原**：是把内容放回原位置（或冲突时自动改名）。
> - **彻底删除**：是永久删除，**不可恢复**。

---

## 五、常见“为什么我不能/看不到”的例子（带英文提示对照）

> 下面列出一些高频情况，看到类似英文提示时，可以按对应方式处理。

### 例 1：看不到某个部门空间 / 点进去提示无权限
- 可能原因：该部门空间是“非开放”，而你 **不是该部门成员/管理员**。
- 你会看到的现象：进入时报错或列表为空。
- 处理方式：联系该部门管理员把你加入部门成员。

### 例 2：能看部门空间，但“上传/删除/重命名”按钮不可用
- 可能原因：你不是该部门成员。
- 处理方式：联系部门管理员。

### 例 3：回收站里看到文件，但点“还原”提示失败
- 可能原因：你对“还原目标空间”没有写权限（例如部门空间）。
- 处理方式：联系部门管理员或管理员协助还原。

### 例 4：个人保险库里找不到同事的文件
- 正常现象：个人保险库通常 **只能看到自己的**。
- 处理方式：需要共享时，把文件复制到公共空间或部门空间再共享。

` ,
  },
  {
    id: 'file-browser',
    group: 'file-ops',
    title: '文件浏览与常用操作',
    md: `# 文件浏览与常用操作

本节按“从进入页面到完成一次协作”的思路组织。

---

## 1. 导航与目录
- **双击文件夹**：进入下级目录
- 顶部 **首页**：回到当前空间根目录
- 顶部 **上级**：返回上一级目录
- 顶部 **当前路径**：用于确认自己所在位置（避免误操作）

> 建议：在执行“移动/删除/覆盖”前，先确认一次当前路径。

---

## 2. 上传（最常用）

### 上传前先确认
- 你是否在正确的空间（公共/部门/个人）
- 你是否进入了正确的目标文件夹

### 上传后你会看到什么
- 文件出现在列表中
- 文件“详情”里会记录最近编辑信息

### 大文件上传
- 大文件会自动分片上传，期间请不要关闭页面
- 若网络中断，可重新选择文件再次上传（系统会尽量减少重复上传）

---

## 3. 整理：新建文件夹 / 重命名

- **新建文件夹**：用于按项目、日期、部门进行归档
- **重命名**：建议使用规范命名，例如：\`2025-12-医务科-制度修订-v2.docx\`

---

## 4. 移动到 / 复制到（跨空间协作）

- **移动到**：把原文件“搬家”，原位置不再保留。
- **复制到**：生成一份副本，原位置仍保留。

### 常见使用场景
- 想让全院可见：复制到 **公共空间**
- 想让部门内部协作：移动或复制到 **部门空间**
- 想做个人备份：复制到 **个人保险库**

> 提示：移动/复制完成后，系统会自动跳转到目标位置，方便你立刻核对结果。

---

## 5. 固定到快速访问（收藏常用目录）

> 适合经常来回进入同一个目录的人，例如：某个部门固定的“制度文档”文件夹。

- 左侧有一个「快速访问」区域，用于展示你收藏的常用目录；
- 当你浏览到某个目录时，可以通过页面中的按钮/菜单，把当前目录“固定到快速访问”；
- 固定之后：
  - 该目录会出现在左侧列表中；
  - 下次点击即可一键跳转到该目录，无需一层层打开；
- 如不再需要某个收藏目录，可以在快速访问区域取消固定，仅从列表移除，不会删除目录里的文件。

---

## 6. 压缩、解压与打包下载

- **压缩**：把多个文件打成 ZIP，适合对外转交或归档
- **解压**：对 ZIP 解压，注意同名文件是否覆盖
- **打包下载**：勾选多个文件/文件夹后下载为一个 ZIP

> 提示：打包下载需要一定时间生成压缩包，请耐心等待。
`,
  },
  {
    id: 'recycle',
    group: 'file-ops',
    title: '回收站与删除恢复',
    md: `# 回收站与删除恢复

删除相关操作分两步：

1. **删除（移入回收站）**：可恢复
2. **彻底删除（回收站内执行）**：不可恢复

---

## 1) 删除（移入回收站）
在文件浏览页面点击 **删除** 后，内容会先进入回收站。

> **重要**：删除部门属于高风险操作；删除文件/文件夹相对安全，因为还能在回收站找回。

---

## 2) 回收站里能做什么

### 还原
- 将内容恢复到原空间与原路径
- 若原位置已有同名内容，系统会自动改名：
  - \`名称(恢复)\`
  - \`名称(恢复-2)\`、\`(恢复-3)\` ...

### 彻底删除
- 永久删除，**不可恢复**
- 建议仅在：确认不需要、或清理临时文件时使用

---

## 3) 还原失败的常见原因
- 你对目标空间没有写权限（尤其是部门空间）
- 原路径已不存在且无法自动创建（极少见）

处理方式：
- 联系部门管理员或管理员协助操作
`,
  },
  {
    id: 'file-stats',
    group: 'more',
    title: '文件详情与统计',
    md: `# 文件详情与统计

在文件列表中点击某个文件的 **详情**，可查看：

- 下载次数
- 最近访问时间
- 最近编辑人 / 编辑时间

## 统计更新规则（用户视角）
- 下载（含打包下载）会增加下载次数并更新最近访问时间
- 上传、重命名、移动、复制、从回收站还原等会更新最近编辑信息

> **提示**：仅“移入回收站”不会立即清空统计；彻底删除后相关信息会被移除。
`,
  },
  {
    id: 'home-posts',
    group: 'more',
    title: '首页动态与附件',
    md: `# 首页动态与附件（详解）

首页的「动态」用于发布公告、通知、更新说明等内容，并可附带文件作为附件，方便同事一键下载。

---

## 1. 浏览动态

在首页你可以：
- 查看动态列表（标题、发布人、发布时间、正文摘要）
- 展开查看正文全文
- 查看附件列表，并对附件进行下载或打包下载（如提供该入口）

### 常见阅读方式建议
- 想快速定位：先选择部门空间，再看标题与发布时间
- 想下载资料：先确认附件是否来自你有权限访问的空间（公共/部门）

---

## 2. 发布动态（谁能发布）

通常情况下：
- **普通用户**：是否允许发布取决于管理员开放策略；
- **管理员/部门管理员**：一般可以发布。

> 若你在首页看不到“发布动态/新增动态”的入口，通常表示你当前账号没有发布权限。

### 发布动态的基本步骤
1. 点击「发布动态」或「新增」
2. 填写 **标题**（建议简洁明确）
3. 填写 **正文**（可包含要点、时间、联系人等）
4. （可选）选择 **所属部门/可见范围**（若系统提供该选项）
5. 选择 **附件**（见下节）
6. 点击「发布」

### 标题与正文的写法建议（不冗余、易检索）
- 标题建议包含：\`[部门/主题] + 事项 + 日期\`
  - 例：\`[医务科] 12月制度修订说明（2025-12-27）\`
- 正文建议分点：背景、变更点、执行时间、联系人

---

## 3. 编辑与删除动态

- 一般规则：
  - **发布人本人**可以编辑/删除自己发布的动态
  - **管理员**可以管理所有动态

> 若你能看到某条动态右下角角的“编辑/删除”按钮，说明你对该动态有管理权限。

---

## 4. 附件选择（非常重要）

### 4.1 附件来源
附件来自系统的文件空间：
- 公共空间
- 部门空间

### 4.2 选择规则（对齐系统现状）
- 最多选择 **5 个文件** 或 **1 个文件夹**（不可混用）
- 附件选择完成后会显示在动态下方

> **建议**：
> - 面向全院的通知附件，优先放在「公共空间」并作为附件引用
> - 面向部门内部的资料，放在对应「部门空间」

### 4.3 常见附件组织方式
- 多个文件：选择 1–5 个关键文件（制度、模板、流程图等）
- 一个文件夹：把所有资料归档到同一个文件夹，然后把文件夹作为附件（便于一键打包）

---

## 5. 附件下载与打包下载

### 5.1 单个附件下载
点击附件旁的「下载」即可。

### 5.2 打包下载全部附件
当动态附件较多时，可以使用「打包下载全部附件」：
- 系统会将附件打成一个 ZIP 再下载
- 若部分附件已不存在或被移动，系统通常会提示“有部分附件已失效”，并尽量下载仍存在的部分

> **提示**：打包需要时间生成压缩包，附件多/文件大时等待会更久。

---

## 6. 动态与空间权限（详解）

动态由“文字内容”与“附件引用”组成：

### 6.1 你能不能看到一条动态？
- 通常取决于：
  - 动态的可见范围（全院/某部门/指定范围）
  - 你的账号是否属于该范围

### 6.2 你能不能下载这条动态的附件？
附件下载权限取决于附件所在空间：

- **公共空间附件**：大多数登录用户都能下载
- **部门空间附件**：
  - 如果该部门空间是“开放”：通常可下载
  - 如果该部门空间是“非开放”：通常只有该部门成员/管理员才能下载

> **常见现象与解释**
> - 你能看到动态正文，但附件下载失败：通常是你对附件所在空间没有权限。
> - 动态附件显示“已不存在/无法下载”：附件可能被移动、删除，或已被彻底删除。

### 6.3 如何避免“动态可见但附件不可用”
- 面向全院的动态：附件放公共空间
- 面向某部门的动态：附件放该部门空间

---

## 7. 常见问题（FAQ）

### Q1：附件显示不存在/下载失败怎么办？
- 先刷新页面再试
- 若仍失败：联系发布人确认附件是否被移动/删除，或让发布人重新选择附件

### Q2：我能看到动态，但同事看不到
- 可能原因：该动态设置了可见范围（例如仅某部门可见）
- 处理方式：联系发布人或管理员调整可见范围

### Q3：打包下载提示部分缺失
- 说明部分附件已被移动或删除
- 可以联系发布人重新发布或补齐附件
`,
  },
  {
    id: 'share-link',
    group: 'more',
    title: '分享链接',
    md: `# 分享链接

> 用途：为单个文件或文件夹生成一个简短的访问地址，方便在院内其他系统或聊天工具中共享。

---

## 1. 生成分享链接

- 在文件列表中，针对某个 **文件** 或 **文件夹**，点击菜单中的「生成分享链接」（或类似入口）；
- 系统会生成一段短地址，你可以：
  - 复制到剪贴板；
  - 粘贴到 OA、微信群、办公软件等发送给同事；

> 提醒：分享链接只是访问入口，是否能打开仍然受原来空间的权限控制。

---

## 2. 谁可以通过链接访问？

- **公共空间中的内容**：
  - 一般登录后即可通过链接访问（如果院内策略允许）。
- **部门空间中的内容**：
  - 只有对该部门空间有权限的同事，才能通过链接正常访问；
- **个人保险库中的内容**：
  - 通常仅本人可见，即使有链接，其他人也无法打开（除非管理员根据制度做了特殊配置）。

> 可以把分享链接理解为：一种“省去找路径”的打开方式，而不是绕过权限的捷径。

---

## 3. 取消或失效

  - 打开时会提示链接无效或资源已不可用；
- 如果你发现链接不再可用，优先检查：
  - 原文件/文件夹是否还存在；
  - 自己对该空间是否仍有访问权限。
`,
  },
  {
    id: 'feedback',
    group: 'more',
    title: '反馈与使用建议',
    md: `# 反馈与使用建议

## 反馈
- 首页右侧「留言 / 反馈」可以提交问题与建议

## 建议
- 重要资料建议按“公共 / 部门 / 个人”分级存放
- 命名建议包含日期与版本号，便于搜索与协作
- 删除前认真确认；**彻底删除后无法恢复**
`,
  },
]

const navGroups = {
  gettingStarted: docs.filter((d) => d.group === 'getting-started'),
  fileOps: docs.filter((d) => d.group === 'file-ops'),
  more: docs.filter((d) => d.group === 'more'),
}

const openGroups = ref({
  'getting-started': true,
  'file-ops': true,
  more: true,
})

const activeId = ref('intro')

const activeDoc = computed(() => docs.find((d) => d.id === activeId.value) || docs[0])
const activeTitle = computed(() => activeDoc.value.title || '')

const renderedHtml = computed(() => {
  const raw = md.render(activeDoc.value.md || '')
  return DOMPurify.sanitize(raw)
})

const select = (id) => {
  activeId.value = id
  // 切换文档时，保证阅读区回到顶部
  requestAnimationFrame(() => {
    const el = document.querySelector('.help-content')
    if (el) el.scrollTop = 0
  })
}

const toggleGroup = (key) => {
  openGroups.value = {
    ...openGroups.value,
    [key]: !openGroups.value[key],
  }
}
</script>

<style scoped>
.help-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  height: calc(100vh - 3.2rem - 2rem); /* header + main padding（与 App.vue 一致） */
  min-height: 520px;
  gap: 0.75rem;
}

.help-nav {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: auto;
  padding: 0.5rem;
}

.help-nav-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 0.25rem;
}

.help-nav-group {
  margin-top: 0.35rem;
}

.help-nav-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.6rem;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  color: #111827;
  font-weight: 600;
}

.help-nav-toggle:hover {
  background: #f3f4f6;
  border-radius: 4px;
}

.caret {
  width: 16px;
  display: inline-block;
  color: #6b7280;
  transform: rotate(0deg);
  transition: transform 0.12s ease;
}

.caret.open {
  transform: rotate(90deg);
}

.help-nav-items {
  padding: 0.15rem 0 0.25rem 1.35rem;
}

.help-nav-item {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  padding: 0.35rem 0.55rem;
  border-radius: 4px;
  cursor: pointer;
  color: #374151;
  font-size: 13px;
}

.help-nav-item:hover {
  background: #f3f4f6;
}

.help-nav-item.active {
  background: #e0edff;
  color: #1d4ed8;
  font-weight: 600;
}

.help-content {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: auto;
}

.help-content-inner {
  /* 原来是：padding: 0.9rem 1rem 1.2rem; */
  padding: 0.9rem 1.75rem 1.2rem; /* ↑ 左右留白加大 */
  color: #111827;
  max-width: 980px;              /* 可选：限制行宽，阅读更像 docs */
  margin: 0 auto;                /* 可选：居中显示内容 */
}

.help-breadcrumb {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 0.75rem;
}

.help-breadcrumb .sep {
  margin: 0 0.35rem;
}

.help-breadcrumb .strong {
  color: #111827;
  font-weight: 600;
}

/* Markdown 阅读样式（参考大厂 docs 风格，简化版） */
.md :deep(h1) {
  font-size: 20px;
  margin: 0.2rem 0 0.8rem;
}

.md :deep(h2) {
  font-size: 16px;
  margin: 1.05rem 0 0.45rem;
  padding-top: 0.2rem;
}

.md :deep(h3) {
  font-size: 14px;
  margin: 0.85rem 0 0.35rem;
}

.md :deep(p),
.md :deep(li) {
  font-size: 13px;
  line-height: 1.7;
  color: #374151;
}

.md :deep(ul) {
  padding-left: 1.25rem;
}

.md :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 4px;
}

.md :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.6rem 0 1rem;
  font-size: 12px;
}

.md :deep(th),
.md :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 8px 10px;
  vertical-align: top;
}

.md :deep(th) {
  background: #f9fafb;
  font-weight: 700;
}

.md :deep(blockquote) {
  margin: 0.7rem 0;
  padding: 0.55rem 0.75rem;
  border-left: 4px solid #2563eb;
  background: #eff6ff;
  color: #1f2937;
}
</style>
