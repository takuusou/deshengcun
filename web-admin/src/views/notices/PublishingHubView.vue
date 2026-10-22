<template>
  <section class="publish-page">
    <section class="publish-workspace">
      <aside class="publish-filter">
        <div class="filter-block">
          <div class="filter-title">发布类型</div>
          <button
            v-for="item in publishTypes"
            :key="item.value"
            class="type-card"
            :class="{ active: activeType === item.value }"
            type="button"
            @click="pickType(item.value)"
          >
            <span class="type-dot"></span>
            <span>{{ item.label }}</span>
            <em>{{ typeBadge(item.value) }}</em>
          </button>
        </div>
      </aside>

      <main class="publish-panel">
        <template v-if="activeType === 'notice'">
          <div class="publish-panel-head">
            <div>
              <h2>通知公告</h2>
              <p>共 {{ typeBadge("notice") }} 条</p>
            </div>
            <div class="publish-head-search">
              <input
                v-model.trim="noticeSearchDraft"
                type="text"
                placeholder="搜索标题或通知内容"
                @keydown.enter.prevent="searchNotices"
              />
              <button class="btn-primary" type="button" @click="searchNotices">搜索</button>
            </div>
            <div class="panel-head-actions">
              <button class="btn-primary" type="button" :disabled="!canWrite" @click="noticesRef?.startCreate()">新建通知</button>
            </div>
          </div>
          <div class="embedded-view list-embedded-view">
            <NoticesView ref="noticesRef" />
          </div>
        </template>

        <template v-else-if="activeType === 'open'">
          <div class="publish-panel-head">
            <div>
              <h2>数字公开</h2>
              <p>维护公开页四指标、村部照片和村情简介。</p>
            </div>
            <div class="panel-head-actions">
              <button class="btn-primary" type="button" :disabled="!canWrite || metricsSaving || villagePhotoUploading" @click="saveMetrics">
                {{ metricsSaving ? "保存中" : "保存" }}
              </button>
            </div>
          </div>

          <div v-if="openFeedbackText" class="inline-success">{{ openFeedbackText }}</div>
          <div v-if="openError" class="inline-error">{{ openError }}</div>
          <div v-if="metricsLoading" class="empty-state">正在加载数字公开资料...</div>
          <template v-else>
            <section class="profile-card">
              <div class="profile-photo-block">
                <span>村部图片</span>
                <div class="profile-photo-frame">
                  <button
                    class="profile-photo-preview"
                    :class="{ empty: !profileDraft.village_photo_url }"
                    type="button"
                    :disabled="villagePhotoUploading || (!profileDraft.village_photo_url && !canWrite)"
                    @click="handleVillagePhotoClick"
                  >
                    <img v-if="profileDraft.village_photo_url" :src="profileDraft.village_photo_url" alt="村部照片" />
                    <span v-else>{{ villagePhotoUploading ? "上传中" : "点击上传图片" }}</span>
                  </button>
                  <button
                    v-if="profileDraft.village_photo_url && canWrite"
                    class="profile-photo-remove"
                    type="button"
                    title="移除村部图片"
                    aria-label="移除村部图片"
                    @click.stop="removeVillagePhoto"
                  >
                    ×
                  </button>
                </div>
                <input ref="villagePhotoInputRef" class="hidden-file-input" type="file" accept="image/*" @change="handleVillagePhotoPicked" />
              </div>

              <label class="profile-intro-field">
                <span>村情简介</span>
                <textarea
                  v-model.trim="profileDraft.village_intro"
                  rows="8"
                  :disabled="!canWrite || metricsSaving"
                  placeholder="请输入村情简介"
                />
              </label>
            </section>

            <div v-if="photoPreviewOpen && profileDraft.village_photo_url" class="photo-preview-overlay" @click="closePhotoPreview">
              <img :src="profileDraft.village_photo_url" alt="村部图片预览" @click.stop />
              <button class="photo-preview-close" type="button" aria-label="关闭图片预览" @click="closePhotoPreview">×</button>
            </div>

            <section class="metrics-grid">
              <article v-for="(item, index) in metricDraft" :key="`${item.metric_key || index}`" class="metric-card">
                <label>指标名称</label>
                <input v-model.trim="item.metric_label" type="text" :disabled="!canWrite || metricsSaving" placeholder="如：村组" />
                <label>指标数值</label>
                <input v-model.trim="item.metric_value" type="text" :disabled="!canWrite || metricsSaving" placeholder="请输入纯数字，如：9" />
              </article>
              <div v-if="!metricDraft.length" class="empty-state slim">暂无指标，请刷新后重试。</div>
            </section>
          </template>
        </template>

        <template v-else-if="activeType === 'shop'">
          <div class="publish-panel-head">
            <div>
              <h2>本地好物</h2>
              <p>共 {{ typeBadge("shop") }} 条</p>
            </div>
            <div class="panel-head-actions">
              <button class="btn-primary" type="button" :disabled="!canWrite" @click="shopRef?.startCreate()">新增好物</button>
            </div>
          </div>
          <div class="embedded-view list-embedded-view">
            <ShopProductsView ref="shopRef" />
          </div>
        </template>

        <template v-else-if="activeType === 'job'">
          <div class="publish-panel-head">
            <div>
              <h2>就业培训</h2>
              <p>共 {{ typeBadge("job") }} 条</p>
            </div>
            <div class="publish-head-search">
              <input
                v-model.trim="trainingSearchDraft"
                type="text"
                placeholder="搜索培训标题、地点或对象"
                @keydown.enter.prevent="searchTraining"
              />
              <button class="btn-primary" type="button" @click="searchTraining">搜索</button>
            </div>
            <div class="panel-head-actions">
              <button class="btn-primary" type="button" :disabled="!canWrite" @click="trainingRef?.startCreate()">新建培训</button>
            </div>
          </div>
          <div class="embedded-view list-embedded-view">
            <TrainingProgramsView ref="trainingRef" />
          </div>
        </template>

        <template v-else-if="activeType === 'volunteer'">
          <div class="publish-panel-head">
            <div>
              <h2>志愿活动</h2>
              <p>共 {{ typeBadge("volunteer") }} 条</p>
            </div>
            <div class="publish-head-search">
              <input
                v-model.trim="volunteerSearchDraft"
                type="text"
                placeholder="搜索活动标题、地点或对象"
                @keydown.enter.prevent="searchVolunteer"
              />
              <button class="btn-primary" type="button" @click="searchVolunteer">搜索</button>
            </div>
            <div class="panel-head-actions">
              <button class="btn-primary" type="button" :disabled="!canWrite" @click="volunteerRef?.startCreate()">新建活动</button>
            </div>
          </div>
          <div class="embedded-view list-embedded-view">
            <VolunteerActivitiesView ref="volunteerRef" />
          </div>
        </template>
      </main>
    </section>
  </section>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { listAdminNotices } from "../../api/notices";
