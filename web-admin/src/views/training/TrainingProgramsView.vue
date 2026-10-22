<template>
  <section class="training-admin-page">
    <section class="publishing-list-panel">
      <div v-if="feedbackText" class="success-box">{{ feedbackText }}</div>
      <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
      <div v-if="loading" class="empty-block">正在加载就业培训...</div>
      <div v-else-if="!items.length" class="empty-block">当前筛选条件下暂无就业培训。</div>

      <div v-else class="program-list">
        <button
          v-for="item in paginatedItems"
          :key="item.id"
          type="button"
          class="program-row"
          :class="{ active: item.id === activeId && drawerOpen }"
          @click="selectProgram(item.id)"
        >
          <div class="program-row-primary">
            <div class="program-row-title">{{ item.title }}</div>
            <div class="program-row-sub">
              {{ item.schedule_text || "-" }} · {{ item.location || "-" }}
            </div>
            <div class="program-row-result">对象：{{ item.target || "未填写" }}</div>
          </div>
          <div class="program-row-secondary">
            <span class="status-badge" :class="{ closed: !item.is_open }">{{ item.status_label }}</span>
            <div class="program-row-time">截止：{{ item.signup_deadline || "-" }}</div>
            <div class="program-row-side-note">{{ item.signup_count || 0 }} 人报名</div>
          </div>
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
            <h3 class="detail-title">{{ editorMode === "create" ? "新建就业培训" : "编辑就业培训" }}</h3>
            <p class="detail-subtitle">发布到村民端“就业培训”，村民可浏览并填写姓名、电话报名。</p>
          </div>
          <div class="detail-head-actions">
            <button
              v-if="editorMode === 'edit' && canWrite && currentProgram?.is_open"
              class="warning-btn"
              type="button"
              :disabled="saving || !activeId"
              @click="endProgram"
            >
              手动结束
            </button>
            <button
              v-if="editorMode === 'edit' && canWrite"
              class="danger-btn"
              type="button"
              :disabled="saving || !activeId"
              @click="removeProgram"
            >
              删除培训
            </button>
            <button class="drawer-close" type="button" @click="closeDrawer">关闭</button>
          </div>
        </header>

        <div class="detail-scroll">
          <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
          <div class="detail-form">
            <label class="detail-field">
              <span>培训标题</span>
              <input v-model.trim="form.title" type="text" :disabled="!canWrite || saving" placeholder="如：叉车技能培训报名" />
            </label>

            <div class="detail-grid">
              <label class="detail-field">
                <span>培训时间</span>
                <input
                  v-model.trim="form.schedule_text"
                  type="text"
                  :disabled="!canWrite || saving"
                  placeholder="如：2026-07-08 至 2026-07-10"
                />
              </label>
              <label class="detail-field">
                <span>培训地点</span>
                <input v-model.trim="form.location" type="text" :disabled="!canWrite || saving" placeholder="如：上塔市镇就业服务站" />
              </label>
            </div>

            <label class="detail-field">
              <span>适合对象</span>
              <input
                v-model.trim="form.target"
                type="text"
                :disabled="!canWrite || saving"
                placeholder="如：有就业意向、能按时参加培训的村民"
              />
            </label>

            <div class="detail-grid">
              <label class="detail-field">
                <span>报名截止日</span>
                <input v-model="form.signup_deadline" type="date" :disabled="!canWrite || saving" />
              </label>
              <label class="detail-field">
                <span>培训结束日</span>
                <input v-model="form.end_date" type="date" :disabled="!canWrite || saving" />
              </label>
            </div>

            <div class="detail-grid">
              <label class="detail-field">
                <span>联系电话</span>
                <input v-model.trim="form.contact_phone" type="text" :disabled="!canWrite || saving" placeholder="村书记或村委联系电话" />
              </label>
              <label class="detail-field">
                <span>发布状态</span>
                <select v-model="form.status" :disabled="!canWrite || saving">
                  <option value="open">开放报名</option>
                  <option value="ended">手动结束</option>
                </select>
              </label>
            </div>

            <div v-if="editorMode === 'edit' && activeId" class="detail-section">
              <div class="detail-section-head">
                <div class="detail-section-title">报名名单</div>
                <div class="section-meta">共 {{ signups.length }} 人</div>
              </div>
              <div class="detail-actions">
                <button class="ghost-btn" type="button" :disabled="signupLoading" @click="loadSignups">刷新名单</button>
                <button class="ghost-btn" type="button" :disabled="!signups.length" @click="exportSignups">导出 CSV</button>
              </div>
              <div v-if="signupLoading" class="detail-empty">正在加载报名名单...</div>
              <div v-else-if="!signups.length" class="detail-empty">当前还没有村民报名。</div>
              <div v-else class="signup-table-wrap">
                <table class="signup-table">
                  <thead>
                    <tr>
                      <th>姓名</th>
                      <th>手机号</th>
                      <th>报名时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in signups" :key="item.id">
                      <td>{{ item.name }}</td>
                      <td>{{ item.phone }}</td>
                      <td>{{ formatDateTime(item.created_at) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <div class="detail-foot">
          <div class="detail-actions">
            <button class="primary-btn" type="button" :disabled="!canWrite || saving" @click="saveProgram">
              {{ saving ? "保存中..." : editorMode === "create" ? "创建培训" : "保存修改" }}
            </button>
            <button class="ghost-btn" type="button" :disabled="saving" @click="resetEditor">
              {{ editorMode === "create" ? "清空表单" : "恢复当前内容" }}
            </button>
          </div>
          <span v-if="!canWrite" class="readonly-tip">当前账号是只读角色，不能新增或修改就业培训。</span>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import {
  createAdminTrainingProgram,
  deleteAdminTrainingProgram,
  endAdminTrainingProgram,
  exportAdminTrainingSignups,
  listAdminTrainingPrograms,
  listAdminTrainingSignups,
  updateAdminTrainingProgram,
} from "../../api/training";
import { useAuthStore } from "../../stores/auth";
import { extractApiError, hasText } from "../../utils/admin-ui";
import { useTransientMessage } from "../../utils/success-toast";

const authStore = useAuthStore();

const filters = reactive({ keyword: "" });
const allItems = ref([]);
const signups = ref([]);
const activeId = ref(0);
const editorMode = ref("create");
const drawerOpen = ref(false);
const loading = ref(false);
const signupLoading = ref(false);
const saving = ref(false);
const errorMessage = ref("");
const feedbackText = useTransientMessage();
const PAGE_SIZE = 8;
const currentPage = ref(1);

const form = reactive({
  title: "",
  schedule_text: "",
  location: "",
  target: "",
  signup_deadline: "",
  end_date: "",
  contact_phone: "",
  status: "open",
});

const canWrite = computed(() => ["super_admin", "cadre"].includes(authStore.user?.role_key || ""));
const currentProgram = computed(() => allItems.value.find((item) => item.id === activeId.value) || null);
const items = computed(() => allItems.value);
const totalPages = computed(() => Math.max(1, Math.ceil(items.value.length / PAGE_SIZE)));
const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return items.value.slice(start, start + PAGE_SIZE);
});

