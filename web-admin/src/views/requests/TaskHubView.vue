<template>
  <section class="task-page">
    <section class="task-workspace">
      <aside class="task-filter">
        <div class="filter-block">
          <div class="filter-title">类型</div>
          <button
            v-for="item in typeFilters"
            :key="item.value"
            class="type-card"
            :class="{ active: typeFilter === item.value }"
            type="button"
            @click="setTypeFilter(item.value)"
          >
            <span class="type-dot"></span>
            <span>{{ item.label }}</span>
            <em>{{ typeCount(item.value) }}</em>
          </button>
        </div>
      </aside>

      <main class="task-list-panel">
        <div class="task-list-head">
          <div>
            <h2>{{ listTitle }}</h2>
            <p>{{ activeTypeLabel }} · 共 {{ visibleRows.length }} 条</p>
          </div>
          <div class="task-search-bar">
            <label class="task-search-field">
              <input
                v-model.trim="searchDraft"
                type="text"
                placeholder="搜索姓名、手机号、村组、标题或内容"
                @keydown.enter.prevent="applySearch"
              />
            </label>
            <button class="btn-primary small" type="button" @click="applySearch">搜索</button>
          </div>
          <div class="status-segment">
            <button
              v-for="item in statusFilters"
              :key="item.value"
              type="button"
              :class="{ active: statusFilter === item.value }"
              @click="setStatusFilter(item.value)"
            >
              {{ item.label }} {{ statusCounts[item.value] || 0 }}
            </button>
          </div>
        </div>

        <div v-if="feedbackText" class="inline-success">{{ feedbackText }}</div>
        <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
        <div v-if="loading" class="empty-state">正在加载事务列表...</div>
        <div v-else-if="!visibleRows.length" class="empty-state">
          <p>{{ searchKeyword ? "当前搜索条件下暂无事务" : "该筛选下暂无事务" }}</p>
        </div>

        <div v-else class="task-list">
          <button
            v-for="item in paginatedRows"
            :key="item.uid"
            class="task-row"
            :class="{ active: selectedTask?.uid === item.uid }"
            type="button"
            @click="openTask(item)"
          >
            <span class="type-tag" :class="`tag-${item.type}`">{{ item.typeShortLabel }}</span>
            <span class="task-main">
              <strong>{{ item.title }}</strong>
              <em>{{ item.person }} · {{ item.villageGroup }} · {{ item.summary }}</em>
            </span>
            <span class="task-side">
              <span class="status-badge" :class="item.result === 'reject' ? 'reject' : item.statusGroup">
                {{ statusText(item) }}
              </span>
              <small>{{ formatShortTime(item.createdAt) }}</small>
            </span>
          </button>
        </div>

        <footer v-if="!loading && visibleRows.length" class="task-pagination">
          <button
            class="btn-ghost small"
            type="button"
            :disabled="currentPage <= 1"
            @click="currentPage -= 1"
          >
            上一页
          </button>
          <span>第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
          <button
            class="btn-ghost small"
            type="button"
            :disabled="currentPage >= totalPages"
            @click="currentPage += 1"
          >
            下一页
          </button>
        </footer>
      </main>
    </section>

    <div v-if="detailOpen" class="modal-mask" @click="closeDetail">
      <section class="task-modal" @click.stop>
        <header class="modal-head">
          <div>
            <h2>{{ selectedTask?.title || "事务详情" }}</h2>
            <p>{{ selectedTask?.typeLabel }} · {{ statusText(selectedTask) }}</p>
          </div>
          <div class="modal-head-actions">
            <span v-if="selectedTask" class="status-badge" :class="selectedTask.result === 'reject' ? 'reject' : selectedTask.statusGroup">
              {{ statusText(selectedTask) }}
            </span>
            <button class="drawer-close" type="button" @click="closeDetail">关闭</button>
          </div>
        </header>

        <div class="modal-body" v-if="selectedTask">
          <template v-if="selectedTask.type === 'cert'">
            <div class="keyinfo">
              <div class="kline"><span>申请人</span><strong>{{ selectedTask.person }}</strong></div>
              <div class="kline"><span>联系方式</span><strong>{{ selectedTask.phone || "-" }}</strong></div>
              <div v-if="selectedTask.raw?.extra_fields?.id_card" class="kline">
                <span>申请人身份证</span><strong>{{ selectedTask.raw.extra_fields.id_card }}</strong>
              </div>
              <div v-if="selectedTask.raw?.extra_fields?.related_id_card" class="kline">
                <span>相关人员身份证</span><strong>{{ selectedTask.raw.extra_fields.related_id_card }}</strong>
              </div>
              <div class="kline"><span>证明类型</span><strong>{{ certificateTitle(selectedTask.raw) }}</strong></div>
            </div>

            <section v-if="selectedTask.raw?.note" class="detail-block">
              <h3>补充说明</h3>
              <p>{{ selectedTask.raw.note }}</p>
            </section>

            <section v-if="photoList(selectedTask.raw?.supporting_photo_urls).length" class="detail-block">
              <h3>佐证附件</h3>
              <div class="photo-grid compact">
                <button
                  v-for="(url, index) in photoList(selectedTask.raw?.supporting_photo_urls)"
                  :key="`${url}-${index}`"
                  class="photo-thumb image-thumb"
                  type="button"
                  @click="openAttachment(url)"
                >
                  <img :src="resolvePhotoUrl(url)" :alt="`附件 ${index + 1}`" />
                  <span>附件 {{ index + 1 }}</span>
                </button>
              </div>
            </section>

            <section v-if="photoList(selectedTask.raw?.reply_photo_urls).length" class="detail-block">
              <h3>已开具电子证明</h3>
              <div class="photo-grid compact">
                <button
                  v-for="(url, index) in photoList(selectedTask.raw?.reply_photo_urls)"
                  :key="`${url}-${index}`"
                  class="photo-thumb image-thumb proof-thumb"
                  type="button"
                  @click="openAttachment(url)"
                >
                  <img :src="resolvePhotoUrl(url)" :alt="`电子证明 ${index + 1}`" />
                  <span>电子证明 {{ index + 1 }}</span>
                </button>
              </div>
            </section>

            <button class="more-toggle" type="button" @click="moreInfoOpen = !moreInfoOpen">
              {{ moreInfoOpen ? "收起更多信息" : "更多信息" }}
            </button>
            <section v-if="moreInfoOpen" class="detail-block muted">
              <div class="kline"><span>村组</span><strong>{{ selectedTask.villageGroup }}</strong></div>
              <div class="kline"><span>提交时间</span><strong>{{ formatDateTime(selectedTask.createdAt) }}</strong></div>
            </section>
          </template>

          <template v-else-if="selectedTask.type === 'dibao' || selectedTask.type === 'tekun'">
            <div class="keyinfo">
              <div class="kline"><span>申请人</span><strong>{{ selectedTask.person }}</strong></div>
              <div class="kline"><span>联系方式</span><strong>{{ selectedTask.phone || "-" }}</strong></div>
              <div class="kline"><span>村组</span><strong>{{ selectedTask.villageGroup }}</strong></div>
            </div>

            <section class="download-banner">
              <div class="download-icon">↓</div>
              <div class="download-copy">
                <strong>材料打包下载</strong>
                <p>将村民上传的全部材料整理为一个 ZIP 压缩包，一次下载完成。</p>
              </div>
              <button
                class="btn-success download-action"
                type="button"
                :disabled="materialDownloading"
                @click="downloadAllMaterials"
              >
                {{ materialDownloading ? "正在打包..." : "一键下载材料" }}
              </button>
            </section>

            <section class="detail-block">
              <h3>材料预览</h3>
              <div class="material-grid">
                <article v-for="item in selectedTask.materials" :key="item.key" class="material-card">
                  <div class="material-name">
                    <span>{{ item.name }}</span>
                    <strong :class="{ missing: !item.uploaded }">{{ item.uploaded ? `已传${item.photo_urls.length}张` : "未传" }}</strong>
                  </div>
                  <div v-if="item.uploaded" class="material-thumbs">
                    <button
                      v-for="(url, idx) in item.photo_urls"
                      :key="`${url}-${idx}`"
                      class="photo-thumb image-thumb"
                      type="button"
                      @click="openAttachment(url)"
                    >
                      <img :src="resolvePhotoUrl(url)" :alt="`${item.name} ${idx + 1}`" />
                    </button>
                  </div>
                  <div v-else class="material-pic empty">未上传</div>
                </article>
              </div>
            </section>
          </template>

          <template v-else-if="selectedTask.source === 'proposal'">
            <section class="detail-block">
              <h3>建议内容</h3>
              <p>{{ selectedTask.raw?.content || "暂无内容" }}</p>
            </section>
            <section class="detail-block muted">
              <div class="kline"><span>提交人</span><strong>{{ selectedTask.person || "村民" }}</strong></div>
              <div class="kline"><span>提交时间</span><strong>{{ formatDateTime(selectedTask.createdAt) }}</strong></div>
              <p class="muted-line">建议仅供村委查看参考，无需在此处理。</p>
            </section>
          </template>

          <template v-else>
            <section class="detail-block">
              <h3>{{ selectedTask.type === "photo" ? "问题内容" : "建议内容" }}</h3>
              <p>{{ selectedTask.raw?.content || "暂无内容" }}</p>
            </section>

            <section v-if="photoList(selectedTask.raw?.photo_urls).length" class="detail-block">
              <h3>现场照片</h3>
              <div class="photo-grid compact">
                <button
                  v-for="(url, index) in photoList(selectedTask.raw?.photo_urls)"
                  :key="`${url}-${index}`"
                  class="photo-thumb image-thumb"
                  type="button"
                  @click="openAttachment(url)"
                >
                  <img :src="resolvePhotoUrl(url)" :alt="`照片 ${index + 1}`" />
                  <span>照片 {{ index + 1 }}</span>
                </button>
              </div>
            </section>

            <section class="detail-block">
              <h3>回复内容</h3>
              <textarea v-model.trim="replyDraft" :disabled="!canWrite || isSelectedDone" rows="5" placeholder="填写给村民的回复内容"></textarea>
            </section>
          </template>

          <section v-if="isSelectedDone" class="detail-block result-block">
            <h3>处理结果</h3>
            <p>{{ selectedTask.resultText || "已处理" }}</p>
            <p class="muted-line">处理人：{{ selectedTask.raw?.handled_by || "-" }} · 处理时间：{{ formatDateTime(selectedTask.raw?.handled_at) }}</p>
            <div v-if="selectedTask.type !== 'cert' && photoList(selectedTask.raw?.reply_photo_urls).length" class="photo-grid compact result-photo-grid">
              <button
                v-for="(url, index) in photoList(selectedTask.raw?.reply_photo_urls)"
                :key="`${url}-${index}`"
                class="photo-thumb image-thumb"
                type="button"
                @click="openAttachment(url)"
              >
                <img :src="resolvePhotoUrl(url)" :alt="`回执图片 ${index + 1}`" />
                <span>回执图片 {{ index + 1 }}</span>
              </button>
            </div>
          </section>
        </div>

        <footer class="modal-foot">
          <span v-if="!canWrite" class="readonly-tip">当前账号是只读角色，不能处理事务。</span>
          <span v-else-if="saving" class="readonly-tip">正在保存...</span>
          <span v-else></span>

          <div v-if="selectedTask && !isSelectedDone && selectedTask.source !== 'proposal'" class="modal-actions">
            <template v-if="selectedTask.type === 'cert'">
              <button class="btn-primary" type="button" :disabled="!canWrite || saving" @click="approveCertificate">情况属实，办理</button>
              <button class="btn-ghost danger" type="button" :disabled="!canWrite || saving" @click="rejectCertificate">驳回申请</button>
            </template>
            <template v-else-if="selectedTask.type === 'dibao' || selectedTask.type === 'tekun'">
              <button class="btn-primary" type="button" :disabled="!canWrite || saving" @click="resolveMaterialRequest">材料已收齐，办理</button>
              <button class="btn-ghost danger" type="button" :disabled="!canWrite || saving" @click="rejectMaterialRequest">材料不全，驳回</button>
            </template>
            <template v-else>
              <button class="btn-ghost" type="button" :disabled="!canWrite || saving" @click="saveRequestReply">回复</button>
              <button class="btn-primary" type="button" :disabled="!canWrite || saving" @click="resolveRequest">办理</button>
              <button class="btn-ghost danger" type="button" :disabled="!canWrite || saving" @click="rejectRequest">驳回</button>
            </template>
          </div>
        </footer>
      </section>
    </div>

    <div v-if="attachmentPreviewUrl" class="image-preview-mask" @click="closeAttachmentPreview">
      <button class="image-preview-close" type="button" @click.stop="closeAttachmentPreview">关闭</button>
      <img class="image-preview-full" :src="attachmentPreviewUrl" alt="图片预览" @click.stop />
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";

