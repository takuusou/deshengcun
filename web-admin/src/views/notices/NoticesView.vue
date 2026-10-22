<template>
  <section class="notices-page">
    <section class="task-list-panel">
      <div v-if="feedbackText" class="success-box">{{ feedbackText }}</div>
      <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
      <div v-if="loading" class="empty-block">正在加载通知...</div>
      <div v-else-if="!items.length" class="empty-block">当前筛选条件下暂无通知。</div>

      <div v-else class="task-list">
        <button
          v-for="item in paginatedItems"
          :key="item.id"
          type="button"
          class="task-row"
          :class="{ active: item.id === activeId && drawerOpen }"
          @click="selectNotice(item.id)"
        >
          <span class="type-tag" :class="item.is_home_top ? 'tag-home-top' : 'tag-notice'">
            {{ item.is_home_top ? "轮播" : "通知" }}
          </span>
          <span class="task-main">
            <strong>{{ item.title }}</strong>
            <em>{{ item.publisher || "村委会" }} · {{ attachmentCount(item) }} 张附件</em>
          </span>
          <span class="task-side">
            <span class="status-badge" :class="{ done: item.is_home_top }">
              {{ item.is_home_top ? "首页轮播" : "普通通知" }}
            </span>
            <small>{{ formatShortTime(item.created_at) }}</small>
          </span>
        </button>
      </div>

      <footer v-if="!loading && items.length" class="task-pagination">
        <button class="btn-ghost small" type="button" :disabled="currentPage <= 1" @click="currentPage -= 1">上一页</button>
        <span>第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
        <button class="btn-ghost small" type="button" :disabled="currentPage >= totalPages" @click="currentPage += 1">下一页</button>
      </footer>
    </section>

    <div v-if="drawerOpen" class="detail-overlay" @click="closeDrawer">
      <section class="detail-modal" @click.stop>
        <header class="detail-head">
          <div>
            <h3 class="detail-title">{{ editorMode === "create" ? "新建通知" : "编辑通知" }}</h3>
            <p class="detail-subtitle">填写通知标题、正文、发布人和附件。</p>
          </div>
          <div class="detail-head-actions">
            <button
              v-if="editorMode === 'edit' && canWrite"
              class="danger-btn"
              type="button"
              :disabled="saving || !activeId"
              @click="removeNotice"
            >
              删除通知
            </button>
            <button class="drawer-close" type="button" @click="closeDrawer">关闭</button>
          </div>
        </header>

        <div class="detail-scroll">
          <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
          <div class="detail-form">
            <label class="detail-field">
              <span>通知标题</span>
              <input v-model.trim="form.title" type="text" :disabled="!canWrite || detailLoading || saving" placeholder="请输入通知标题" />
            </label>

            <label class="detail-field">
              <span>发布人</span>
              <input
                v-model.trim="form.publisher"
                type="text"
                :disabled="!canWrite || detailLoading || saving"
                placeholder="如：得胜村委会"
              />
            </label>

            <label class="detail-field">
              <span>通知内容</span>
              <textarea
                v-model.trim="form.content"
                rows="10"
                :disabled="!canWrite || detailLoading || saving"
                placeholder="请输入通知内容"
              />
            </label>

            <label class="check-field">
              <input v-model="form.is_home_top" type="checkbox" :disabled="!canWrite || detailLoading || saving" />
              <span>设为首页轮播通知</span>
            </label>

            <div class="detail-section">
              <div class="detail-section-title">通知附件</div>
              <div class="attachment-toolbar">
                <button class="ghost-btn" type="button" :disabled="!canWrite || saving" @click="pickFiles">选择图片</button>
                <input
                  ref="fileInputRef"
                  class="hidden-file-input"
                  type="file"
                  accept="image/*"
                  multiple
                  @change="handleFilesPicked"
                />
                <span class="attachment-hint">支持 JPG / PNG / WEBP / HEIC，最多 9 张。</span>
              </div>

              <div v-if="existingPhotoUrls.length" class="attachment-list">
                <div v-for="(url, index) in existingPhotoUrls" :key="`existing-${index}`" class="attachment-chip">
                  <a :href="url" target="_blank" rel="noreferrer">附件 {{ index + 1 }}</a>
                  <button v-if="canWrite" type="button" class="chip-remove" @click="removeExistingPhoto(index)">移除</button>
                </div>
              </div>

              <div v-if="pendingFiles.length" class="attachment-list">
                <div v-for="(file, index) in pendingFiles" :key="`${file.name}-${index}`" class="attachment-chip pending">
                  <span>{{ file.name }}</span>
                  <button type="button" class="chip-remove" @click="removePendingFile(index)">取消</button>
                </div>
              </div>

              <div v-if="!existingPhotoUrls.length && !pendingFiles.length" class="detail-empty">当前没有附件。</div>
            </div>
          </div>
        </div>
        <div class="detail-foot">
          <div class="detail-actions">
            <button class="primary-btn" type="button" :disabled="!canWrite || saving" @click="saveNotice">
              {{ saving ? "保存中..." : editorMode === "create" ? "创建通知" : "保存修改" }}
            </button>
            <button class="ghost-btn" type="button" :disabled="saving" @click="resetEditor">
              {{ editorMode === "create" ? "清空表单" : "恢复当前内容" }}
            </button>
          </div>
          <span v-if="!canWrite" class="readonly-tip">当前账号是只读角色，不能新增或修改通知。</span>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue"