import { getAdminOpenProfile, listAdminMetrics, updateAdminMetrics, updateAdminOpenProfile } from "../../api/open";
import { listAdminTrainingPrograms } from "../../api/training";
import { uploadAdminImage } from "../../api/uploads";
import { listAdminVolunteerActivities } from "../../api/volunteer";
import { listAdminProducts } from "../../api/products";
import { useAuthStore } from "../../stores/auth";
import { extractApiError } from "../../utils/admin-ui";
import { useTransientMessage } from "../../utils/success-toast";
import TrainingProgramsView from "../training/TrainingProgramsView.vue";
import VolunteerActivitiesView from "../volunteer/VolunteerActivitiesView.vue";
import ShopProductsView from "../shop/ShopProductsView.vue";
import NoticesView from "./NoticesView.vue";

const ConstructionPanel = defineComponent({
  name: "ConstructionPanel",
  props: {
    title: { type: String, required: true },
    text: { type: String, required: true },
  },
  setup(props) {
    return () =>
      h("section", { class: "construction-card" }, [
        h("div", { class: "construction-icon" }, "建"),
        h("div", [h("h2", props.title), h("p", props.text)]),
        h("div", { class: "placeholder-list" }, [
          h("div"),
          h("div"),
          h("div"),
        ]),
      ]);
  },
});

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();

