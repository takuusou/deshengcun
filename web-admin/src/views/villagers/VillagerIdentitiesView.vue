<template>
  <section class="villager-page">
    <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
    <div v-if="statusMessage" class="inline-success">{{ statusMessage }}</div>

      <div class="tablewrap">
        <div class="twhead">
          <h3>村民列表</h3>
        </div>

        <div v-if="loading" class="empty-block">正在加载村民实名记录...</div>
        <div v-else-if="!items.length" class="empty-block">暂无村民实名记录</div>

        <template v-else>
          <div
            v-for="item in paginatedItems"
            :key="item.user_id"
            class="trow"
            @click="selectItem(item.user_id)"
          >
            <span class="nm"><span class="ava">{{ avatarText(item.real_name) }}</span>{{ item.real_name || "未登记" }}</span>
            <span class="ph">{{ item.phone_masked || "-" }}</span>
            <span class="idn">{{ item.id_card_masked || "-" }}</span>
            <span class="gp">{{ item.village_group || "未分组" }}</span>
            <span class="ag">{{ ageText(item.age) }}</span>
            <span><span class="pill" :class="rosterPillClass(item.roster_match_status)">{{ rosterLabel(item.roster_match_status) }}</span></span>
            <span class="view">查看 ›</span>
          </div>
        </template>

        <footer v-if="!loading && items.length" class="task-pagination">
          <button class="btn-ghost small" type="button" :disabled="currentPage <= 1" @click="currentPage -= 1">上一页</button>
          <span>第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
          <button class="btn-ghost small" type="button" :disabled="currentPage >= totalPages" @click="currentPage += 1">下一页</button>
        </footer>
      </div>

      <div v-if="detailVisible" class="mask" @click="closeDetail">
        <div class="modal" @click.stop>
          <template v-if="activeItem">
            <div class="mhead">
              <div class="ava">{{ avatarText(activeItem.real_name) }}</div>
              <div class="ht">
                <h2>{{ activeItem.real_name || "未登记" }}</h2>
                <div class="sub">{{ activeItem.village_group || "未分组" }}</div>
              </div>
              <span class="pill" :class="rosterPillClass(activeItem.roster_match_status)">{{ rosterLabel(activeItem.roster_match_status) }}</span>
              <button class="mclose" type="button" @click="closeDetail">×</button>
            </div>

            <div class="mbody">
              <div class="info-grid">
                <div class="info-cell">
                  <div class="k">手机号</div>
                  <div class="v">{{ activeItem.phone_masked || "-" }}</div>
                </div>
                <div class="info-cell">
                  <div class="k">身份证</div>
                  <div class="v">{{ activeItem.id_card_masked || "-" }}</div>
                </div>
                <div class="info-cell">
                  <div class="k">性别</div>
                  <div class="v">{{ genderText(activeItem.gender) }}</div>
                </div>
                <div class="info-cell">
                  <div class="k">年龄</div>
                  <div class="v">{{ ageText(activeItem.age) }}</div>
                </div>
                <div class="info-cell">
                  <div class="k">所在村组</div>
                  <div class="v">{{ activeItem.village_group || "未分组" }}</div>
                </div>
                <div class="info-cell">
                  <div class="k">实名时间</div>
                  <div class="v">{{ formatTime(activeItem.realname_submitted_at) }}</div>
                </div>
              </div>

              <div v-if="isSuperAdmin" class="adv-toggle" @click="advancedOpen = !advancedOpen">
                <span class="ar">{{ advancedOpen ? "▲" : "▼" }}</span>
                高级操作（解绑 / 重绑实名）
              </div>
              <div v-show="isSuperAdmin && advancedOpen" class="adv-box">
                <div class="warn-note">谨慎操作。解绑后该村民需重新实名认证，操作将记入审计日志。一般情况无需在此处理。</div>
                <label>解绑原因（便于审计追溯）</label>
                <textarea v-model.trim="unbindReason" rows="2" placeholder="如：手机号变更、信息登记有误…" />
                <label>按花名册重绑（姓名 + 身份证号）</label>
                <input v-model.trim="rebindForm.real_name" type="text" placeholder="姓名" />
                <input v-model.trim="rebindForm.id_card_number" type="text" placeholder="身份证号" />
                <div class="adv-actions">
                  <button class="btn-danger-ghost" type="button" :disabled="saving" @click="handleUnbind">
                    {{ saving ? "处理中..." : "解绑实名登记" }}
                  </button>
                  <button class="btn-ghost" type="button" :disabled="saving" @click="handleRebind">
                    {{ saving ? "处理中..." : "按花名册重绑" }}
                  </button>
                </div>
              </div>
            </div>
          </template>

          <div v-else class="empty-block">未找到这条实名记录。</div>
        </div>
      </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import {
  exportAdminVillagerIdentities,
  fetchAdminVillagerIdentitySummary,
  listAdminVillagerIdentities,
  rebindAdminVillagerIdentity,
  unbindAdminVillagerIdentity,
} from "../../api/villagers";
import { useAuthStore } from "../../stores/auth";
import { extractApiError } from "../../utils/admin-ui";
import { useTransientMessage } from "../../utils/success-toast";