function clearFeedback() {
  feedbackText.value = "";
}

function formatDateTime(value) {
  const text = String(value || "").trim();
  if (!text) return "-";
  return text.replace("T", " ").replace(/\.\d+\+00:00$/, "");
}

function clearForm() {
  form.title = "";
  form.schedule_text = "";
  form.location = "";
  form.target = "";
  form.signup_deadline = "";
  form.end_date = "";
  form.contact_phone = "";
  form.status = "open";
  signups.value = [];
}

function applyForm(item) {
  form.title = item?.title || "";
  form.schedule_text = item?.schedule_text || "";
  form.location = item?.location || "";
  form.target = item?.target || "";
  form.signup_deadline = item?.signup_deadline || "";
  form.end_date = item?.end_date || "";
  form.contact_phone = item?.contact_phone || "";
  form.status = item?.status === "ended" ? "ended" : "open";
}

async function loadPrograms() {
  loading.value = true;
  errorMessage.value = "";
  try {
    const rows = await listAdminTrainingPrograms(authStore.token, { keyword: filters.keyword });
    allItems.value = rows || [];
    currentPage.value = 1;
    if (activeId.value && !items.value.some((item) => item.id === activeId.value)) {
      closeDrawer();
    }
  } catch (err) {
    errorMessage.value = extractApiError(err, "就业培训加载失败");
  } finally {
    loading.value = false;
  }
}