const publishTypes = [
  { value: "notice", label: "通知公告" },
  { value: "open", label: "数字公开" },
  { value: "shop", label: "本地好物" },
  { value: "job", label: "就业培训" },
  { value: "volunteer", label: "志愿活动" },
];

const activeType = ref(routeToType(route.name));
const noticesRef = ref(null);
const trainingRef = ref(null);
const volunteerRef = ref(null);
const shopRef = ref(null);
const summaryLoading = ref(false);
const noticeRows = ref([]);
const trainingRows = ref([]);
const volunteerRows = ref([]);
const shopRows = ref([]);
const noticeSearchDraft = ref("");
const trainingSearchDraft = ref("");
const volunteerSearchDraft = ref("");
const metricDraft = ref([]);
const profileDraft = ref({
  village_intro: "",
  village_photo_url: "",
});
const metricsLoading = ref(false);
const metricsSaving = ref(false);
const villagePhotoUploading = ref(false);
const villagePhotoInputRef = ref(null);
const photoPreviewOpen = ref(false);
const openError = ref("");
const openFeedbackText = useTransientMessage();

const canWrite = computed(() => ["super_admin", "cadre"].includes(authStore.user?.role_key || ""));

function routeToType(name) {
  const routeName = String(name || "notices");
  if (routeName === "volunteer-events") return "volunteer";
  if (routeName === "training-programs") return "job";
  if (routeName === "open") return "open";
  return "notice";
}

function typeBadge(type) {
  if (type === "notice") return noticeRows.value.length;
  if (type === "volunteer") return volunteerRows.value.length;
  if (type === "job") return trainingRows.value.length;
  if (type === "shop") return shopRows.value.length;
  if (type === "open") return metricDraft.value.length;
  return "待建";
}

function searchNotices() {
  noticesRef.value?.searchByKeyword(noticeSearchDraft.value);
}

function searchTraining() {
  trainingRef.value?.searchByKeyword(trainingSearchDraft.value);
}

function searchVolunteer() {
  volunteerRef.value?.searchByKeyword(volunteerSearchDraft.value);
}

async function pickType(type) {
  activeType.value = type;
  if (type === "notice" && route.name !== "notices") {
    await router.replace({ name: "notices" });
  } else if (type === "volunteer" && route.name !== "volunteer-events") {
    await router.replace({ name: "volunteer-events" });
  } else if (type === "job" && route.name !== "training-programs") {
    await router.replace({ name: "training-programs" });
  } else if (type === "open" && route.name !== "open") {
    await router.replace({ name: "open" });
  }
  if (type === "open" && !metricDraft.value.length) {
    loadMetrics();
  }
}

function normalizeMetricRows(rows = []) {
  return (rows || []).slice(0, 4).map((item) => ({
    metric_key: item.metric_key || "",
    metric_label: item.metric_label || "",
    metric_value: item.metric_value || "",
  }));
}

function applyProfileDraft(profile = {}) {
  profileDraft.value = {
    village_intro: String(profile.village_intro || "").trim(),
    village_photo_url: String(profile.village_photo_url || "").trim(),
  };
}

function loadImageElement(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = (error) => {
      URL.revokeObjectURL(url);
      reject(error);
    };
    image.src = url;
  });
}