const authStore = useAuthStore();

const filters = reactive({
  keyword: "",
});

const items = ref([]);
const activeId = ref(0);
const activeItem = ref(null);
const detailVisible = ref(false);
const loading = ref(false);
const saving = ref(false);
const exporting = ref(false);
const errorMessage = ref("");
const statusMessage = useTransientMessage();
const summary = reactive({
  total_count: 0,
  matched_count: 0,
  grouped_count: 0,
});
const unbindReason = ref("");
const rebindForm = reactive({
  real_name: "",
  id_card_number: "",
});
const advancedOpen = ref(false);
const PAGE_SIZE = 10;
const currentPage = ref(1);

const isSuperAdmin = computed(() => authStore.user?.role_key === "super_admin");
const totalPages = computed(() => Math.max(1, Math.ceil(items.value.length / PAGE_SIZE)));
const paginatedItems = computed(() => {
  const safePage = Math.min(currentPage.value, totalPages.value);
  const start = (safePage - 1) * PAGE_SIZE;
  return items.value.slice(start, start + PAGE_SIZE);
});

function authStatusLabel(value) {
  const map = {
    unverified: "未完成",
    partial: "进行中",
    verified: "已完成",
  };
  return map[String(value || "").trim()] || value || "-";
}

function rosterLabel(value) {
  const map = {
    unmatched: "未匹配",
    matched: "已匹配",
    not_configured: "未配置名单",
  };
  return map[String(value || "").trim()] || value || "-";
}

function ageText(value) {
  return Number.isFinite(value) ? `${value} 岁` : "年龄待识别";
}

function avatarText(name) {
  const text = String(name || "").trim();
  return text ? text.slice(0, 1) : "村";
}

function rosterPillClass(value) {
  return String(value || "").trim() === "matched" ? "pill-match" : "pill-unmatch";
}