import sealImageUrl from "../../assets/deshengcun-seal.png";
import { buildApiUrl } from "../../api/http";
import { fetchAdminGovApplicationDetail, listAdminGovApplications, updateAdminGovApplication } from "../../api/gov";
import {
  exportAdminRequestMaterials,
  fetchAdminRequestDetail,
  listAdminRequests,
  listAdminProposals,
  updateAdminRequest,
} from "../../api/requests";
import { uploadAdminImage } from "../../api/uploads";
import { useAuthStore } from "../../stores/auth";
import { extractApiError } from "../../utils/admin-ui";
import { buildStampedCertificateFile } from "../../utils/certificate-proof";
import { useTransientMessage } from "../../utils/success-toast";

const authStore = useAuthStore();

const statusFilters = [
  { value: "todo", label: "待处理" },
  { value: "done", label: "已处理" },
];

const PAGE_SIZE = 8;

const typeFilters = [
  { value: "cert", label: "开具证明" },
  { value: "dibao", label: "低保申请" },
  { value: "tekun", label: "特困认证" },
  { value: "photo", label: "随手拍" },
  { value: "advice", label: "建议" },
];

const materialConfigs = {
  dibao: [
    { key: "application", name: "申请书", uploaded: false },
    { key: "diagnosis", name: "病历诊断书", uploaded: false },
    { key: "hospitalization", name: "出入院记录", uploaded: false },
    { key: "expense", name: "费用清单", uploaded: false },
    { key: "hukou", name: "户口簿", uploaded: false },
    { key: "bank_card", name: "银行卡", uploaded: false },
  ],
  tekun: [
    { key: "application", name: "申请书", uploaded: false },
    { key: "hukou", name: "户口簿", uploaded: false },
    { key: "id_card", name: "身份证", uploaded: false },
    { key: "bank_card", name: "银行卡", uploaded: false },
  ],
};

