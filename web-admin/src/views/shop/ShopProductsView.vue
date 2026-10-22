<template>
  <section class="training-admin-page">
    <section class="publishing-list-panel">
      <div v-if="feedbackText" class="success-box">{{ feedbackText }}</div>
      <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
      <div v-if="loading" class="empty-block">正在加载好物...</div>
      <div v-else-if="!items.length" class="empty-block">暂无好物，点击右上角“新增好物”。</div>

      <div v-else class="product-list">
        <div v-for="item in paginatedItems" :key="item.id" class="product-row">
          <div class="product-thumb">
            <img v-if="item.cover_url" :src="item.cover_url" :alt="item.name" />
            <span v-else>无图</span>
          </div>
          <div class="product-row-main">
            <div class="product-row-title">{{ item.name }}</div>
            <div class="product-row-sub">{{ item.subtitle || "—" }}</div>
          </div>
          <div class="product-row-actions">
            <button class="ghost-btn" type="button" @click="selectProduct(item.id)">编辑</button>
            <button class="ghost-btn danger" type="button" :disabled="!canWrite || saving" @click="removeProduct(item.id)">删除</button>
          </div>
        </div>
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
            <h3 class="detail-title">{{ editorMode === "create" ? "新增好物" : "编辑好物" }}</h3>
            <p class="detail-subtitle">维护村民端“好物”展示信息，无价格、无购买，仅作展示。</p>
          </div>
          <button class="drawer-close" type="button" @click="closeDrawer">关闭</button>
        </header>

        <div class="detail-scroll">
          <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
          <div class="detail-form">
            <div class="detail-grid">
              <label class="detail-field">
                <span>名称</span>
                <input v-model.trim="form.name" type="text" :disabled="!canWrite || saving" placeholder="如：平江烟茶" />
              </label>
              <label class="detail-field">
                <span>排序（小的在前）</span>
                <input v-model.number="form.sort_order" type="number" min="0" :disabled="!canWrite || saving" placeholder="0" />
              </label>
            </div>

            <label class="detail-field">
              <span>一句简介</span>
              <input v-model.trim="form.subtitle" type="text" :disabled="!canWrite || saving" placeholder="如：柴火熏制 · 回味悠长" />
            </label>

            <div class="detail-grid">
              <div class="detail-field">
                <span>封面图（列表用）</span>
                <div class="img-uploader">
                  <div class="img-preview" :class="{ empty: !form.cover_url }">
                    <img v-if="form.cover_url" :src="form.cover_url" alt="封面" />
                    <span v-else>暂无封面</span>
                  </div>
                  <div class="img-actions">
                    <button class="ghost-btn" type="button" :disabled="!canWrite || coverUploading" @click="pickCover">
                      {{ coverUploading ? "上传中" : form.cover_url ? "替换" : "上传" }}
                    </button>
                    <button class="ghost-btn" type="button" :disabled="!canWrite || coverUploading || !form.cover_url" @click="form.cover_url = ''">移除</button>
                    <input ref="coverInputRef" class="hidden-file-input" type="file" accept="image/*" @change="onCoverPicked" />
                  </div>
                </div>
              </div>

              <div class="detail-field">
                <span>详情配图</span>
                <div class="img-uploader">
                  <div class="img-preview" :class="{ empty: !form.detail_img_url }">
                    <img v-if="form.detail_img_url" :src="form.detail_img_url" alt="详情图" />
                    <span v-else>暂无配图</span>
                  </div>
                  <div class="img-actions">
                    <button class="ghost-btn" type="button" :disabled="!canWrite || detailUploading" @click="pickDetail">
                      {{ detailUploading ? "上传中" : form.detail_img_url ? "替换" : "上传" }}
                    </button>
                    <button class="ghost-btn" type="button" :disabled="!canWrite || detailUploading || !form.detail_img_url" @click="form.detail_img_url = ''">移除</button>
                    <input ref="detailInputRef" class="hidden-file-input" type="file" accept="image/*" @change="onDetailPicked" />
                  </div>
                </div>
              </div>
            </div>

            <label class="detail-field">
              <span>历史渊源</span>
              <textarea v-model.trim="form.history" rows="4" :disabled="!canWrite || saving" placeholder="介绍这款好物的历史渊源"></textarea>
            </label>
            <label class="detail-field">
              <span>传统制法</span>
              <textarea v-model.trim="form.craft" rows="4" :disabled="!canWrite || saving" placeholder="介绍传统制作工艺"></textarea>
            </label>
            <label class="detail-field">
              <span>风味特点</span>
              <textarea v-model.trim="form.flavor" rows="4" :disabled="!canWrite || saving" placeholder="介绍口感风味特点"></textarea>
            </label>
          </div>
        </div>

        <div class="detail-foot">
          <div class="detail-actions">
            <button class="primary-btn" type="button" :disabled="!canWrite || saving || coverUploading || detailUploading" @click="saveProduct">
              {{ saving ? "保存中..." : editorMode === "create" ? "创建好物" : "保存修改" }}
            </button>
            <button class="ghost-btn" type="button" :disabled="saving" @click="resetEditor">
              {{ editorMode === "create" ? "清空表单" : "恢复当前内容" }}
            </button>
          </div>
          <span v-if="!canWrite" class="readonly-tip">当前账号是只读角色，不能维护好物。</span>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import {
  createAdminProduct,
  deleteAdminProduct,
  listAdminProducts,
  updateAdminProduct,
} from "../../api/products";
import { uploadAdminImage } from "../../api/uploads";
import { useAuthStore } from "../../stores/auth";
import { extractApiError, hasText } from "../../utils/admin-ui";
import { useTransientMessage } from "../../utils/success-toast";