function genderText(value) {
  const text = String(value || "").trim();
  if (text === "male" || text === "男") return "男";
  if (text === "female" || text === "女") return "女";
  return text || "-";
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

function formatTime(value) {
  const text = String(value || "").trim();
  if (!text) return "-";
  const dt = new Date(text);
  if (Number.isNaN(dt.getTime())) return text;
  const hm = `${pad2(dt.getHours())}:${pad2(dt.getMinutes())}`;
  return `${dt.getFullYear()}-${pad2(dt.getMonth() + 1)}-${pad2(dt.getDate())} ${hm}`;
}

function syncDetailForm(item) {
  rebindForm.real_name = item?.real_name || "";
  rebindForm.id_card_number = "";
  unbindReason.value = "";
}

function closeDetail() {
  detailVisible.value = false;
  advancedOpen.value = false;
}

function selectItem(userId) {
  activeId.value = Number(userId || 0);
  activeItem.value = items.value.find((item) => item.user_id === activeId.value) || null;
  syncDetailForm(activeItem.value);
  advancedOpen.value = false;
  detailVisible.value = !!activeItem.value;
}

async function loadItems(resetSelection = false) {
  loading.value = true;
  errorMessage.value = "";
  if (resetSelection) {
    statusMessage.value = "";
  }
  try {
    const [rows, summaryRow] = await Promise.all([
      listAdminVillagerIdentities(authStore.token, {
        keyword: filters.keyword,
        limit: 500,
      }),
      fetchAdminVillagerIdentitySummary(authStore.token, {
        keyword: filters.keyword,
      }),
    ]);
    items.value = Array.isArray(rows) ? rows : [];
    currentPage.value = resetSelection ? 1 : Math.min(currentPage.value, totalPages.value);
    summary.total_count = Number(summaryRow?.total_count || 0);
    summary.matched_count = Number(summaryRow?.matched_count || 0);
    summary.grouped_count = Number(summaryRow?.grouped_count || 0);
    if (!items.value.length) {
      activeId.value = 0;
      activeItem.value = null;
      syncDetailForm(null);
      closeDetail();
      return;
    }
    if (resetSelection) {
      activeId.value = 0;
      activeItem.value = null;
      syncDetailForm(null);
      closeDetail();
      return;
    }
    if (detailVisible.value && activeId.value) {
      const current = items.value.find((item) => item.user_id === activeId.value) || null;
      if (current) {
        activeItem.value = current;
        syncDetailForm(current);
      } else {
        activeId.value = 0;
        activeItem.value = null;
        syncDetailForm(null);
        closeDetail();
      }
      return;
    }
    if (!items.value.some((item) => item.user_id === activeId.value)) {
      activeId.value = 0;
      activeItem.value = null;
      syncDetailForm(null);
    }
  } catch (error) {
    errorMessage.value = extractApiError(error, "加载实名记录失败，请稍后重试。");
  } finally {
    loading.value = false;
  }
}

function resetFilters() {
  filters.keyword = "";
  closeDetail();
  loadItems(true);
}

function searchWith(keyword) {
  filters.keyword = String(keyword || "");
  loadItems(true);
}

async function handleExport() {
  exporting.value = true;
  errorMessage.value = "";
  try {
    await exportAdminVillagerIdentities(authStore.token, { keyword: filters.keyword });
    statusMessage.value = "村民脱敏名册已开始下载。";
  } catch (error) {
    errorMessage.value = extractApiError(error, "村民脱敏名册导出失败，请稍后重试。");
  } finally {
    exporting.value = false;
  }
}

async function handleUnbind() {
  if (!activeItem.value) {
    return;
  }
  if (!window.confirm(`确认解绑 ${activeItem.value.real_name || "该村民"} 的基础实名登记吗？`)) {
    return;
  }
  saving.value = true;
  errorMessage.value = "";
  statusMessage.value = "";
  try {
    const result = await unbindAdminVillagerIdentity(authStore.token, activeItem.value.user_id, {
      reason: unbindReason.value,
    });
    statusMessage.value = result?.message || "已解绑基础实名登记。";
    await loadItems(true);
  } catch (error) {
    errorMessage.value = extractApiError(error, "解绑失败，请稍后重试。");
  } finally {
    saving.value = false;
  }
}

async function handleRebind() {
  if (!activeItem.value) {
    return;
  }
  saving.value = true;
  errorMessage.value = "";
  statusMessage.value = "";
  try {
    const row = await rebindAdminVillagerIdentity(authStore.token, activeItem.value.user_id, {
      real_name: rebindForm.real_name,
      id_card_number: rebindForm.id_card_number,
    });
    statusMessage.value = "已按名单完成重绑。";
    await loadItems(false);
    activeId.value = row.user_id;
    activeItem.value = items.value.find((item) => item.user_id === row.user_id) || row;
    syncDetailForm(activeItem.value);
  } catch (error) {
    errorMessage.value = extractApiError(error, "重绑失败，请稍后重试。");
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadItems(true);
});

defineExpose({ loadItems, handleExport, resetFilters, searchWith, loading, exporting });
</script>

<style scoped>
.villager-page {
  min-height: 100%;
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  gap: 12px;
}

/* ===== 村民表格 ===== */
.tablewrap {
  min-height: 0;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.twhead {
  display: flex;
  align-items: center;
  padding: 16px 22px;
  border-bottom: 1px solid var(--color-border-light);
}

.twhead h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.twhead .cnt {
  margin-left: auto;
  font-size: 12.5px;
  color: var(--color-text-hint);
}

.thead-row,
.trow {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1.5fr 0.9fr 0.7fr 0.8fr 72px;
  align-items: center;
  gap: 12px;
  padding: 0 22px;
}

.thead-row {
  height: 44px;
  background: var(--color-bg);
  font-size: 12.5px;
  color: var(--color-text-hint);
  border-bottom: 1px solid var(--color-border-light);
}

.trow {
  height: 62px;
  border-bottom: 1px solid var(--color-border-light);
  cursor: pointer;
  transition: background 0.12s;
}

.trow:hover {
  background: var(--color-bg);
}

.task-pagination {
  min-height: 58px;
  margin-top: auto;
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

.trow .nm {
  font-size: 15px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 9px;
}

.trow .nm .ava {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-primary-pale);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.trow .ph {
  font-size: 14px;
  color: var(--color-text-sub);
  font-variant-numeric: tabular-nums;
}

.trow .idn {
  color: var(--color-text-sub);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.trow .gp,
.trow .ag {
  font-size: 13.5px;
  color: var(--color-text-sub);
}

.trow .view {
  font-size: 13px;
  color: var(--color-primary);
  text-align: right;
}

.pill {
  font-size: 12px;
  padding: 3px 11px;
  border-radius: 13px;
  font-weight: 500;
  display: inline-block;
}

.pill-match {
  background: #e9f0e7;
  color: #3d6b35;
}

.pill-unmatch {
  background: #fbf1db;
  color: #b5852a;
}

/* ===== 详情弹窗 ===== */
.mask {
  position: fixed;
  inset: 0;
  background: rgba(40, 30, 22, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 30px;
}

.modal {
  background: #fff;
  border-radius: 18px;
  width: 560px;
  max-width: 100%;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 30px 70px -20px rgba(40, 25, 15, 0.5);
}

.mhead {
  padding: 24px 28px 20px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
}

.mhead .ava {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--color-primary-pale);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  font-family: var(--font-serif);
  margin-right: 14px;
}

.mhead .ht {
  flex: 1;
  min-width: 0;
}

.mhead .ht h2 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 600;
}

.mhead .ht .sub {
  font-size: 13px;
  color: var(--color-text-hint);
  margin-top: 4px;
}

.mhead .pill {
  margin-right: 14px;
}

.mhead .mclose {
  border: 1px solid var(--color-border);
  background: #fff;
  border-radius: 9px;
  width: 34px;
  height: 34px;
  font-size: 18px;
  color: var(--color-text-hint);
  cursor: pointer;
  line-height: 1;
}

.mbody {
  padding: 22px 28px;
  overflow-y: auto;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--color-border-light);
  border: 1px solid var(--color-border-light);
  border-radius: 14px;
  overflow: hidden;
}

.info-cell {
  background: #fff;
  padding: 15px 18px;
}

.info-cell .k {
  font-size: 12px;
  color: var(--color-text-hint);
  margin-bottom: 6px;
}

.info-cell .v {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
  word-break: break-all;
}

.adv-toggle {
  margin-top: 18px;
  font-size: 13px;
  color: var(--color-text-hint);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 0;
  border-top: 1px solid var(--color-border-light);
  user-select: none;
}

.adv-toggle:hover {
  color: var(--color-primary);
}

.adv-box {
  padding-top: 6px;
}

.adv-box .warn-note {
  font-size: 12.5px;
  color: var(--color-text-sub);
  background: #fbf4e6;
  border: 1px solid #ebd9b5;
  border-radius: 10px;
  padding: 11px 14px;
  margin-bottom: 14px;
  line-height: 1.6;
}

.adv-box label {
  font-size: 12.5px;
  color: var(--color-text-hint);
  display: block;
  margin-bottom: 7px;
}

.adv-box textarea,
.adv-box input {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 11px 13px;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  margin-bottom: 14px;
  resize: vertical;
}

.adv-box textarea:focus,
.adv-box input:focus {
  border-color: var(--color-primary);
}

.adv-actions {
  display: flex;
  gap: 10px;
}

.btn-danger-ghost {
  background: #fff;
  border: 1px solid #e0c4be;
  color: var(--color-primary);
  border-radius: 10px;
  height: 40px;
  padding: 0 18px;
  font-size: 14px;
  cursor: pointer;
}

.btn-danger-ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.mfoot {
  padding: 16px 28px;
  border-top: 1px solid var(--color-border-light);
  display: flex;
  gap: 12px;
  background: var(--color-bg);
}

.mfoot .spacer {
  flex: 1;
}

.page-topbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px 12px;
  align-items: start;
}

.page-topbar-heading {
  min-width: 0;
}

.page-topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}