const statusFilter = ref("todo");
const typeFilter = ref("cert");
const searchDraft = ref("");
const searchKeyword = ref("");
const currentPage = ref(1);
const govRows = ref([]);
const requestRows = ref([]);
const proposalRows = ref([]);
const loading = ref(false);
const saving = ref(false);
const materialDownloading = ref(false);
const errorMessage = ref("");
const feedbackText = useTransientMessage();
const detailOpen = ref(false);
const selectedTask = ref(null);
const replyDraft = ref("");
const moreInfoOpen = ref(false);
const attachmentPreviewUrl = ref("");

const canWrite = computed(() => ["super_admin", "cadre"].includes(authStore.user?.role_key || ""));

const normalizedRows = computed(() => [
  ...govRows.value.filter((item) => String(item?.service_key || "") === "certificate").map(normalizeGovApplication),
  ...requestRows.value.map(normalizeVillagerRequest),
].sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt))));

// 村民建议：纯收集箱，只读、无状态、不进待处理/已处理流程
const normalizedProposals = computed(() =>
  proposalRows.value
    .map(normalizeProposal)
    .sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)))
);

const visibleRows = computed(() => {
  // “建议”筛选直接展示村民建议（只读），不受待处理/已处理切换影响
  if (typeFilter.value === "advice") {
    return filterRowsByKeyword(normalizedProposals.value);
  }
  const rows = normalizedRows.value.filter((item) => {
    const statusMatched = item.statusGroup === statusFilter.value;
    const typeMatched = item.type === typeFilter.value;
    return statusMatched && typeMatched;
  });
  return filterRowsByKeyword(rows);
});

const totalPages = computed(() => Math.max(1, Math.ceil(visibleRows.value.length / PAGE_SIZE)));
const paginatedRows = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return visibleRows.value.slice(start, start + PAGE_SIZE);
});

