<template>
  <section class="ledger-page">
    <header class="page-topbar">
      <div>
        <h2 class="page-title">村民台账中心</h2>
        <p class="page-sub">用于按领域查询村民台账、筛选重点对象、导出台账名单。</p>
      </div>
      <div class="page-topbar-actions">
        <button class="ghost-btn" type="button" :disabled="loading" @click="loadRecords(true)">
          {{ loading ? "刷新中..." : "刷新数据" }}
        </button>
        <button class="primary-btn" type="button" :disabled="exporting" @click="handleExportCurrent">
          {{ exporting ? "导出中..." : "导出当前结果" }}
        </button>
      </div>
    </header>

    <section class="notice-card">
      当前页面已从村民实名登记同步基础台账，可按年龄自动筛出今年即将满60岁、已满60岁、已满80岁等重点对象。
    </section>

    <section class="tab-card">
      <button
        v-for="tab in ledgerTabsConfig"
        :key="tab.key"
        class="tab-chip"
        :class="{ active: activeTab === tab.key }"
        type="button"
        @click="selectTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </section>

    <section class="filter-card">
      <div class="filter-row">
        <label class="filter-field filter-field-keyword">
          <span>关键词</span>
          <input
            v-model.trim="filters.keyword"
            type="text"
            placeholder="搜索姓名、手机号、身份证号、村组"
            @keydown.enter.prevent="applyFilters"
          />
        </label>
        <div class="filter-actions">
          <button class="primary-btn" type="button" @click="applyFilters">搜索</button>
          <button class="ghost-btn" type="button" @click="resetFilters">重置</button>
        </div>
      </div>

      <div class="quick-filter-wrap">
        <div class="quick-filter-label">快捷筛选</div>
        <div class="quick-filter-list">
          <button
            v-for="item in currentQuickFilters"
            :key="item.key"
            class="quick-filter-chip"
            :class="{ active: activeQuickFilter === item.key }"
            type="button"
            @click="toggleQuickFilter(item.key)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>
    </section>

    <section class="stats-card">
      <article v-for="item in currentStats" :key="item.key" class="stat-item">
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-value">{{ item.value(filteredRecords) }}</div>
      </article>
    </section>

    <section class="list-card">
      <div class="list-card-head">
        <div>
          <div class="section-title">查询结果</div>
          <div class="section-sub">{{ currentTabLabel }}领域重点对象查询结果</div>
        </div>
        <div class="section-meta">当前共 {{ filteredRecords.length }} 条</div>
      </div>

      <div v-if="statusMessage" class="inline-success">{{ statusMessage }}</div>
      <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
      <div v-if="loading" class="empty-block">正在刷新台账数据...</div>
      <div v-else-if="!filteredRecords.length" class="empty-block">当前筛选条件下暂无台账记录。</div>

      <div v-else class="table-wrap">
        <table class="ledger-table">
          <thead>
            <tr>
              <th v-for="column in currentColumns" :key="column.key">{{ column.label }}</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in filteredRecords" :key="record.id">
              <td v-for="column in currentColumns" :key="`${record.id}-${column.key}`">
                {{ column.value(record) }}
              </td>
              <td>
                <button class="table-link" type="button" @click="openDrawer(record)">查看台账</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="drawerVisible" class="drawer-backdrop" @click="closeDrawer"></div>
    <aside v-if="drawerVisible" class="drawer-shell">
      <section class="drawer-card" @click.stop>
        <header class="drawer-head">
          <div>
            <h3 class="drawer-title">{{ activeRecord?.real_name || "台账详情" }}</h3>
            <p class="drawer-subtitle">{{ currentTabLabel }}领域完整台账信息</p>
          </div>
          <button class="drawer-close" type="button" @click="closeDrawer">关闭</button>
        </header>

        <div class="drawer-body">
          <section v-for="section in currentDetailSections" :key="section.key" class="detail-section">
            <div class="detail-section-title">{{ section.title }}</div>
            <div class="detail-grid">
              <div v-for="field in section.fields" :key="field.label" class="detail-item">
                <div class="detail-label">{{ field.label }}</div>
                <div class="detail-value">{{ formatFieldValue(field.value(activeRecord)) }}</div>
              </div>
            </div>
          </section>
        </div>
      </section>
    </aside>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import { downloadBlobFile } from "../../api/http";
import { listAdminVillagerIdentities } from "../../api/villagers";
import { useAuthStore } from "../../stores/auth";
import { extractApiError } from "../../utils/admin-ui";
import { useTransientMessage } from "../../utils/success-toast";
import {
  ledgerColumnsConfig,
  ledgerDetailSectionsConfig,
  ledgerFilterConfig,
  ledgerStatsConfig,
  ledgerTabsConfig,
} from "./ledger-config";