.page-sub {
  margin: 4px 0 0;
  color: #5f6b62;
  font-size: 13px;
}

.summary-card,
.list-card,
.detail-card {
  background: #ffffff;
  border: 1px solid rgba(16, 56, 42, 0.08);
  border-radius: 18px;
  padding: 12px 14px;
  box-shadow: 0 12px 32px rgba(16, 56, 42, 0.06);
}

.top-search-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  grid-column: 1 / -1;
  padding: 10px 12px;
  border: 1px solid rgba(16, 56, 42, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
}

.top-search-field {
  gap: 0;
}

.top-search-actions {
  align-self: stretch;
  justify-content: flex-start;
}

.summary-card {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.summary-item {
  border-radius: 16px;
  background: #f7faf7;
  padding: 10px 12px;
  display: grid;
  gap: 4px;
  min-height: 64px;
  align-content: center;
}

.summary-label {
  color: #667085;
  font-size: 11px;
}

.summary-value {
  color: #10382a;
  font-size: 16px;
  font-weight: 700;
}

.filter-field {
  display: grid;
  gap: 6px;
}

.filter-field span,
.detail-field span {
  font-size: 13px;
  color: #526158;
}

.filter-field input,
.detail-field input,
.detail-textarea {
  width: 100%;
  border: 1px solid rgba(16, 56, 42, 0.12);
  border-radius: 12px;
  padding: 8px 12px;
  font-size: 14px;
  background: #fdfefd;
}

.filter-actions,
.detail-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.list-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
}