const statusCounts = computed(() => ({
  todo: normalizedRows.value.filter((item) => item.statusGroup === "todo").length,
  done: normalizedRows.value.filter((item) => item.statusGroup === "done").length,
}));

const listTitle = computed(() => (statusFilter.value === "todo" ? "待处理" : "已处理"));
const activeTypeLabel = computed(() => typeFilters.find((item) => item.value === typeFilter.value)?.label || "开具证明");
const isSelectedDone = computed(() => selectedTask.value?.statusGroup === "done");

function typeCount(value) {
  if (value === "advice") {
    return normalizedProposals.value.length;
  }
  return normalizedRows.value.filter((item) => item.type === value).length;
}

function applySearch() {
  searchKeyword.value = searchDraft.value.trim();
  currentPage.value = 1;
  closeDetail();
}

function filterRowsByKeyword(rows) {
  const tokens = searchKeyword.value
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  if (!tokens.length) return rows;
  return rows.filter((item) => {
    const haystack = searchableText(item).toLowerCase();
    return tokens.every((token) => haystack.includes(token));
  });
}

function searchableText(item) {
  const raw = item?.raw || {};
  const extraFields = raw?.extra_fields && typeof raw.extra_fields === "object" ? JSON.stringify(raw.extra_fields) : "";
  return [
    item?.title,
    item?.typeLabel,
    item?.typeShortLabel,
    item?.person,
    item?.phone,
    item?.villageGroup,
    item?.summary,
    item?.resultText,
    statusText(item),
    item?.createdAt,
    raw?.title,
    raw?.content,
    raw?.note,
    raw?.applicant_name,
    raw?.applicant_phone,
    raw?.reporter_name,
    raw?.contact_phone,
    raw?.villager_name,
    raw?.village_group,
    raw?.selected_option,
    extraFields,
  ]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .join(" ");
}

function setStatusFilter(value) {
  statusFilter.value = value;
  currentPage.value = 1;
  closeDetail();
}

function setTypeFilter(value) {
  typeFilter.value = value;
  currentPage.value = 1;
  closeDetail();
}

function statusGroupFromRaw(status) {
  const value = String(status || "").trim().toLowerCase();
  return value === "pending" || value === "processing" ? "todo" : "done";
}

function resultFromRaw(status) {
  const value = String(status || "").trim().toLowerCase();
  if (value === "rejected" || value === "closed") {
    return "reject";
  }
  if (value === "resolved") {
    return "done";
  }
  return "";
}

function normalizeGovApplication(item) {
  const result = resultFromRaw(item?.status);
  return {
    uid: `gov-${item.id}`,
    source: "gov",
    id: Number(item.id || 0),
    type: "cert",
    typeLabel: "开具证明",
    typeShortLabel: "证明",
    title: certificateTitle(item),
    person: item?.applicant_name || "村民用户",
    phone: item?.applicant_phone || "",
    villageGroup: item?.village_group || "未分组",
    summary: item?.note || summarizeCertificate(item),
    rawStatus: String(item?.status || "pending"),
    statusGroup: statusGroupFromRaw(item?.status),
    result,
    resultText: item?.cadre_reply || (result === "reject" ? "申请已驳回" : "情况属实，电子证明已开具。"),
    createdAt: item?.created_at || "",
    raw: item,
  };
}

function normalizeMaterialRequest(item, type) {
  const isTekun = type === "tekun";
  let manifest = [];
  try {
    const parsed = JSON.parse(item?.content || "{}");
    manifest = Array.isArray(parsed?.materials) ? parsed.materials : [];
  } catch (error) {
    manifest = [];
  }
  const flatPhotos = photoList(item?.photo_urls);
  let cursor = 0;
  const countByKey = {};
  const nameByKey = {};
  manifest.forEach((entry) => {
    const key = String(entry?.key || "").trim();
    if (!key) return;
    countByKey[key] = Math.max(0, Number(entry?.count || 0));
    nameByKey[key] = String(entry?.name || "").trim();
  });
  const buildMaterial = (key, name) => {
    const count = countByKey[key] || 0;
    const photos = count > 0 ? flatPhotos.slice(cursor, cursor + count) : [];
    cursor += count;
    return { key, name: name || nameByKey[key] || key, uploaded: photos.length > 0, photo_urls: photos };
  };
  const materials = (materialConfigs[type] || []).map((cfg) => buildMaterial(cfg.key, cfg.name));
  const knownKeys = new Set(materials.map((m) => m.key));
  manifest.forEach((entry) => {
    const key = String(entry?.key || "").trim();
    if (key && !knownKeys.has(key)) {
      materials.push(buildMaterial(key, nameByKey[key]));
    }
  });
  const uploadedCount = materials.filter((m) => m.uploaded).length;
  const result = resultFromRaw(item?.status);
  return {
    uid: `request-${item.id}`,
    source: "request",
    id: Number(item.id || 0),
    type,
    typeLabel: isTekun ? "特困认证" : "低保申请",
    typeShortLabel: isTekun ? "特困" : "低保",
    title: item?.title || (isTekun ? "特困认证材料" : "低保材料提交"),
    person: item?.reporter_name || "村民用户",
    phone: item?.contact_phone || "",
    villageGroup: item?.village_group || "未分组",
    summary: `已传 ${uploadedCount}/${materials.length} 项材料`,
    rawStatus: String(item?.status || "pending"),
    statusGroup: statusGroupFromRaw(item?.status),
    result,
    resultText: item?.reply_text || (result === "reject" ? "材料不全，已驳回" : "材料已收齐，已办理"),
    createdAt: item?.created_at || "",
    materials,
    raw: item,
  };
}