import {
  createAdminNotice,
  deleteAdminNotice,
  fetchAdminNoticeDetail,
  listAdminNotices,
  updateAdminNotice,
} from "../../api/notices"
import { uploadAdminImages } from "../../api/uploads"
import { useAuthStore } from "../../stores/auth"
import { extractApiError, hasText } from "../../utils/admin-ui"
import { useTransientMessage } from "../../utils/success-toast"

const authStore = useAuthStore()

const filters = reactive({
  keyword: "",
})

const items = ref([])
const activeId = ref(0)
const activeDetail = ref(null)
const editorMode = ref("create")
const drawerOpen = ref(false)
const form = reactive({
  title: "",
  content: "",
  publisher: "",
  is_home_top: false,
})
const existingPhotoUrls = ref([])
const pendingFiles = ref([])
const fileInputRef = ref(null)
const loading = ref(false)
const detailLoading = ref(false)
const saving = ref(false)
const errorMessage = ref("")
const feedbackText = useTransientMessage()
const PAGE_SIZE = 8
const currentPage = ref(1)

const canWrite = computed(() => ["super_admin", "cadre"].includes(authStore.user?.role_key || ""))
const totalPages = computed(() => Math.max(1, Math.ceil(items.value.length / PAGE_SIZE)))
const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return items.value.slice(start, start + PAGE_SIZE)
})

function formatDateTime(value) {
  const text = String(value || "").trim()
  if (!text) return "-"
  return text.replace("T", " ").replace(/\.\d+\+00:00$/, "")
}

function formatShortTime(value) {
  const text = formatDateTime(value)
  if (text === "-") return text
  const [date = "", time = ""] = text.split(" ")
  return `${date} ${time.slice(0, 5)}`.trim()
}

function attachmentCount(item) {
  return Array.isArray(item?.photo_urls) ? item.photo_urls.length : 0
}

function clearFeedback() {
  feedbackText.value = ""
}

function applyFormFromDetail(detail) {
  form.title = detail?.title || ""
  form.content = detail?.content || ""
  form.publisher = detail?.publisher || ""
  form.is_home_top = !!detail?.is_home_top
  existingPhotoUrls.value = [...(detail?.photo_urls || [])]
  pendingFiles.value = []
}

function clearForm() {
  form.title = ""
  form.content = ""
  form.publisher = authStore.user?.display_name || authStore.user?.real_name || "得胜村委会"
  form.is_home_top = false
  existingPhotoUrls.value = []
  pendingFiles.value = []
}

async function loadNoticeDetail(noticeId) {
  if (!noticeId) {
    activeId.value = 0
    activeDetail.value = null
    editorMode.value = "create"
    clearForm()
    return
  }
  detailLoading.value = true
  errorMessage.value = ""
  try {
    const detail = await fetchAdminNoticeDetail(authStore.token, noticeId)
    activeDetail.value = detail
    activeId.value = detail.id
    editorMode.value = "edit"
    applyFormFromDetail(detail)
  } catch (error) {
    errorMessage.value = extractApiError(error, "通知详情加载失败")
  } finally {
    detailLoading.value = false
  }
}

async function loadNotices() {
  loading.value = true
  errorMessage.value = ""
  try {
    const rows = await listAdminNotices(authStore.token, { ...filters })
    items.value = [...(rows || [])].sort((left, right) => {
      const timeCompared = String(right?.created_at || "").localeCompare(String(left?.created_at || ""))
      return timeCompared || Number(right?.id || 0) - Number(left?.id || 0)
    })
    currentPage.value = 1
    if (!items.value.length) {
      activeId.value = 0
      activeDetail.value = null
      if (editorMode.value === "edit") {
        drawerOpen.value = false
      }
      return
    }
    if (activeId.value && !items.value.some((item) => item.id === activeId.value)) {
      activeId.value = 0
      activeDetail.value = null
      editorMode.value = "create"
      drawerOpen.value = false
      clearForm()
    }
  } catch (error) {
    errorMessage.value = extractApiError(error, "通知加载失败")
  } finally {
    loading.value = false
  }
}