async function compressImageToWebp(file) {
  if (!file || !file.type?.startsWith("image/")) {
    return file;
  }
  try {
    const image = await loadImageElement(file);
    const maxWidth = 1600;
    const maxHeight = 900;
    const scale = Math.min(1, maxWidth / image.naturalWidth, maxHeight / image.naturalHeight);
    const width = Math.max(1, Math.round(image.naturalWidth * scale));
    const height = Math.max(1, Math.round(image.naturalHeight * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) {
      return file;
    }
    context.drawImage(image, 0, 0, width, height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/webp", 0.82));
    if (!blob) {
      return file;
    }
    const basename = String(file.name || "village-photo").replace(/\.[^.]+$/, "");
    return new File([blob], `${basename}.webp`, { type: "image/webp" });
  } catch (_) {
    return file;
  }
}

async function loadMetrics() {
  metricsLoading.value = true;
  openError.value = "";
  try {
    const [rows, profile] = await Promise.all([
      listAdminMetrics(authStore.token),
      getAdminOpenProfile(authStore.token),
    ]);
    metricDraft.value = normalizeMetricRows(rows);
    applyProfileDraft(profile);
  } catch (error) {
    openError.value = extractApiError(error, "数字公开资料加载失败");
  } finally {
    metricsLoading.value = false;
  }
}

async function saveMetrics() {
  if (!canWrite.value) return;
  metricsSaving.value = true;
  openError.value = "";
  openFeedbackText.value = "";
  try {
    const items = metricDraft.value
      .map((item) => ({
        metric_key: item.metric_key || "",
        metric_label: String(item.metric_label || "").trim(),
        metric_value: String(item.metric_value || "").trim(),
      }))
      .filter((item) => item.metric_label && item.metric_value);
    if (!items.length) {
      openError.value = "请至少保留一项公开指标。";
      return;
    }
    const [rows, profile] = await Promise.all([
      updateAdminMetrics(authStore.token, { items }),
      updateAdminOpenProfile(authStore.token, {
        village_intro: profileDraft.value.village_intro,
        village_photo_url: profileDraft.value.village_photo_url,
      }),
    ]);
    metricDraft.value = normalizeMetricRows(rows);
    applyProfileDraft(profile);
    openFeedbackText.value = "数字公开资料已保存。";
  } catch (error) {
    openError.value = extractApiError(error, "数字公开资料保存失败");
  } finally {
    metricsSaving.value = false;
  }
}

function pickVillagePhoto() {
  villagePhotoInputRef.value?.click();
}

function handleVillagePhotoClick() {
  if (profileDraft.value.village_photo_url) {
    photoPreviewOpen.value = true;
    return;
  }
  pickVillagePhoto();
}

function closePhotoPreview() {
  photoPreviewOpen.value = false;
}

async function handleVillagePhotoPicked(event) {
  const file = event?.target?.files?.[0];
  if (event?.target) {
    event.target.value = "";
  }
  if (!file) return;
  villagePhotoUploading.value = true;
  openError.value = "";
  openFeedbackText.value = "";
  try {
    const uploadFile = await compressImageToWebp(file);
    const result = await uploadAdminImage(authStore.token, uploadFile, "open");
    profileDraft.value = {
      ...profileDraft.value,
      village_photo_url: result?.url || "",
    };
    openFeedbackText.value = "村部照片已上传并压缩，点击保存后同步到村民端。";
  } catch (error) {
    openError.value = extractApiError(error, "村部照片上传失败");
  } finally {
    villagePhotoUploading.value = false;
  }
}

function removeVillagePhoto() {
  profileDraft.value = {
    ...profileDraft.value,
    village_photo_url: "",
  };
  photoPreviewOpen.value = false;
}

async function loadSummary() {
  if (!authStore.token) return;
  summaryLoading.value = true;
  try {
    const [notices, trainings, volunteers, products, metrics, profile] = await Promise.all([
      listAdminNotices(authStore.token, {}),
      listAdminTrainingPrograms(authStore.token, {}),
      listAdminVolunteerActivities(authStore.token, {}),
      listAdminProducts(authStore.token),
      listAdminMetrics(authStore.token),
      getAdminOpenProfile(authStore.token),
    ]);
    noticeRows.value = Array.isArray(notices) ? notices : [];
    trainingRows.value = Array.isArray(trainings) ? trainings : [];
    volunteerRows.value = Array.isArray(volunteers) ? volunteers : [];
    shopRows.value = Array.isArray(products) ? products : [];
    metricDraft.value = normalizeMetricRows(metrics);
    applyProfileDraft(profile);
  } catch (error) {
    openError.value = extractApiError(error, "发布管理数据加载失败");
  } finally {
    summaryLoading.value = false;
  }
}

watch(
  () => route.name,
  () => {
    const nextType = routeToType(route.name);
    if (["notice", "open", "job", "volunteer"].includes(nextType)) {
      activeType.value = nextType;
    }
  },
  { immediate: true }
);

onMounted(() => {
  loadSummary();
});
</script>

<style scoped>
.publish-page {
  display: grid;
  gap: 16px;
}

.publish-workspace {
  min-height: calc(100vh - 104px);
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
}

.publish-filter,
.publish-panel {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  box-shadow: var(--card-shadow);
}

.publish-filter {
  padding: 18px 16px;
}

.filter-block + .filter-block {
  margin-top: 22px;
}

.filter-title {
  margin-bottom: 11px;
  color: var(--color-text-hint);
  font-size: 12px;
  letter-spacing: 0.14em;
}

.type-card {
  width: 100%;
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 9px;
  border-radius: 10px;
  color: var(--color-text-sub);
  padding: 0 12px;
  font-size: 13px;
}

.type-card.active {
  background: var(--color-primary-pale);
  color: var(--color-primary);
  font-weight: 600;
}

.type-card:focus,
.type-card:focus-visible {
  outline: none;
}

.type-card em {
  margin-left: auto;
  color: var(--color-text-hint);
  font-style: normal;
  font-size: 12px;
}

.type-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--color-text-hint);
}