const authStore = useAuthStore();
const loading = ref(false);
const exporting = ref(false);
const errorMessage = ref("");
const statusMessage = useTransientMessage();
const activeTab = ref("civil");
const appliedKeyword = ref("");
const activeQuickFilter = ref("");
const drawerVisible = ref(false);
const activeRecord = ref(null);
const records = ref([]);

const filters = reactive({
  keyword: "",
});

function parseBirthDateText(value) {
  const text = String(value || "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return text;
  }
  const idCardText = text.toUpperCase();
  const birthText = /^\d{17}[\dX]$/.test(idCardText)
    ? idCardText.slice(6, 14)
    : /^\d{15}$/.test(idCardText)
      ? `19${idCardText.slice(6, 12)}`
      : "";
  if (!birthText) {
    return "";
  }
  const year = birthText.slice(0, 4);
  const month = birthText.slice(4, 6);
  const day = birthText.slice(6, 8);
  const date = new Date(Number(year), Number(month) - 1, Number(day));
  if (
    date.getFullYear() !== Number(year) ||
    date.getMonth() !== Number(month) - 1 ||
    date.getDate() !== Number(day)
  ) {
    return "";
  }
  return `${year}-${month}-${day}`;
}

function calculateAge(birthDateText) {
  if (!birthDateText) {
    return null;
  }
  const [year, month, day] = birthDateText.split("-").map((item) => Number(item));
  const today = new Date();
  let age = today.getFullYear() - year;
  if (today.getMonth() + 1 < month || (today.getMonth() + 1 === month && today.getDate() < day)) {
    age -= 1;
  }
  return age >= 0 && age <= 130 ? age : null;
}

function willTurn60ThisYear(birthDateText) {
  if (!birthDateText) {
    return false;
  }
  const [year, month, day] = birthDateText.split("-").map((item) => Number(item));
  const today = new Date();
  return (
    year === today.getFullYear() - 60 &&
    (today.getMonth() + 1 < month || (today.getMonth() + 1 === month && today.getDate() < day))
  );
}

function normalizeLedgerRecord(row) {
  const birthDate = parseBirthDateText(row?.birth_date);
  const rawAge = row?.age;
  const apiAge = rawAge === null || rawAge === undefined || rawAge === "" ? NaN : Number(rawAge);
  const age = Number.isFinite(apiAge) ? apiAge : calculateAge(birthDate);
  const isAge60Plus = Boolean(row?.is_age_60_plus) || (Number.isFinite(age) && age >= 60);
  const isAge80Plus = Boolean(row?.is_age_80_plus) || (Number.isFinite(age) && age >= 80);
  const isTurning60ThisYear = Boolean(row?.is_turning_60_this_year) || willTurn60ThisYear(birthDate);

  return {
    id: Number(row?.user_id || row?.id || 0),
    user_id: Number(row?.user_id || row?.id || 0),
    real_name: row?.real_name || "",
    gender: row?.gender || "",
    phone_masked: row?.phone_masked || "",
    id_card_masked: row?.id_card_masked || "",
    birth_date: birthDate,
    village_group: row?.village_group || "",
    auth_status: row?.auth_status || "",
    roster_match_status: row?.roster_match_status || "",
    age,
    is_turning_60_this_year: isTurning60ThisYear,
    is_age_60_plus: isAge60Plus,
    is_age_80_plus: isAge80Plus,
    updated_at: row?.updated_at || "",
    updated_by: "实名登记同步",
    remarks: "来自村民实名登记，民政/医保/农业/社保/环境专项信息可后续补录。",
    statuses: {
      civil: "实名已同步",
      medical: "待补录",
      agriculture: "待补录",
      social: "待补录",
      environment: "待补录",
    },
    civil: {
      is_dibao: false,
      is_tekun: false,
      is_lonely_elder: false,
      disability_status: "",
      needs_temp_help: false,
      hardship_type: "",
      remark: isTurning60ThisYear
        ? "今年将满60岁，已纳入民政年龄提醒。"
        : isAge80Plus
          ? "已满80岁，已纳入高龄老人提醒。"
          : isAge60Plus
            ? "已满60岁，已纳入老人年龄提醒。"
            : "",
    },
    medical: {},
    agriculture: {},
    social: {},
    environment: {},
  };
}

const currentQuickFilters = computed(() => ledgerFilterConfig[activeTab.value] || []);
const currentStats = computed(() => ledgerStatsConfig[activeTab.value] || []);
const currentColumns = computed(() => ledgerColumnsConfig[activeTab.value] || []);
const currentDetailSections = computed(() => ledgerDetailSectionsConfig[activeTab.value] || []);
const currentTabLabel = computed(
  () => ledgerTabsConfig.find((item) => item.key === activeTab.value)?.label || "民政"
);