async function selectNotice(noticeId) {
  if (!noticeId || detailLoading.value) return
  clearFeedback()
  await loadNoticeDetail(Number(noticeId))
  drawerOpen.value = true
}

function startCreate() {
  clearFeedback()
  errorMessage.value = ""
  editorMode.value = "create"
  activeId.value = 0
  activeDetail.value = null
  clearForm()
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
  activeId.value = 0
  activeDetail.value = null
  editorMode.value = "create"
  errorMessage.value = ""
  clearForm()
}

function resetEditor() {
  errorMessage.value = ""
  if (editorMode.value === "edit" && activeDetail.value) {
    applyFormFromDetail(activeDetail.value)
    return
  }
  clearForm()
}

function searchByKeyword(keyword) {
  filters.keyword = String(keyword || "").trim()
  clearFeedback()
  return loadNotices()
}

function pickFiles() {
  fileInputRef.value?.click()
}

function handleFilesPicked(event) {
  const fileList = Array.from(event?.target?.files || [])
  if (!fileList.length) return
  pendingFiles.value = [...pendingFiles.value, ...fileList].slice(0, Math.max(0, 9 - existingPhotoUrls.value.length))
  if (event?.target) {
    event.target.value = ""
  }
}

function removeExistingPhoto(index) {
  existingPhotoUrls.value = existingPhotoUrls.value.filter((_, itemIndex) => itemIndex !== index)
}

function removePendingFile(index) {
  pendingFiles.value = pendingFiles.value.filter((_, itemIndex) => itemIndex !== index)
}

function validateNoticeForm() {
  if (!hasText(form.title)) return "请先填写通知标题。"
  if (!hasText(form.publisher)) return "请先填写发布人。"
  if (!hasText(form.content)) return "请先填写通知内容。"
  return ""
}

async function saveNotice() {
  if (!canWrite.value) return
  const validationError = validateNoticeForm()
  if (validationError) {
    errorMessage.value = validationError
    return
  }
  const isCreating = editorMode.value === "create"
  saving.value = true
  errorMessage.value = ""
  clearFeedback()
  try {
    const uploadedUrls = await uploadAdminImages(authStore.token, pendingFiles.value, "notice")
    const payload = {
      title: form.title,
      content: form.content,
      publisher: form.publisher,
      is_home_top: form.is_home_top,
      photo_urls: [...existingPhotoUrls.value, ...uploadedUrls],
    }
    const result =
      editorMode.value === "edit" && activeId.value
        ? await updateAdminNotice(authStore.token, activeId.value, payload)
        : await createAdminNotice(authStore.token, payload)
    feedbackText.value = isCreating ? "通知已创建。" : "通知已保存。"
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("admin-nav-badges:refresh"))
    }
    await loadNotices()
    if (isCreating) {
      drawerOpen.value = false
      activeId.value = 0
      activeDetail.value = null
      editorMode.value = "create"
      clearForm()
    } else {
      await loadNoticeDetail(result.id)
      drawerOpen.value = true
    }
  } catch (error) {
    errorMessage.value = extractApiError(error, "通知保存失败")
  } finally {
    saving.value = false
  }
}

async function removeNotice() {
  if (!canWrite.value || !activeId.value) return
  if (!window.confirm("确认删除这条通知吗？删除后不可恢复。")) return
  saving.value = true
  errorMessage.value = ""
  clearFeedback()
  try {
    await deleteAdminNotice(authStore.token, activeId.value)
    feedbackText.value = "通知已删除。"
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("admin-nav-badges:refresh"))
    }
    closeDrawer()
    await loadNotices()
  } catch (error) {
    errorMessage.value = extractApiError(error, "通知删除失败")
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  clearForm()
  loadNotices()
})

defineExpose({ loadNotices, searchByKeyword, startCreate, loading, canWrite })
</script>

<style scoped>
.notices-page {
  min-height: 100%;
  display: grid;
}

.detail-actions,
.attachment-toolbar,
.detail-head-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-actions,
.attachment-toolbar,
.detail-head-actions {
  justify-content: flex-end;
}

.detail-title {
  margin: 0;
  font-size: 22px;
  color: #10382a;
}

.detail-subtitle {
  margin: 6px 0 0;
  color: #667085;
  font-size: 13px;
}

.task-list-panel {
  min-height: 100%;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--color-card);
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.detail-field,
.detail-form,
.detail-section {
  display: grid;
  gap: 10px;
}

.task-list {
  flex: 1;
  min-height: 0;
  display: block;
  gap: 0;
}

.task-pagination {
  min-height: 58px;
  padding: 10px 20px;
  border-top: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-shrink: 0;
}

.task-pagination span {
  min-width: 132px;
  color: var(--color-text-sub);
  font-size: 13px;
  text-align: center;
}