.type-card.active .type-dot {
  background: var(--color-primary);
}

.publish-panel {
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.publish-panel-head {
  min-height: 68px;
  padding: 15px 20px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  gap: 14px;
}

.publish-head-search {
  flex: 1;
  min-width: 360px;
  margin-left: clamp(48px, 6vw, 120px);
  display: flex;
  align-items: center;
  gap: 10px;
}

.publish-head-search input {
  flex: 1;
  min-width: 0;
}

.panel-head-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.publish-panel-head h2 {
  margin: 0;
  font-size: 16px;
}

.publish-panel-head p {
  margin: 5px 0 0;
  color: var(--color-text-hint);
  font-size: 12px;
}

.embedded-view {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px;
}

.list-embedded-view {
  display: flex;
  overflow: hidden;
  padding: 0;
}

.list-embedded-view :deep(.notices-page),
.list-embedded-view :deep(.training-admin-page) {
  width: 100%;
  height: 100%;
  min-height: 0;
  gap: 0;
}

.embedded-view :deep(.notices-page),
.embedded-view :deep(.events-page) {
  gap: 12px;
}

.embedded-view :deep(.page-topbar) {
  margin: 0;
}

.profile-card {
  margin: 18px 20px 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.profile-photo-block,
.profile-intro-field {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
}

.profile-photo-block {
  grid-column: span 1;
}

.profile-intro-field {
  grid-column: span 3;
}

.profile-photo-frame {
  position: relative;
  height: 240px;
}

.profile-photo-preview {
  width: 100%;
  height: 100%;
  padding: 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  background: #ffffff;
  display: grid;
  place-items: center;
  color: var(--color-text-hint);
  font-size: 13px;
  cursor: pointer;
}

.profile-photo-preview:disabled {
  cursor: default;
}

.profile-photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.profile-photo-remove {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 50%;
  background: rgba(24, 24, 24, 0.72);
  color: #fff;
  font-size: 20px;
  line-height: 1;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.16s ease;
}

.profile-photo-frame:hover .profile-photo-remove,
.profile-photo-remove:focus-visible {
  opacity: 1;
  pointer-events: auto;
}

.hidden-file-input {
  display: none;
}

.profile-photo-block > span,
.profile-intro-field span {
  color: var(--color-text-hint);
  font-size: 12px;
}

.profile-intro-field textarea {
  width: 100%;
  height: 240px;
  min-height: 240px;
  resize: none;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 12px 14px;
  box-sizing: border-box;
  color: var(--color-text);
  background: #fff;
  line-height: 1.7;
}

.photo-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  padding: 48px;
  background: rgba(20, 20, 20, 0.76);
  display: grid;
  place-items: center;
}

.photo-preview-overlay img {
  max-width: min(1100px, 92vw);
  max-height: 86vh;
  object-fit: contain;
}

.photo-preview-close {
  position: fixed;
  top: 24px;
  right: 28px;
  width: 38px;
  height: 38px;
  padding: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-size: 28px;
  line-height: 1;
}

.metrics-grid {
  padding: 18px 20px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  display: grid;
  gap: 8px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: #ffffff;
}

.metric-card label {
  color: var(--color-text-hint);
  font-size: 12px;
}

.construction-card {
  margin: 0 20px 20px;
  padding: 18px 20px;
  border-radius: 14px;
  border: 1px solid var(--color-border);
  background: #ffffff;
}

.construction-card h2 {
  margin: 0 0 8px;
  font-size: 16px;
  color: var(--color-text);
}

.construction-card p {
  margin: 0;
  color: var(--color-text-sub);
  line-height: 1.75;
  font-size: 13px;
}

.construction-card {
  margin: 20px;
  min-height: 420px;
  background: #fbf4e6;
  border-color: #ebd9b5;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-content: start;
  gap: 16px;
}

.construction-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: #fff;
  color: var(--color-kincha);
  font-weight: 700;
}