.section-meta {
  color: #6b7280;
  font-size: 13px;
}

.identity-scroll-area {
  max-height: min(60vh, 560px);
  overflow-y: auto;
  padding-right: 6px;
  min-height: 460px;
}

.identity-scroll-area::-webkit-scrollbar {
  width: 8px;
}

.identity-scroll-area::-webkit-scrollbar-thumb {
  background: rgba(16, 56, 42, 0.18);
  border-radius: 999px;
}

.identity-scroll-area::-webkit-scrollbar-track {
  background: transparent;
}

.identity-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  align-content: start;
}

.identity-row {
  width: 100%;
  border: 1px solid rgba(16, 56, 42, 0.08);
  border-radius: 18px;
  background: #f7faf7;
  padding: 11px;
  text-align: left;
  cursor: pointer;
  display: grid;
  gap: 6px;
  align-content: start;
  min-height: 110px;
}

.identity-row.active {
  border-color: rgba(16, 56, 42, 0.3);
  background: #eef6ef;
}

.identity-row-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.identity-row-title {
  font-size: 14px;
  font-weight: 700;
  color: #10382a;
  line-height: 1.35;
  word-break: break-all;
}

.identity-row-phone {
  color: #10382a;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
  word-break: break-all;
}

.identity-row-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.identity-inline-tag {
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(16, 56, 42, 0.08);
  color: #10382a;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.2;
}

.identity-row-side-note {
  color: #667085;
  font-size: 10px;
  margin-top: auto;
}