.task-pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  transform: none;
}

.small {
  min-height: 32px;
  padding: 0 12px;
}

.detail-field span,
.detail-section-title {
  font-size: 13px;
  font-weight: 700;
  color: #10382a;
}

.check-field {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #344054;
  flex-wrap: wrap;
}

.attachment-hint,
.readonly-tip,
.detail-empty,
.empty-block {
  color: #667085;
  font-size: 12px;
}

.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(16, 24, 40, 0.38);
  display: grid;
  place-items: center;
  padding: 24px;
  z-index: 50;
}

.detail-modal {
  width: min(980px, 100%);
  max-height: min(90vh, 920px);
  border-radius: 26px;
  border: 1px solid rgba(16, 56, 42, 0.08);
  background: #fff;
  box-shadow: 0 24px 64px rgba(16, 24, 40, 0.18);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.detail-head,
.detail-foot {
  padding: 16px 18px;
  background: #fff;
}

.detail-head {
  border-bottom: 1px solid rgba(16, 56, 42, 0.08);
}

.detail-foot {
  border-top: 1px solid rgba(16, 56, 42, 0.08);
}

.detail-scroll {
  min-height: 0;
  overflow: auto;
  padding: 16px 18px;
}

.task-row {
  width: 100%;
  min-height: 74px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  border: 0;
  border-bottom: 1px solid var(--color-border-light);
  border-radius: 0;
  background: transparent;
  text-align: left;
}

.task-row:hover,
.task-row.active {
  background: #fbf8f1;
}

.type-tag {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
}

.tag-notice {
  background: #f4f0ea;
  color: #6f6258;
}

.tag-home-top {
  background: #e9f0e7;
  color: var(--color-matcha);
}

.task-main {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 5px;
}

.task-main strong {
  color: var(--color-text);
  font-size: 15px;
}

.task-main em,
.task-side small {
  color: var(--color-text-hint);
  font-size: 12px;
  font-style: normal;
}

.task-side {
  flex-shrink: 0;
  min-width: 132px;
  display: grid;
  justify-items: end;
  gap: 7px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: #fbf1db;
  color: #b5852a;
}

.status-badge.done {
  background: #e9f0e7;
  color: var(--color-matcha);
}

.attachment-list,
.detail-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.attachment-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  padding: 8px 12px;
  background: #eef4ff;
  color: #175cd3;
}

.attachment-chip.pending {
  background: #f2f4f7;
  color: #344054;
}

.attachment-chip a {
  color: inherit;
  text-decoration: none;
}

.chip-remove {
  border: 0;
  background: transparent;
  color: inherit;
}

.hidden-file-input {
  display: none;
}

.inline-error {
  padding: 12px 14px;
  border-radius: 12px;
  background: #fef2f2;
  color: #b42318;
  font-size: 13px;
}

.danger-btn {
  min-height: 42px;
  padding: 0 16px;
  border: 0;
  border-radius: 12px;
  background: #b42318;
  color: #fff;
}

@media (max-width: 960px) {
  .detail-overlay {
    padding: 12px;
  }

  .detail-modal {
    max-height: 94vh;
    border-radius: 18px;
  }
}

@media (max-width: 720px) {
  .task-row {
    min-height: 0;
    padding: 14px 12px;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: start;
    gap: 9px 10px;
  }

  .task-main strong,
  .task-main em {
    overflow-wrap: anywhere;
  }

  .task-side {
    grid-column: 2;
    min-width: 0;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .task-pagination {
    min-height: 62px;
    padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
    gap: 8px;
  }

  .task-pagination span {
    min-width: 0;
    flex: 1;
    white-space: nowrap;
  }

  .detail-overlay {
    place-items: stretch;
    padding: 0;
  }

  .detail-modal {
    width: 100%;
    max-height: none;
    height: 100vh;
    height: 100dvh;
    margin: 0;
    border: 0;
    border-radius: 0;
  }

  .detail-head {
    position: relative;
    display: block;
    gap: 10px;
    padding-right: 82px;
  }

  .detail-title {
    font-size: 18px;
  }

  .detail-head-actions {
    width: auto;
    justify-content: flex-start;
    margin-top: 10px;
  }

  .detail-head-actions .drawer-close {
    position: absolute;
    top: 12px;
    right: 12px;
    margin-left: 0;
  }

  .detail-scroll {
    padding: 12px;
    overscroll-behavior: contain;
  }

  .detail-foot {
    padding: 12px 12px calc(12px + env(safe-area-inset-bottom));
  }

  .detail-actions {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-actions button,
  .attachment-toolbar button {
    min-height: 44px;
  }

  .attachment-toolbar {
    justify-content: flex-start;
  }

  .attachment-hint {
    flex-basis: 100%;
    line-height: 1.55;
  }
}
</style>