const visibleRecords = computed(() => {
  const keyword = appliedKeyword.value.trim().toLowerCase();
  if (!keyword) {
    return records.value;
  }
  return records.value.filter((item) => {
    const haystacks = [
      item.real_name,
      item.phone_masked,
      item.id_card_masked,
      item.village_group,
    ]
      .map((value) => String(value || "").toLowerCase())
      .filter(Boolean);
    return haystacks.some((value) => value.includes(keyword));
  });
});

const filteredRecords = computed(() => {
  const activeFilter = currentQuickFilters.value.find((item) => item.key === activeQuickFilter.value);
  if (!activeFilter) {
    return visibleRecords.value;
  }
  return visibleRecords.value.filter((item) => activeFilter.predicate(item));
});

function applyFilters() {
  appliedKeyword.value = filters.keyword.trim();
  statusMessage.value = "";
}

function resetFilters() {
  filters.keyword = "";
  appliedKeyword.value = "";
  activeQuickFilter.value = "";
  statusMessage.value = "";
}

function selectTab(tabKey) {
  if (activeTab.value === tabKey) {
    return;
  }
  activeTab.value = tabKey;
  activeQuickFilter.value = "";
  closeDrawer();
}

function toggleQuickFilter(filterKey) {
  activeQuickFilter.value = activeQuickFilter.value === filterKey ? "" : filterKey;
  closeDrawer();
}

function openDrawer(record) {
  activeRecord.value = record;
  drawerVisible.value = true;
}

function closeDrawer() {
  drawerVisible.value = false;
  activeRecord.value = null;
}

function formatFieldValue(value) {
  if (Array.isArray(value)) {
    return value.length ? value.join("、") : "-";
  }
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function buildExportRows() {
  const exportSections = currentDetailSections.value;
  return filteredRecords.value.map((record) => {
    const row = {};
    exportSections.forEach((section) => {
      section.fields.forEach((field) => {
        row[field.label] = formatFieldValue(field.value(record));
      });
    });
    return row;
  });
}

function buildCsv(rows) {
  if (!rows.length) {
    return "";
  }
  const headers = Object.keys(rows[0]);
  const escape = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const lines = [headers.map(escape).join(",")];
  rows.forEach((row) => {
    lines.push(headers.map((header) => escape(row[header])).join(","));
  });
  return `\ufeff${lines.join("\n")}`;
}

async function handleExportCurrent() {
  exporting.value = true;
  errorMessage.value = "";
  statusMessage.value = "";
  try {
    const rows = buildExportRows();
    if (!rows.length) {
      statusMessage.value = "当前筛选结果为空，无可导出数据。";
      return;
    }
    const csv = buildCsv(rows);
    const filename = `村民台账中心_${currentTabLabel.value}_当前结果.csv`;
    downloadBlobFile(csv, filename, "text/csv;charset=utf-8");
    statusMessage.value = "当前筛选结果已开始导出。";
  } catch (error) {
    errorMessage.value = "导出当前结果失败，请稍后重试。";
  } finally {
    exporting.value = false;
  }
}

async function loadRecords(showFeedback = false) {
  loading.value = true;
  errorMessage.value = "";
  closeDrawer();
  try {
    const rows = await listAdminVillagerIdentities(authStore.token, { limit: 500 });
    records.value = Array.isArray(rows) ? rows.map(normalizeLedgerRecord).filter((item) => item.id > 0) : [];
    statusMessage.value = showFeedback ? `已同步 ${records.value.length} 条实名记录到村民台账中心。` : "";
  } catch (error) {
    errorMessage.value = extractApiError(error, "加载台账数据失败，请稍后重试。");
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadRecords(false);
});
</script>

<style scoped>
.ledger-page {
  display: grid;
  gap: 16px;
}

.page-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-topbar-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
}

.page-sub {
  margin: 6px 0 0;
  color: #7a6e64;
  font-size: 14px;
}

.notice-card,
.tab-card,
.filter-card,
.stats-card,
.list-card,
.drawer-card {
  background: #ffffff;
  border: 1px solid #efe8da;
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 12px 32px rgba(82, 56, 35, 0.06);
}

.notice-card {
  color: #5c5047;
  line-height: 1.6;
  background: #ffffff;
}

.tab-card {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.tab-chip,
.quick-filter-chip {
  border: 1px solid #efe8da;
  background: #ffffff;
  color: #5c5047;
  border-radius: 999px;
  padding: 12px 20px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}

.tab-chip.active,
.quick-filter-chip.active {
  background: #f5e8e6;
  border-color: #e8c9c4;
  color: #8a2e22;
}

.filter-card {
  display: grid;
  gap: 16px;
}

.filter-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: end;
}