.muted {
  color: #6b7280;
}

.status-chip,
.detail-status {
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(16, 56, 42, 0.08);
  color: #10382a;
  font-size: 11px;
  font-weight: 700;
}

.detail-title {
  font-size: 20px;
  font-weight: 700;
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
  padding: 16px;
  background: #fff;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(16, 56, 42, 0.08);
}

.detail-head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-sub {
  margin-top: 6px;
  color: #6b7280;
  font-size: 13px;
}

.detail-scroll {
  min-height: 0;
  overflow: auto;
  padding: 16px;
  display: grid;
  gap: 16px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.detail-stat {
  border-radius: 14px;
  background: #f7faf7;
  padding: 14px;
}

.detail-stat-label {
  color: #6b7280;
  font-size: 12px;
}

.detail-stat-value {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 600;
  word-break: break-all;
}

.detail-section {
  margin-top: 18px;
  display: grid;
  gap: 12px;
}

.detail-section-title {
  font-size: 15px;
  font-weight: 700;
}

.detail-field {
  display: grid;
  gap: 8px;
}

.detail-foot {
  border-top: 1px solid rgba(16, 56, 42, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.inline-error,
.inline-success,
.empty-block,
.detail-empty-block {
  border-radius: 14px;
  padding: 16px;
  font-size: 14px;
}

.inline-error {
  background: rgba(180, 46, 46, 0.08);
  color: #9f1239;
  margin-bottom: 12px;
}

.inline-success {
  background: rgba(16, 56, 42, 0.08);
  color: #166534;
  margin-bottom: 12px;
}

.empty-block {
  background: #f7faf7;
  color: #6b7280;
}

.detail-empty-block {
  height: 100%;
  display: grid;
  place-items: center;
  background: #f7faf7;
  color: #6b7280;
}

.primary-btn,
.ghost-btn,
.danger-btn {
  min-height: 42px;
  border-radius: 12px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.primary-btn {
  border: none;
  background: #135c3a !important;
  color: #ffffff !important;
}

.ghost-btn {
  border: 1px solid rgba(16, 56, 42, 0.14);
  background: #ffffff;
  color: #10382a !important;
}

.danger-btn {
  border: none;
  background: #b91c1c;
  color: #ffffff;
}

@media (max-width: 1180px) {
  .top-search-card {
    grid-template-columns: 1fr;
  }

  .summary-card {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .identity-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .page-topbar {
    grid-template-columns: 1fr;
  }

  .page-topbar-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .top-search-card {
    grid-template-columns: 1fr;
  }

  .summary-card {
    grid-template-columns: 1fr;
  }

  .identity-scroll-area {
    max-height: 50vh;
    min-height: 360px;
  }

  .identity-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .identity-row {
    min-height: 0;
  }

  .detail-overlay {
    padding: 12px;
  }

  .detail-modal {
    max-height: 94vh;
    border-radius: 18px;
  }

  .trow {
    height: auto;
    min-height: 88px;
    padding: 14px;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px 12px;
  }

  .trow .ph,
  .trow .idn,
  .trow .gp,
  .trow .ag {
    color: var(--color-text-hint);
    font-size: 12px;
  }

  .trow .ph,
  .trow .idn,
  .trow .gp {
    grid-column: 1;
  }

  .trow .ag,
  .trow > span:nth-child(6),
  .trow .view {
    grid-column: 2;
    justify-self: end;
  }

  .trow .ag {
    grid-row: 1;
  }

  .trow > span:nth-child(6) {
    grid-row: 2;
  }

  .trow .view {
    grid-row: 3;
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

  .mask {
    padding: 0;
    align-items: stretch;
  }

  .modal {
    width: 100%;
    max-width: none;
    max-height: none;
    height: 100vh;
    height: 100dvh;
    border-radius: 0;
  }

  .mhead {
    padding: 14px 12px;
  }

  .mbody {
    padding: 12px;
    overscroll-behavior: contain;
  }
}

@media (max-width: 560px) {
  .identity-list {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