.placeholder-list {
  grid-column: 1 / -1;
  display: grid;
  gap: 12px;
  margin-top: 12px;
}

.placeholder-list div {
  height: 58px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px dashed #dfc994;
}

.empty-state {
  min-height: 260px;
  display: grid;
  place-items: center;
  color: var(--color-text-hint);
}

.empty-state.slim {
  min-height: 120px;
}

@media (max-width: 1080px) {
  .publish-workspace {
    grid-template-columns: 1fr;
    min-height: auto;
    gap: 12px;
  }
  .publish-filter {
    padding: 8px;
    overflow-x: auto;
    overscroll-behavior-inline: contain;
    scrollbar-width: thin;
  }
  .publish-filter .filter-block {
    width: max-content;
    min-width: 100%;
    display: flex;
    gap: 6px;
  }
  .filter-title {
    display: none;
  }
  .type-card {
    width: auto;
    min-width: max-content;
    min-height: 40px;
    padding: 0 13px;
  }
  .filter-block + .filter-block {
    margin-top: 0;
  }
  .profile-card {
    grid-template-columns: 1fr;
  }
  .profile-photo-block,
  .profile-intro-field {
    grid-column: auto;
  }
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .publish-page {
    gap: 10px;
  }

  .publish-filter,
  .publish-panel {
    border-radius: 10px;
  }

  .publish-panel {
    min-height: calc(100dvh - 142px);
  }

  .publish-panel-head {
    min-height: 0;
    padding: 12px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px 8px;
  }

  .publish-panel-head h2 {
    font-size: 17px;
  }

  .publish-panel-head p {
    margin-top: 3px;
  }

  .publish-head-search {
    grid-column: 1 / -1;
    grid-row: 2;
    min-width: 0;
    width: 100%;
    margin-left: 0;
    gap: 8px;
  }

  .publish-head-search .btn-primary {
    flex: 0 0 auto;
  }

  .panel-head-actions {
    grid-column: 2;
    grid-row: 1;
  }

  .panel-head-actions button,
  .publish-head-search button {
    min-height: 44px;
    padding-inline: 14px;
    white-space: nowrap;
  }

  .list-embedded-view {
    min-height: 520px;
  }

  .profile-card {
    margin: 14px 12px 0;
    gap: 12px;
  }

  .profile-photo-frame,
  .profile-intro-field textarea {
    height: min(58vw, 240px);
    min-height: 190px;
  }

  .profile-photo-remove {
    opacity: 1;
    pointer-events: auto;
  }

  .metrics-grid {
    padding: 12px;
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .photo-preview-overlay {
    padding: 16px;
  }

  .photo-preview-close {
    top: max(12px, env(safe-area-inset-top));
    right: 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .type-card,
  .profile-photo-remove {
    transition: none;
  }
}
</style>