async function loadSignups() {
  if (!activeId.value) {
    signups.value = [];
    return;
  }
  signupLoading.value = true;
  try {
    signups.value = await listAdminTrainingSignups(authStore.token, activeId.value);
  } catch (err) {
    errorMessage.value = extractApiError(err, "报名名单加载失败");
    signups.value = [];
  } finally {
    signupLoading.value = false;
  }
}

async function selectProgram(programId) {
  const current = items.value.find((item) => item.id === programId) || null;
  if (!current) return;
  clearFeedback();
  errorMessage.value = "";
  activeId.value = programId;
  editorMode.value = "edit";
  applyForm(current);
  drawerOpen.value = true;
  await loadSignups();
}

function startCreate() {
  clearFeedback();
  errorMessage.value = "";
  editorMode.value = "create";
  activeId.value = 0;
  clearForm();
  drawerOpen.value = true;
}

function closeDrawer() {
  drawerOpen.value = false;
  activeId.value = 0;
  editorMode.value = "create";
  errorMessage.value = "";
  clearForm();
}

function searchByKeyword(keyword) {
  filters.keyword = String(keyword || "").trim();
  clearFeedback();
  return loadPrograms();
}

function resetEditor() {
  errorMessage.value = "";
  if (editorMode.value === "create") {
    clearForm();
    return;
  }
  const current = allItems.value.find((item) => item.id === activeId.value);
  if (current) {
    applyForm(current);
  }
}

function validateForm() {
  if (!hasText(form.title)) return "请先填写培训标题。";
  if (!hasText(form.schedule_text)) return "请先填写培训时间。";
  if (!hasText(form.location)) return "请先填写培训地点。";
  if (!hasText(form.target)) return "请先填写适合对象。";
  if (!hasText(form.signup_deadline)) return "请先选择报名截止日。";
  if (!hasText(form.end_date)) return "请先选择培训结束日。";
  if (form.end_date < form.signup_deadline) return "培训结束日不能早于报名截止日。";
  if (!hasText(form.contact_phone)) return "请先填写联系电话。";
  return "";
}

function buildPayload() {
  return {
    title: form.title,
    schedule_text: form.schedule_text,
    location: form.location,
    target: form.target,
    signup_deadline: form.signup_deadline,
    end_date: form.end_date,
    contact_phone: form.contact_phone,
    status: form.status === "ended" ? "ended" : "open",
  };
}

async function saveProgram() {
  if (!canWrite.value) return;
  const validationError = validateForm();
  if (validationError) {
    errorMessage.value = validationError;
    return;
  }
  const isCreating = editorMode.value === "create";
  saving.value = true;
  errorMessage.value = "";
  clearFeedback();
  try {
    const result =
      editorMode.value === "create"
        ? await createAdminTrainingProgram(authStore.token, buildPayload())
        : await updateAdminTrainingProgram(authStore.token, activeId.value, buildPayload());
    activeId.value = result.id;
    editorMode.value = "edit";
    applyForm(result);
    drawerOpen.value = true;
    feedbackText.value = isCreating ? "就业培训已创建。" : "就业培训已保存。";
    await loadPrograms();
    await loadSignups();
  } catch (err) {
    errorMessage.value = extractApiError(err, "就业培训保存失败");
  } finally {
    saving.value = false;
  }
}

async function endProgram() {
  if (!activeId.value || !canWrite.value) return;
  if (!window.confirm("手动结束后村民端将不能继续报名，确定继续吗？")) return;
  saving.value = true;
  errorMessage.value = "";
  clearFeedback();
  try {
    const result = await endAdminTrainingProgram(authStore.token, activeId.value);
    applyForm(result);
    feedbackText.value = "就业培训已结束。";
    await loadPrograms();
  } catch (err) {
    errorMessage.value = extractApiError(err, "就业培训结束失败");
  } finally {
    saving.value = false;
  }
}

async function removeProgram() {
  if (!activeId.value || !canWrite.value) return;
  if (!window.confirm("删除后村民端将不再显示该培训，且报名名单会一起删除，确定继续吗？")) return;
  saving.value = true;
  errorMessage.value = "";
  clearFeedback();
  try {
    await deleteAdminTrainingProgram(authStore.token, activeId.value);
    feedbackText.value = "就业培训已删除。";
    closeDrawer();
    await loadPrograms();
  } catch (err) {
    errorMessage.value = extractApiError(err, "就业培训删除失败");
  } finally {
    saving.value = false;
  }
}