function normalizeVillagerRequest(item) {
  const requestType = String(item?.request_type || "").trim().toLowerCase();
  if (requestType === "dibao" || requestType === "tekun") {
    return normalizeMaterialRequest(item, requestType);
  }
  const isPhoto = String(item?.request_type || "") === "complaint";
  const result = resultFromRaw(item?.status);
  return {
    uid: `request-${item.id}`,
    source: "request",
    id: Number(item.id || 0),
    type: isPhoto ? "photo" : "advice",
    typeLabel: isPhoto ? "随手拍" : "建议",
    typeShortLabel: isPhoto ? "随手拍" : "建议",
    title: item?.title || (isPhoto ? "随手拍事项" : "村民建议"),
    person: item?.reporter_name || "村民用户",
    phone: item?.contact_phone || "",
    villageGroup: item?.village_group || "未分组",
    summary: truncateText(item?.content, 46),
    rawStatus: String(item?.status || "pending"),
    statusGroup: statusGroupFromRaw(item?.status),
    result,
    resultText: item?.reply_text || (result === "reject" ? "事项已驳回" : "事项已办理"),
    createdAt: item?.created_at || "",
    raw: item,
  };
}

function normalizeProposal(item) {
  return {
    uid: `proposal-${item.id}`,
    source: "proposal",
    id: Number(item.id || 0),
    type: "advice",
    typeLabel: "建议",
    typeShortLabel: "建议",
    title: "村民建议",
    person: item?.villager_name || "村民",
    phone: "",
    villageGroup: "",
    summary: truncateText(item?.content, 46),
    rawStatus: "",
    statusGroup: "",
    result: "",
    resultText: "",
    createdAt: item?.created_at || "",
    raw: item,
  };
}

function truncateText(value, size = 60) {
  const text = String(value || "").trim();
  return text.length > size ? `${text.slice(0, size)}...` : text || "暂无摘要";
}

function certificateTitle(item) {
  return String(item?.extra_fields?.certificate_title || item?.selected_option || "开具证明").replace(/^开具证明[:：]\s*/, "");
}

function summarizeCertificate(item) {
  const relation = String(item?.extra_fields?.relation_type || "").trim();
  const relatedName = String(item?.extra_fields?.related_name || "").trim();
  if (relation || relatedName) {
    return [relatedName, relation].filter(Boolean).join(" · ");
  }
  return "村级证明申请";
}

function statusText(item) {
  if (!item) return "待处理";
  if (item.source === "proposal") return "建议";
  if (item.statusGroup === "todo") return "待处理";
  return item.result === "reject" ? "已处理 · 驳回" : "已处理 · 已办";
}

function formatDateTime(value) {
  const text = String(value || "").trim();
  if (!text) return "-";
  return text.replace("T", " ").replace(/\.\d+(\+00:00|Z)$/, "");
}

function formatShortTime(value) {
  const text = formatDateTime(value);
  if (text === "-") return "-";
  return text.slice(0, 16);
}

function photoList(value) {
  return Array.isArray(value) ? value.map((item) => String(item || "").trim()).filter(Boolean) : [];
}

function isLocalHostname(hostname) {
  const text = String(hostname || "").trim().toLowerCase();
  return (
    text === "localhost" ||
    text === "127.0.0.1" ||
    /^10\.\d+\.\d+\.\d+$/.test(text) ||
    /^192\.168\.\d+\.\d+$/.test(text) ||
    /^172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+$/.test(text)
  );
}

function getApiOrigin() {
  try {
    return new URL(buildApiUrl("/"), window.location.href).origin;
  } catch (error) {
    return window.location.origin;
  }
}