const authStore = useAuthStore();

const allItems = ref([]);
const activeId = ref(0);
const editorMode = ref("create");
const drawerOpen = ref(false);
const loading = ref(false);
const saving = ref(false);
const coverUploading = ref(false);
const detailUploading = ref(false);
const errorMessage = ref("");
const feedbackText = useTransientMessage();
const coverInputRef = ref(null);
const detailInputRef = ref(null);
const PAGE_SIZE = 8;
const currentPage = ref(1);

const form = reactive({
  name: "",
  subtitle: "",
  cover_url: "",
  detail_img_url: "",
  history: "",
  craft: "",
  flavor: "",
  sort_order: 0,
});

const canWrite = computed(() => ["super_admin", "cadre"].includes(authStore.user?.role_key || ""));
const items = computed(() => allItems.value);
const totalPages = computed(() => Math.max(1, Math.ceil(items.value.length / PAGE_SIZE)));
const paginatedItems = computed(() => {
  const safePage = Math.min(currentPage.value, totalPages.value);
  const start = (safePage - 1) * PAGE_SIZE;
  return items.value.slice(start, start + PAGE_SIZE);
});

function clearForm() {
  form.name = "";
  form.subtitle = "";
  form.cover_url = "";
  form.detail_img_url = "";
  form.history = "";
  form.craft = "";
  form.flavor = "";
  form.sort_order = 0;
}

function applyForm(item) {
  form.name = item?.name || "";
  form.subtitle = item?.subtitle || "";
  form.cover_url = item?.cover_url || "";
  form.detail_img_url = item?.detail_img_url || "";
  form.history = item?.history || "";
  form.craft = item?.craft || "";
  form.flavor = item?.flavor || "";
  form.sort_order = Number(item?.sort_order || 0);
}

async function loadProducts() {
  loading.value = true;
  errorMessage.value = "";
  try {
    allItems.value = (await listAdminProducts(authStore.token)) || [];
    currentPage.value = Math.min(currentPage.value, totalPages.value);
  } catch (err) {
    errorMessage.value = extractApiError(err, "好物加载失败");
  } finally {
    loading.value = false;
  }
}

function startCreate() {
  feedbackText.value = "";
  errorMessage.value = "";
  editorMode.value = "create";
  activeId.value = 0;
  clearForm();
  drawerOpen.value = true;
}

