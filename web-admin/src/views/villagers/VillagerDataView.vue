<template>
  <section class="ad-page-shell">
    <div class="villager-actionbar">
      <div class="villager-searchbar">
        <input
          v-model.trim="keyword"
          type="text"
          placeholder="搜索村民姓名、手机号、村组"
          @keydown.enter.prevent="doSearch"
        />
        <button class="btn-primary btn-search" type="button" @click="doSearch">搜索</button>
        <button class="btn-ghost btn-search" type="button" @click="doReset">重置</button>
      </div>

      <div class="search-right">
        <div class="head-total">实名总数 <b>{{ Number(summary.total_count || 0) }}</b> 人</div>
        <button
          class="btn-primary"
          type="button"
          title="导出不含完整身份证号和手机号的村民脱敏名册"
          @click="identitiesRef?.handleExport()"
        >
          下载脱敏名册
        </button>
      </div>
    </div>

    <div v-if="summaryError" class="inline-error">{{ summaryError }}</div>

    <div class="hub-embedded">
      <VillagerIdentitiesView ref="identitiesRef" />
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";

import { fetchAdminVillagerIdentitySummary } from "../../api/villagers";
import { useAuthStore } from "../../stores/auth";
import { extractApiError } from "../../utils/admin-ui";
import VillagerIdentitiesView from "./VillagerIdentitiesView.vue";

const authStore = useAuthStore();

const identitiesRef = ref(null);
const keyword = ref("");
function doSearch() {
  identitiesRef.value?.searchWith(keyword.value);
}

function doReset() {
  keyword.value = "";
  identitiesRef.value?.resetFilters();
}

const summaryError = ref("");
const summary = ref({
  total_count: 0,
});

async function loadSummary() {
  if (!authStore.token) {
    return;
  }
  summaryError.value = "";
  try {
    const summaryRow = await fetchAdminVillagerIdentitySummary(authStore.token, {});
    summary.value = {
      total_count: Number(summaryRow?.total_count || 0),
    };
  } catch (error) {
    summaryError.value = extractApiError(error, "村民实名汇总加载失败，请稍后重试。");
  }
}

onMounted(() => {
  loadSummary();
});
</script>

<style scoped>
.head-total {
  font-size: 14px;
  color: var(--color-text-sub);
}

.head-total b {
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 600;
  color: var(--color-primary);
  margin: 0 3px;
  vertical-align: -1px;
}

.ad-page-shell {
  min-height: calc(100vh - 104px);
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
}

.villager-actionbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  flex-wrap: wrap;
}

.search-right {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-shrink: 0;
}

.villager-searchbar {
  flex: 0 1 640px;
  min-width: 320px;
  margin-right: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.villager-searchbar input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  font-family: inherit;
  font-size: 15px;
  background: #fff;
  color: var(--color-text);
}

.villager-searchbar .btn-search {
  flex-shrink: 0;
}

.identity-preview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 14px;
}

.identity-preview-card {
  padding: 14px;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: #fff;
}

.identity-preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.identity-preview-name {
  font-family: var(--font-serif);
  font-size: 16px;
  color: var(--color-text);
}

.identity-preview-phone {
  margin-top: 12px;
  font-size: 14px;
  color: var(--color-text-sub);
}

.identity-preview-tags {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.identity-preview-tags span {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--color-bg);
  color: var(--color-text-sub);
  font-size: 11px;
}

.hub-embedded {
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  gap: 14px;
}

.hub-embedded :deep(.villager-page) {
  height: 100%;
  min-height: 0;
}

.hub-embedded :deep(.page-topbar-heading),
.hub-embedded :deep(.ledger-page > .page-topbar > div:first-child) {
  display: none;
}

.hub-embedded :deep(.page-topbar) {
  padding: 16px 18px;
  border-radius: 12px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  box-shadow: var(--card-shadow);
}

.hub-embedded :deep(.filter-card),
.hub-embedded :deep(.list-card),
.hub-embedded :deep(.summary-card),
.hub-embedded :deep(.stats-card),
.hub-embedded :deep(.tab-card) {
  border-radius: 12px;
  border-color: var(--color-border) !important;
  box-shadow: var(--card-shadow);
}

@media (max-width: 1080px) {
  .identity-preview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .ad-page-shell {
    min-height: calc(100dvh - 82px);
    gap: 12px;
  }

  .villager-actionbar {
    align-items: stretch;
    gap: 10px;
  }

  .villager-searchbar {
    flex: 1 1 100%;
    min-width: 0;
    width: 100%;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    gap: 8px;
  }

  .search-right {
    width: 100%;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
  }

  .head-total {
    align-self: center;
  }

  .identity-preview-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .villager-searchbar {
    grid-template-columns: 1fr 1fr;
  }

  .villager-searchbar input {
    grid-column: 1 / -1;
  }

  .search-right {
    grid-template-columns: 1fr;
  }

  .search-right button {
    width: 100%;
  }
}
</style>