function resolvePhotoUrl(url) {
  const target = String(url || "").trim();
  if (!target) {
    return "";
  }
  try {
    const parsed = new URL(target, window.location.href);
    if (!/\/api\/v1\/uploads\/access\//i.test(parsed.pathname || "")) {
      return target;
    }
    const apiOrigin = getApiOrigin();
    const apiParsed = new URL(apiOrigin);
    if (!isLocalHostname(parsed.hostname) && !isLocalHostname(apiParsed.hostname)) {
      return target;
    }
    return `${apiParsed.origin}${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch (error) {
    return target;
  }
}

function openAttachment(url) {
  const target = resolvePhotoUrl(url);
  if (target) {
    attachmentPreviewUrl.value = target;
  }
}

function closeAttachmentPreview() {
  attachmentPreviewUrl.value = "";
}

function clearFeedback() {
  feedbackText.value = "";
  errorMessage.value = "";
}

async function loadAll() {
  if (!authStore.token) return;
  loading.value = true;
  clearFeedback();
  try {
    const [gov, requests, proposals] = await Promise.all([
      listAdminGovApplications(authStore.token, {}),
      listAdminRequests(authStore.token, {}),
      listAdminProposals(authStore.token),
    ]);
    govRows.value = Array.isArray(gov) ? gov : [];
    requestRows.value = Array.isArray(requests) ? requests : [];
    proposalRows.value = Array.isArray(proposals) ? proposals : [];
  } catch (error) {
    errorMessage.value = extractApiError(error, "事务列表加载失败");
  } finally {
    loading.value = false;
  }
}

async function openTask(item) {
  if (!item) return;
  clearFeedback();
  moreInfoOpen.value = false;
  try {
    if (item.source === "gov") {
      const detail = await fetchAdminGovApplicationDetail(authStore.token, item.id);
      selectedTask.value = normalizeGovApplication(detail);
    } else if (item.source === "request") {
      const detail = await fetchAdminRequestDetail(authStore.token, item.id);
      selectedTask.value = normalizeVillagerRequest(detail);
      replyDraft.value = detail?.reply_text || "";
    } else {
      selectedTask.value = item;
    }
    detailOpen.value = true;
  } catch (error) {
    errorMessage.value = extractApiError(error, "事务详情加载失败");
  }
}

function closeDetail() {
  detailOpen.value = false;
  selectedTask.value = null;
  replyDraft.value = "";
  saving.value = false;
  closeAttachmentPreview();
}

async function generateCertificateReplyPhotoUrl(application) {
  const file = await buildStampedCertificateFile(application, sealImageUrl);
  const uploaded = await uploadAdminImage(authStore.token, file, "gov_reply");
  const url = String(uploaded?.url || "").trim();
  if (!url) throw new Error("电子证明上传失败，请稍后重试。");
  return url;
}

async function approveCertificate() {
  if (!selectedTask.value || !canWrite.value) return;
  saving.value = true;
  clearFeedback();
  try {
    const replyUrl = await generateCertificateReplyPhotoUrl(selectedTask.value.raw);
    const updated = await updateAdminGovApplication(authStore.token, selectedTask.value.id, {
      status: "resolved",
      cadre_reply: "情况属实，电子证明已开具。",
      reply_photo_urls: [replyUrl],
    });
    replaceGovRow(updated);
    selectedTask.value = normalizeGovApplication(updated);
    feedbackText.value = "办件已处理为“已办”。";
    refreshBadges();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : extractApiError(error, "办件处理失败");
  } finally {
    saving.value = false;
  }
}

async function rejectCertificate() {
  if (!selectedTask.value || !canWrite.value) return;
  const reason = window.prompt("请输入驳回原因", "申请材料暂不符合开具要求。");
  if (reason === null) return;
  saving.value = true;
  clearFeedback();
  try {
    const updated = await updateAdminGovApplication(authStore.token, selectedTask.value.id, {
      status: "rejected",
      cadre_reply: String(reason || "申请已驳回。").trim() || "申请已驳回。",
      reply_photo_urls: [],
    });
    replaceGovRow(updated);
    selectedTask.value = normalizeGovApplication(updated);
    feedbackText.value = "办件已处理为“驳回”。";
    refreshBadges();
  } catch (error) {
    errorMessage.value = extractApiError(error, "驳回失败");
  } finally {
    saving.value = false;
  }
}

async function saveRequestReply() {
  await updateSelectedRequest({
    status: selectedTask.value?.rawStatus || "pending",
    reply_text: replyDraft.value || "村委会已收到，将尽快跟进。",
  }, "回复已保存。");
}

async function resolveRequest() {
  await updateSelectedRequest({
    status: "resolved",
    reply_text: replyDraft.value || "该事项已办理。",
  }, "事项已处理为“已办”。");
}

async function rejectRequest() {
  await updateSelectedRequest({
    status: "closed",
    reply_text: replyDraft.value || "该事项暂不符合办理条件，已驳回。",
  }, "事项已处理为“驳回”。");
}

async function updateSelectedRequest(payload, message) {
  if (!selectedTask.value || selectedTask.value.source !== "request" || !canWrite.value) return;
  saving.value = true;
  clearFeedback();
  try {
    const updated = await updateAdminRequest(authStore.token, selectedTask.value.id, {
      status: payload.status,
      reply_text: payload.reply_text,
      reply_photo_urls: selectedTask.value.raw?.reply_photo_urls || [],
    });
    replaceRequestRow(updated);
    selectedTask.value = normalizeVillagerRequest(updated);
    replyDraft.value = updated?.reply_text || "";
    feedbackText.value = message;
    refreshBadges();
  } catch (error) {
    errorMessage.value = extractApiError(error, "事务处理失败");
  } finally {
    saving.value = false;
  }
}

function replaceGovRow(updated) {
  govRows.value = govRows.value.map((item) => (Number(item.id) === Number(updated.id) ? updated : item));
}

function replaceRequestRow(updated) {
  requestRows.value = requestRows.value.map((item) => (Number(item.id) === Number(updated.id) ? updated : item));
}

function refreshBadges() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("admin-nav-badges:refresh"));
  }
}

async function resolveMaterialRequest() {
  await updateSelectedRequest(
    { status: "resolved", reply_text: "材料已收齐，已办理。" },
    "申请已处理为“已办”。"
  );
}

async function rejectMaterialRequest() {
  const reason = window.prompt("请输入驳回原因", "材料不全，请补齐后重新提交。");
  if (reason === null) return;
  await updateSelectedRequest(
    { status: "closed", reply_text: String(reason || "材料不全，已驳回。").trim() || "材料不全，已驳回。" },
    "申请已处理为“驳回”。"
  );
}

async function downloadAllMaterials() {
  if (!selectedTask.value || materialDownloading.value) return;
  const urls = (selectedTask.value.materials || []).flatMap((item) => item.photo_urls || []);
  if (!urls.length) {
    feedbackText.value = "该申请暂无可下载的材料图片。";
    return;
  }
  materialDownloading.value = true;
  clearFeedback();
  try {
    const typeLabel = selectedTask.value.type === "dibao" ? "低保申请" : "特困认证";
    const applicant = String(selectedTask.value.person || "村民").replace(/[\\/:*?\"<>|]/g, "_");
    await exportAdminRequestMaterials(
      authStore.token,
      selectedTask.value.id,
      `${typeLabel}_${applicant}_${selectedTask.value.id}_申请材料.zip`
    );
    feedbackText.value = "材料压缩包已开始下载。";
  } catch (error) {
    errorMessage.value = extractApiError(error, "材料打包下载失败，请稍后重试。");
  } finally {
    materialDownloading.value = false;
  }
}

watch(totalPages, (nextTotal) => {
  if (currentPage.value > nextTotal) {
    currentPage.value = nextTotal;
  }
});

onMounted(() => {
  loadAll();
});
</script>

<style scoped>
.task-page {
  display: grid;
  gap: 16px;
}

.task-workspace {
  min-height: calc(100vh - 104px);
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
}

.task-filter,
.task-list-panel,
.task-modal {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  box-shadow: var(--card-shadow);
}

.task-filter {
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

.status-card,
.type-card {
  width: 100%;
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 9px;
  border-radius: 10px;
  color: var(--color-text-sub);
}

.status-card {
  justify-content: space-between;
  padding: 0 13px;
}

.status-card strong {
  font-family: var(--font-serif);
  color: var(--color-kincha);
  font-size: 17px;
}

.status-card.active,
.type-card.active {
  background: var(--color-primary-pale);
  color: var(--color-primary);
  font-weight: 600;
}

.status-card.active strong {
  color: var(--color-primary);
}

.type-card {
  padding: 0 12px;
  font-size: 13px;
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

.task-list-panel {
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.task-list-head {
  min-height: 62px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  gap: 14px;
}

.task-list-head h2 {
  margin: 0;
  font-size: 16px;
}

.task-list-head p {
  margin: 4px 0 0;
  color: var(--color-text-hint);
  font-size: 12px;
}

.task-search-bar {
  flex: 1;
  min-width: 360px;
  margin-left: clamp(80px, 8.5vw, 170px);
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-search-field {
  flex: 1;
  min-width: 0;
}

.task-search-field input {
  min-height: 38px;
}

.status-segment {
  display: inline-flex;
  gap: 3px;
  padding: 3px;
  border-radius: 9px;
  background: #f1eadb;
}

.status-segment button {
  min-height: 28px;
  padding: 0 14px;
  border-radius: 7px;
  color: var(--color-text-sub);
  font-size: 12px;
}

.status-segment button.active {
  background: #fff;
  color: var(--color-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.small {
  min-height: 32px;
  padding: 0 12px;
}

.task-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
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

.task-row {
  width: 100%;
  min-height: 74px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border-light);
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

.tag-cert { background: #f0e7f0; color: #7a4a78; }
.tag-dibao { background: #e8efe6; color: var(--color-matcha); }
.tag-tekun { background: #f3ebdb; color: var(--color-kincha); }
.tag-photo { background: #e6edf2; color: #3f6184; }
.tag-advice { background: var(--color-primary-pale); color: var(--color-primary); }

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

.status-badge.reject {
  background: #f6e7e4;
  color: var(--color-primary);
}

.empty-state {
  flex: 1;
  min-height: 260px;
  display: grid;
  place-items: center;
  gap: 14px;
  color: var(--color-text-hint);
  text-align: center;
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px;
  background: rgba(40, 30, 22, 0.42);
  backdrop-filter: blur(2px);
}

.task-modal {
  width: min(720px, 100%);
  max-height: min(88vh, 900px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.modal-head,
.modal-foot {
  padding: 18px 24px;
  background: #fff;
}

.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.modal-head h2 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 600;
}

.modal-head p {
  margin: 6px 0 0;
  color: var(--color-text-hint);
  font-size: 13px;
}

.modal-head-actions,
.modal-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.modal-body {
  min-height: 0;
  overflow: auto;
  padding: 22px 24px;
  display: grid;
  gap: 18px;
}

.modal-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border-top: 1px solid var(--color-border-light);
}

.keyinfo,
.detail-block,
.download-banner {
  border: 1px solid var(--color-border-light);
  border-radius: 14px;
  background: #ffffff;
}

.keyinfo {
  padding: 4px 20px;
}

.kline {
  display: flex;
  gap: 16px;
  padding: 13px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.kline:last-child {
  border-bottom: 0;
}

.kline span {
  width: 88px;
  flex-shrink: 0;
  color: var(--color-text-hint);
}

.kline strong {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--color-text);
  font-weight: 600;
}

.detail-block {
  padding: 16px 18px;
}

.detail-block h3 {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--color-text-hint);
  letter-spacing: 0.08em;
}

.detail-block p {
  margin: 0;
  color: var(--color-text);
  line-height: 1.7;
  white-space: pre-wrap;
}

.detail-block textarea {
  width: 100%;
}

.muted {
  background: #fff;
}

.muted-line {
  margin-top: 8px !important;
  color: var(--color-text-hint) !important;
  font-size: 12px;
}

.more-toggle {
  width: fit-content;
  color: var(--color-text-hint);
  font-size: 13px;
}

.more-toggle:hover {
  color: var(--color-primary);
}

.photo-grid,
.material-grid {
  display: grid;
  gap: 12px;
}

.photo-grid.compact {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.photo-thumb {
  height: 74px;
  border: 1px solid var(--color-border);
  border-radius: 11px;
  background: linear-gradient(135deg, #efe9dc, #e3dccb);
  color: var(--color-text-sub);
}

.photo-thumb.image-thumb {
  position: relative;
  min-height: 92px;
  height: 92px;
  overflow: hidden;
  padding: 0;
  background: #f7f2e8;
}

.photo-thumb.image-thumb img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.photo-thumb.image-thumb span {
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: 7px;
  min-height: 22px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(26, 22, 18, 0.76);
  color: #fff;
  font-size: 12px;
}

.photo-thumb.proof-thumb {
  height: 138px;
  background: #fffdf8;
}

.photo-thumb.proof-thumb img {
  object-fit: contain;
  padding: 8px;
  box-sizing: border-box;
}

.result-photo-grid {
  margin-top: 14px;
}

.image-preview-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 32px;
  background: rgba(23, 18, 14, 0.74);
}

.image-preview-full {
  max-width: min(92vw, 1100px);
  max-height: 86vh;
  border-radius: 12px;
  background: #fff;
  object-fit: contain;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
}

.image-preview-close {
  position: fixed;
  top: 24px;
  right: 28px;
  min-height: 40px;
  padding: 0 18px;
  border-radius: 999px;
  background: #fff;
  color: var(--color-text);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
}

.download-banner {
  padding: 18px 20px;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  background: #f2f6f0;
}

.download-copy {
  min-width: 0;
}

.download-copy strong {
  display: block;
  line-height: 1.35;
}

.download-banner p {
  margin: 5px 0 0;
  color: var(--color-text-hint);
  font-size: 12px;
}

.download-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: #fff;
  border: 1px solid #dce7d7;
  color: var(--color-matcha);
  font-size: 22px;
}

.download-action {
  min-width: 150px;
  align-self: center;
  justify-self: end;
}

.download-action:disabled {
  cursor: wait;
  opacity: 0.65;
  transform: none;
}

.material-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.material-card {
  border: 1px solid var(--color-border);
  border-radius: 11px;
  overflow: hidden;
  background: #fff;
}

.material-pic {
  height: 84px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #efe9dc, #e3dccb);
  color: var(--color-text-hint);
}

.material-name {
  min-height: 38px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--color-text-sub);
  font-size: 12px;
}

.material-name strong {
  color: var(--color-matcha);
  font-weight: 600;
}

.material-name strong.missing {
  color: var(--color-text-hint);
}

.material-card .material-name {
  border-bottom: 1px solid var(--color-border);
}

.material-thumbs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  padding: 8px;
}

.material-thumbs .photo-thumb.image-thumb {
  height: 72px;
  min-height: 72px;
  border-radius: 8px;
}

.material-pic.empty {
  height: 60px;
  font-size: 12px;
  color: var(--color-text-hint);
}

.danger {
  color: var(--color-primary) !important;
  border-color: rgba(166, 61, 47, 0.2) !important;
}

.readonly-tip {
  color: var(--color-text-hint);
  font-size: 12px;
}

@media (max-width: 1080px) {
  .task-workspace {
    grid-template-columns: 1fr;
    min-height: auto;
    gap: 12px;
  }
  .task-filter {
    padding: 8px;
    overflow-x: auto;
    overscroll-behavior-inline: contain;
    scrollbar-width: thin;
  }
  .task-filter .filter-block {
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
}

@media (max-width: 720px) {
  .task-page {
    gap: 10px;
  }

  .task-filter,
  .task-list-panel {
    border-radius: 10px;
  }

  .task-list-panel {
    min-height: calc(100dvh - 142px);
  }

  .task-list-head {
    min-height: 0;
    padding: 12px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px 8px;
  }

  .task-list-head h2 {
    font-size: 17px;
  }

  .task-search-bar {
    grid-column: 1 / -1;
    grid-row: 2;
    min-width: 0;
    width: 100%;
    margin-left: 0;
    gap: 8px;
  }

  .task-search-field input {
    width: 100%;
  }

  .status-segment {
    grid-column: 2;
    grid-row: 1;
    max-width: 100%;
  }

  .status-segment button {
    min-height: 36px;
    padding: 0 9px;
    white-space: nowrap;
  }

  .task-row {
    min-height: 0;
    padding: 14px 12px;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: start;
    gap: 9px 10px;
  }

  .task-main {
    align-self: center;
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

  .modal-mask {
    align-items: stretch;
    justify-content: stretch;
    padding: 0;
  }

  .task-modal {
    width: 100%;
    max-height: none;
    height: 100vh;
    height: 100dvh;
    border: 0;
    border-radius: 0;
  }

  .modal-head,
  .modal-foot {
    padding: 12px;
  }

  .modal-head {
    align-items: center;
  }

  .modal-head h2 {
    font-size: 18px;
  }

  .modal-head-actions .status-badge {
    display: none;
  }

  .modal-body {
    padding: 12px;
    gap: 12px;
    overscroll-behavior: contain;
  }

  .modal-foot {
    padding-bottom: calc(12px + env(safe-area-inset-bottom));
    align-items: stretch;
    flex-direction: column;
  }

  .modal-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .modal-actions button {
    width: 100%;
    min-height: 44px;
  }

  .kline {
    display: grid;
    grid-template-columns: 74px minmax(0, 1fr);
    gap: 10px;
  }

  .kline span {
    width: auto;
  }

  .kline strong,
  .detail-block p {
    overflow-wrap: anywhere;
  }

  .download-banner {
    padding: 14px;
    grid-template-columns: 40px minmax(0, 1fr);
    gap: 10px;
  }

  .download-icon {
    width: 40px;
    height: 40px;
  }

  .download-action {
    grid-column: 1 / -1;
    width: 100%;
    min-width: 0;
    justify-self: stretch;
  }

  .photo-grid.compact,
  .material-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .image-preview-mask {
    padding: 12px;
  }

  .image-preview-close {
    top: max(12px, env(safe-area-inset-top));
    right: 12px;
  }
}

@media (max-width: 420px) {
  .task-list-head {
    grid-template-columns: 1fr;
  }

  .status-segment {
    grid-column: 1;
    grid-row: 2;
    width: 100%;
  }

  .status-segment button {
    flex: 1;
  }

  .task-search-bar {
    grid-row: 3;
  }
}
</style>