.filter-field {
  display: grid;
  gap: 8px;
}

.filter-field span {
  font-size: 13px;
  color: #7a6e64;
}

.filter-field input {
  width: 100%;
  border: 1px solid #efe8da;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 14px;
  background: #fffdf8;
}

.filter-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.quick-filter-wrap {
  display: grid;
  gap: 10px;
}

.quick-filter-label {
  font-size: 13px;
  color: #7a6e64;
}

.quick-filter-list {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.stats-card {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.stat-item {
  border-radius: 16px;
  background: #ffffff;
  padding: 16px;
  display: grid;
  gap: 8px;
}

.stat-label {
  color: #7a6e64;
  font-size: 13px;
}

.stat-value {
  color: #a63d2f;
  font-size: 26px;
  font-weight: 700;
}

.list-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
}

.section-sub,
.section-meta {
  margin-top: 4px;
  color: #7a6e64;
  font-size: 13px;
}

.inline-error,
.inline-success,
.empty-block {
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
  background: #eff4e8;
  color: #3d6b35;
  margin-bottom: 12px;
}

.empty-block {
  background: #ffffff;
  color: #7a6e64;
}

.table-wrap {
  overflow-x: auto;
}

.ledger-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 980px;
}

.ledger-table th,
.ledger-table td {
  padding: 14px 12px;
  border-bottom: 1px solid #efe8da;
  text-align: left;
  font-size: 14px;
  vertical-align: top;
}

.ledger-table th {
  color: #7a6e64;
  font-size: 13px;
  font-weight: 700;
  background: #ffffff;
}

.table-link {
  border: none;
  background: transparent;
  color: #a63d2f;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}

.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(16, 24, 40, 0.38);
  z-index: 50;
}

.drawer-shell {
  position: fixed;
  top: 0;
  right: 0;
  width: min(720px, 100vw);
  height: 100vh;
  z-index: 51;
  padding: 16px 16px 16px 0;
}

.drawer-card {
  height: 100%;
  border-radius: 26px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
}

.drawer-head {
  padding: 20px 22px 16px;
  border-bottom: 1px solid #efe8da;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.drawer-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}

.drawer-subtitle {
  margin: 6px 0 0;
  color: #7a6e64;
  font-size: 13px;
}

.drawer-close {
  border: 1px solid #efe8da;
  background: #ffffff;
  color: #1a1612;
  border-radius: 10px;
  min-height: 40px;
  padding: 0 14px;
  cursor: pointer;
}

.drawer-body {
  min-height: 0;
  overflow: auto;
  padding: 18px 22px 22px;
  display: grid;
  gap: 16px;
}

.detail-section {
  display: grid;
  gap: 12px;
}

.detail-section-title {
  font-size: 15px;
  font-weight: 700;
  color: #8a2e22;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-item {
  border-radius: 14px;
  background: #ffffff;
  padding: 14px;
}

.detail-label {
  color: #7a6e64;
  font-size: 12px;
}

.detail-value {
  margin-top: 8px;
  color: #1a1612;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
  word-break: break-word;
}

@media (max-width: 1240px) {
  .stats-card {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .page-topbar,
  .list-card-head {
    flex-direction: column;
    align-items: stretch;
  }

  .page-topbar-actions,
  .filter-actions {
    justify-content: flex-start;
  }

  .filter-row {
    grid-template-columns: minmax(0, 1fr);
  }

  .stats-card {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .drawer-shell {
    width: 100vw;
    padding: 0;
  }

  .drawer-card {
    border-radius: 0;
  }

  .drawer-shell {
    height: 100vh;
    height: 100dvh;
  }

  .drawer-body {
    padding-bottom: calc(22px + env(safe-area-inset-bottom));
    overscroll-behavior: contain;
  }
}

@media (max-width: 640px) {
  .stats-card {
    grid-template-columns: minmax(0, 1fr);
  }

  .tab-card,
  .quick-filter-list {
    gap: 8px;
    flex-wrap: nowrap;
    overflow-x: auto;
    overscroll-behavior-inline: contain;
  }

  .tab-chip,
  .quick-filter-chip {
    width: auto;
    min-width: max-content;
    text-align: center;
  }

  .filter-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-actions button,
  .page-topbar-actions button {
    min-height: 44px;
  }

  .page-topbar-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .table-wrap {
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-inline: contain;
  }

  .drawer-head {
    padding: 14px 12px;
  }

  .drawer-body {
    padding: 12px 12px calc(12px + env(safe-area-inset-bottom));
  }
}
</style>