function selectProduct(productId) {
  const current = allItems.value.find((item) => item.id === productId);
  if (!current) return;
  feedbackText.value = "";
  errorMessage.value = "";
  activeId.value = productId;
  editorMode.value = "edit";
  applyForm(current);
  drawerOpen.value = true;
}

function closeDrawer() {
  drawerOpen.value = false;
  activeId.value = 0;
  editorMode.value = "create";
  errorMessage.value = "";
  clearForm();
}

function resetEditor() {
  errorMessage.value = "";
  if (editorMode.value === "create") {
    clearForm();
    return;
  }
  const current = allItems.value.find((item) => item.id === activeId.value);
  if (current) applyForm(current);
}

function loadImageElement(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = (err) => {
      URL.revokeObjectURL(url);
      reject(err);
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
    const maxHeight = 1600;
    const scale = Math.min(1, maxWidth / image.naturalWidth, maxHeight / image.naturalHeight);
    const width = Math.max(1, Math.round(image.naturalWidth * scale));
    const height = Math.max(1, Math.round(image.naturalHeight * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.drawImage(image, 0, 0, width, height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/webp", 0.82));
    if (!blob) return file;
    const basename = String(file.name || "product").replace(/\.[^.]+$/, "");
    return new File([blob], `${basename}.webp`, { type: "image/webp" });
  } catch (_) {
    return file;
  }
}

function pickCover() {
  coverInputRef.value?.click();
}

function pickDetail() {
  detailInputRef.value?.click();
}

async function uploadPicked(event, target) {
  const input = event.target;
  const file = input?.files?.[0];
  if (!file) return;
  const flag = target === "cover" ? coverUploading : detailUploading;
  flag.value = true;
  errorMessage.value = "";
  try {
    const uploadFile = await compressImageToWebp(file);
    const result = await uploadAdminImage(authStore.token, uploadFile, "shop");
    const url = String(result?.url || "").trim();
    if (!url) throw new Error("上传失败");
    if (target === "cover") {
      form.cover_url = url;
    } else {
      form.detail_img_url = url;
    }
  } catch (err) {
    errorMessage.value = extractApiError(err, "图片上传失败");
  } finally {
    flag.value = false;
    if (input) input.value = "";
  }
}

function onCoverPicked(event) {
  uploadPicked(event, "cover");
}

function onDetailPicked(event) {
  uploadPicked(event, "detail");
}

function buildPayload() {
  return {
    name: form.name,
    subtitle: form.subtitle,
    cover_url: form.cover_url,
    detail_img_url: form.detail_img_url,
    history: form.history,
    craft: form.craft,
    flavor: form.flavor,
    sort_order: Number(form.sort_order || 0),
  };
}

async function saveProduct() {
  if (!canWrite.value) return;
  if (!hasText(form.name)) {
    errorMessage.value = "请先填写好物名称。";
    return;
  }
  const isCreating = editorMode.value === "create";
  saving.value = true;
  errorMessage.value = "";
  feedbackText.value = "";
  try {
    const result = isCreating
      ? await createAdminProduct(authStore.token, buildPayload())
      : await updateAdminProduct(authStore.token, activeId.value, buildPayload());
    activeId.value = result.id;
    editorMode.value = "edit";
    applyForm(result);
    feedbackText.value = isCreating ? "好物已创建。" : "好物已保存。";
    await loadProducts();
  } catch (err) {
    errorMessage.value = extractApiError(err, "好物保存失败");
  } finally {
    saving.value = false;
  }
}

async function removeProduct(productId) {
  if (!canWrite.value) return;
  if (!window.confirm("删除后村民端将不再显示该好物，确定继续吗？")) return;
  saving.value = true;
  errorMessage.value = "";
  feedbackText.value = "";
  try {
    await deleteAdminProduct(authStore.token, productId);
    feedbackText.value = "好物已删除。";
    if (activeId.value === productId) closeDrawer();
    await loadProducts();
  } catch (err) {
    errorMessage.value = extractApiError(err, "好物删除失败");
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  clearForm();
  await loadProducts();
});

defineExpose({ loadProducts, startCreate, loading, canWrite });
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

.readonly-tip,
.empty-block {
  color: #667085;
  font-size: 12px;
}

.empty-block {
  min-height: 120px;
  display: grid;
  place-items: center;
}

.product-list {
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

.product-row {
  min-height: 92px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid rgba(16, 56, 42, 0.08);
  background: transparent;
  padding: 16px 20px;
}

.product-row:hover {
  background: #fbf8f1;
}

.product-thumb {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
  border-radius: 12px;
  overflow: hidden;
  background: #ece6d8;
  display: grid;
  place-items: center;
  color: #b8afa3;
  font-size: 12px;
}

.product-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.product-row-main {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 4px;
}

.product-row-title {
  color: #10382a;
  font-size: 15px;
  font-weight: 700;
}

.product-row-sub {
  color: #667085;
  font-size: 13px;
}

.product-row-actions {
  flex-shrink: 0;
  display: flex;
  gap: 8px;
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
  width: min(900px, 100%);
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
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.detail-foot {
  border-top: 1px solid rgba(16, 56, 42, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #10382a;
}

.detail-subtitle {
  margin: 6px 0 0;
  color: #667085;
  font-size: 13px;
}

.detail-scroll {
  min-height: 0;
  overflow: auto;
  padding: 16px 18px;
}

.detail-form {
  display: grid;
  gap: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-field {
  display: grid;
  gap: 8px;
}

.detail-field > span {
  font-size: 13px;
  font-weight: 700;
  color: #10382a;
}

.detail-field input,
.detail-field textarea {
  width: 100%;
  min-height: 40px;
  border: 1px solid rgba(16, 56, 42, 0.14);
  border-radius: 10px;
  padding: 8px 10px;
  color: #10382a;
  background: #fff;
  box-sizing: border-box;
}

.detail-field textarea {
  resize: vertical;
  line-height: 1.6;
}

.detail-actions {
  display: flex;
  gap: 10px;
}

.img-uploader {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.img-preview {
  width: 120px;
  height: 90px;
  flex-shrink: 0;
  border-radius: 10px;
  overflow: hidden;
  background: #ece6d8;
  display: grid;
  place-items: center;
  color: #b8afa3;
  font-size: 12px;
}

.img-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.img-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hidden-file-input {
  display: none;
}

.primary-btn {
  min-height: 38px;
  padding: 0 16px;
  border-radius: 10px;
  background: #14613f;
  color: #fff;
  border: none;
}

.ghost-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 10px;
  background: #fff;
  color: #10382a;
  border: 1px solid rgba(16, 56, 42, 0.16);
}

.ghost-btn.danger {
  color: #b3261e;
  border-color: rgba(179, 38, 30, 0.28);
}

.success-box {
  background: #e9f6ee;
  color: #14613f;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
}

.inline-error {
  background: #fdecea;
  color: #b3261e;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
}

@media (max-width: 860px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .product-row {
    min-height: 0;
    padding: 14px 12px;
    display: grid;
    grid-template-columns: 64px minmax(0, 1fr);
    gap: 10px 12px;
  }

  .product-thumb {
    width: 64px;
    height: 64px;
  }

  .product-row-actions {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }

  .product-row-actions button {
    min-height: 42px;
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
    align-items: center;
  }

  .detail-title {
    font-size: 18px;
  }

  .detail-scroll {
    padding: 12px;
    overscroll-behavior: contain;
  }

  .detail-foot {
    padding: 12px 12px calc(12px + env(safe-area-inset-bottom));
    align-items: stretch;
    flex-direction: column;
  }

  .detail-actions {
    width: 100%;
  }

  .detail-actions button {
    flex: 1;
    min-height: 44px;
  }

  .img-uploader {
    align-items: stretch;
    flex-direction: column;
  }

  .img-preview {
    width: 100%;
    height: 180px;
  }

  .img-actions {
    flex-direction: row;
  }

  .img-actions button {
    flex: 1;
  }
}
</style>