async function exportSignups() {
  if (!activeId.value) return;
  try {
    const current = allItems.value.find((item) => item.id === activeId.value);
    const filename = `${current?.title || "就业培训"}_报名名单.csv`;
    await exportAdminTrainingSignups(authStore.token, activeId.value, filename);
  } catch (err) {
    errorMessage.value = extractApiError(err, "报名名单导出失败");
  }
}

onMounted(async () => {
  clearForm();
  await loadPrograms();
});

defineExpose({ loadPrograms, searchByKeyword, startCreate, loading, canWrite });
</script>

<style scoped>
.training-admin-page {
  min-height: 100%;
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  gap: 0;
}

.publishing-list-panel {
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  padding: 0;
}

.detail-actions,
.detail-head-actions,
.detail-section-head {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-section-head {
  justify-content: space-between;
}

.detail-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #10382a;
}

.detail-subtitle {
  margin: 6px 0 0;
  color: #667085;
  font-size: 13px;
}

.detail-field,
.detail-form,
.detail-section {
  display: grid;
  gap: 0;
}

.program-list {
  flex: 1;
  min-height: 0;
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

.readonly-tip,
.section-meta,
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
  width: min(960px, 100%);
  max-height: min(90vh, 860px);
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

.program-row {
  width: 100%;
  min-height: 92px;
  border: 0;
  border-bottom: 1px solid rgba(16, 56, 42, 0.08);
  border-radius: 0;
  background: transparent;
  padding: 16px 20px;
  text-align: left;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.program-row:hover,
.program-row.active {
  background: #fbf8f1;
}

.program-row-primary {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.program-row-title {
  color: #10382a;
  font-size: 16px;
  font-weight: 700;
}

.program-row-sub,
.program-row-result {
  color: #667085;
  font-size: 13px;
  line-height: 1.55;
}

.program-row-secondary {
  flex-shrink: 0;
  min-width: 150px;
  display: grid;
  justify-items: end;
  gap: 8px;
}

.program-row-time,
.program-row-side-note {
  color: #667085;
  font-size: 12px;
}

.status-badge {
  padding: 5px 10px;
  border-radius: 999px;
  background: #e9f6ee;
  color: #14613f;
  font-size: 12px;
  font-weight: 700;
}

.status-badge.closed {
  background: #f4ead9;
  color: #8c6d2f;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-field input,
.detail-field select {
  width: 100%;
  min-height: 40px;
  border: 1px solid rgba(16, 56, 42, 0.14);
  border-radius: 10px;
  padding: 8px 10px;
  color: #10382a;
  background: #fff;
  box-sizing: border-box;
}

.detail-section {
  margin-top: 8px;
  padding: 14px;
  border: 1px solid rgba(16, 56, 42, 0.08);
  border-radius: 16px;
  background: #fbfdfb;
}

.signup-table-wrap {
  overflow: auto;
  border: 1px solid rgba(16, 56, 42, 0.08);
  border-radius: 12px;
}

.signup-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 520px;
}

.signup-table th,
.signup-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(16, 56, 42, 0.08);
  text-align: left;
  font-size: 13px;
}

.signup-table th {
  background: #f6faf7;
  color: #10382a;
}

.signup-table td {
  color: #344054;
}

.empty-block,
.detail-empty {
  min-height: 120px;
  display: grid;
  place-items: center;
}

.warning-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 10px;
  background: #fff7e8;
  color: #9a641c;
  border: 1px solid #f0d9a8;
}

@media (max-width: 860px) {
  .program-row {
    align-items: flex-start;
    flex-direction: column;
  }
  .program-row-secondary {
    width: 100%;
    justify-items: start;
  }
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .program-row {
    min-height: 0;
    padding: 14px 12px;
    gap: 10px;
  }

  .program-row-primary,
  .program-row-secondary {
    width: 100%;
  }

  .program-row-secondary {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    justify-items: start;
  }

  .program-row-time,
  .program-row-side-note {
    justify-self: end;
    text-align: right;
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
  }

  .detail-actions button {
    flex: 1;
    min-height: 44px;
  }
}
</style>
