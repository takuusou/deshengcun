<template>
  <section class="sys-page">
    <section v-if="!isSuperAdmin" class="permission-card">
      当前账号不是超级管理员。干部授权管理和审计日志，仅向村书记或最高权限角色开放。
    </section>

    <section v-else class="sys-grid">
      <!-- 左：干部授权 -->
      <article class="card">
        <div class="cardhead">
          <h3>干部授权</h3>
          <span class="meta">共 {{ items.length }} 人</span>
          <button class="btn-add" type="button" @click="openAdd">
            <span class="plus">＋</span>新增干部
          </button>
        </div>

        <div v-if="errorMessage" class="inline-error">{{ errorMessage }}</div>
        <div v-if="loading" class="empty-block">正在加载干部授权名单...</div>
        <div v-else-if="!items.length" class="empty-block">当前还没有干部授权记录。</div>

        <div v-else class="crow-list">
          <button
            v-for="item in items"
            :key="item.id"
            type="button"
            class="crow"
            @click="openEdit(item)"
          >
            <span class="ava">{{ avatarText(item.real_name) }}</span>
            <span class="info">
              <span class="nm">{{ item.real_name || "未命名干部" }}</span>
              <span class="role">{{ officeTitleLabel(item.office_title) }} · {{ roleLabel(item.role_level) }}</span>
            </span>
            <span class="acc">
              <span v-if="item.admin_account_exists" class="a1">{{ item.admin_login_name }}</span>
              <span v-else class="a1 a1-empty">未创建账号</span>
              <span v-if="item.admin_account_exists" class="a2">{{ accountRoleLabel(item.admin_role_key) }}</span>
            </span>
            <span class="pill" :class="statusPillClass(item)">{{ statusPillText(item) }}</span>
            <span class="arr">›</span>
          </button>
        </div>
      </article>

      <!-- 右：审计日志 -->
      <article class="card">
        <div class="cardhead">
          <h3>审计日志</h3>
          <span class="meta meta-right">按时间倒序 · 每页 {{ PAGE_SIZE }} 条</span>
        </div>

        <div v-if="auditLoading" class="empty-block">正在加载审计日志...</div>
        <div v-else-if="!auditRows.length" class="empty-block">当前还没有审计动作记录。</div>

        <template v-else>
          <div class="logbody">
            <div v-for="row in pagedAudit" :key="row.id" class="lrow">
              <span class="dot"></span>
              <div class="lc">
                <div class="human"><b>{{ row.actor_display_name || "系统记录" }}</b> {{ translateAuditAction(row.action) }}</div>
                <span class="keytag">{{ row.target_type || "-" }} / {{ row.target_id || "-" }}</span>
              </div>
              <span class="tm">{{ formatAuditTime(row.created_at) }}</span>
            </div>
          </div>

          <div v-if="totalPages > 1" class="pager">
            <button type="button" class="nav-btn" :disabled="auditPage <= 1" @click="auditPage--">‹</button>
            <span class="page-ind">第 {{ auditPage }} / {{ totalPages }} 页</span>
            <button type="button" class="nav-btn" :disabled="auditPage >= totalPages" @click="auditPage++">›</button>
          </div>
        </template>
      </article>
    </section>

    <!-- ===== 编辑干部弹窗：上只读概览 + 下可编辑表单 ===== -->
    <div v-if="editVisible" class="mask" @click="closeEdit">
      <div class="modal" @click.stop>
        <div class="mhead">
          <div class="ava">{{ avatarText(activeItem?.real_name) }}</div>
          <div class="ht">
            <h2>{{ activeItem?.real_name || "干部" }}</h2>
            <div class="sub">微信身份绑定、后台角色与密码重置，都在这里集中处理</div>
          </div>
          <span class="pill" :class="statusPillClass(activeItem)">{{ statusPillText(activeItem) }}</span>
          <button class="close" type="button" @click="closeEdit">×</button>
        </div>

        <div class="mbody">
          <div v-if="modalError" class="inline-error">{{ modalError }}</div>

          <!-- 只读概览 -->
          <div class="ov-grid">
            <div class="ov-cell"><div class="k">实际职务</div><div class="v">{{ officeTitleLabel(activeItem?.office_title) }}</div></div>
            <div class="ov-cell"><div class="k">授权角色</div><div class="v">{{ roleLabel(activeItem?.role_level) }}</div></div>
            <div class="ov-cell"><div class="k">后台账号</div><div class="v mono">{{ activeItem?.admin_account_exists ? activeItem.admin_login_name : "未创建" }}</div></div>
            <div class="ov-cell"><div class="k">微信绑定</div><div class="v">{{ activeItem?.openid_bound || activeItem?.unionid_bound ? "已绑定" : "未绑定" }}</div></div>
            <div class="ov-cell"><div class="k">账号角色</div><div class="v">{{ activeItem?.admin_account_exists ? accountRoleLabel(activeItem.admin_role_key) : "—" }}</div></div>
            <div class="ov-cell"><div class="k">最近登录</div><div class="v">{{ activeItem?.admin_last_login_at ? formatAuditTime(activeItem.admin_last_login_at) : "暂无记录" }}</div></div>
          </div>

          <!-- 可编辑表单 -->
          <div class="form-sec">授权设置</div>
          <div class="frow two">
            <div>
              <label>实际职务</label>
              <input v-model.trim="editForm.office_title" type="text" maxlength="60" placeholder="如 村委委员" />
            </div>
            <div>
              <label>干部权限级别</label>
              <select v-model="editForm.role_level">
                <option v-for="o in roleLevelOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </div>
          </div>
          <div class="frow two">
            <div>
              <label>后台账号角色</label>
              <select v-model="editForm.admin_role_key">
                <option v-for="o in accountRoleOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </div>
            <div>
              <label>授权状态</label>
              <select v-model="editForm.status">
                <option v-for="o in statusOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </div>
          </div>
          <div class="divider"></div>
          <div class="form-sec">后台账号</div>
          <template v-if="activeItem?.admin_account_exists">
            <div class="frow two">
              <div><label>登录名</label><input :value="activeItem.admin_login_name" type="text" readonly class="readonly" /></div>
              <div><label>显示名</label><input :value="activeItem.admin_display_name || activeItem.real_name" type="text" readonly class="readonly" /></div>
            </div>
            <div class="frow">
              <label>重置密码（留空则不修改）</label>
              <input v-model.trim="resetForm.new_password" type="password" placeholder="至少 12 位，包含两类字符" />
            </div>
            <label class="check">
              <input v-model="resetForm.force_reset" type="checkbox" />
              下次登录后要求本人再次修改密码
            </label>
          </template>
          <template v-else>
            <div class="frow two">
              <div><label>登录名</label><input v-model.trim="accountForm.login_name" type="text" placeholder="如 zengzeyu，登录时使用" /></div>
              <div><label>初始密码</label><input v-model.trim="accountForm.password" type="password" placeholder="至少 12 位，包含两类字符" /></div>
            </div>
            <label class="check">
              <input v-model="accountForm.force_reset" type="checkbox" />
              首次登录后要求本人立即修改密码
            </label>
          </template>
        </div>

        <div class="mfoot">
          <button class="btn btn-ghost" type="button" @click="closeEdit">关闭</button>
          <button
            v-if="canDeleteActive"
            class="btn btn-danger-ghost"
            type="button"
            :disabled="saving"
            @click="removeCadre"
          >删除干部</button>
          <span class="spacer"></span>
          <button
            v-if="activeItem?.admin_account_exists"
            class="btn btn-ghost"
            type="button"
            :disabled="saving"
            @click="resetPassword"
          >重置后台密码</button>
          <button
            v-else
            class="btn btn-ghost"
            type="button"
            :disabled="saving"
            @click="createAccount"
          >创建后台账号</button>
          <button class="btn btn-primary" type="button" :disabled="saving" @click="saveEdit">
            {{ saving ? "保存中..." : "保存授权设置" }}
          </button>
        </div>
      </div>
    </div>

    <!-- ===== 新增干部弹窗 ===== -->
    <div v-if="addVisible" class="mask" @click="closeAdd">
      <div class="modal" @click.stop>
        <div class="mhead">
          <div class="ava">{{ addForm.real_name ? addForm.real_name.slice(0, 1) : "＋" }}</div>
          <div class="ht">
            <h2>新增干部</h2>
            <div class="sub">登记一名新干部，可同时为其创建后台登录账号</div>
          </div>
          <button class="close" type="button" @click="closeAdd">×</button>
        </div>

        <div class="mbody">
          <div v-if="modalError" class="inline-error">{{ modalError }}</div>

          <div class="form-sec">基本信息</div>
          <div class="frow two">
            <div><label>姓名 <span class="req">＊</span></label><input v-model.trim="addForm.real_name" type="text" maxlength="50" placeholder="如 示例人员1" /></div>
            <div><label>实际职务</label><input v-model.trim="addForm.office_title" type="text" maxlength="60" placeholder="如 村委委员" /></div>
          </div>
          <div class="frow two">
            <div>
              <label>所属</label>
              <select v-model="addForm.scope">
                <option value="village">村级</option>
                <option value="town">镇政府</option>
              </select>
            </div>
            <div>
              <label>干部权限级别</label>
              <select v-model="addForm.role_level">
                <option v-for="o in roleLevelOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </div>
          </div>

          <div class="divider"></div>
          <label class="check">
            <input v-model="addForm.create_account" type="checkbox" />
            为该干部创建后台登录账号 <span class="tip">（不勾选则仅登记在名单中，状态显示"未创建"）</span>
          </label>

          <div v-if="addForm.create_account" class="acc-block">
            <div class="form-sec">后台账号</div>
            <div class="frow two">
              <div><label>登录名</label><input v-model.trim="addForm.login_name" type="text" placeholder="如 zengzeyu，登录时使用" /></div>
              <div>
                <label>账号角色</label>
                <select v-model="addForm.admin_role_key">
                  <option v-for="o in accountRoleOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
              </div>
            </div>
            <div class="frow">
              <label>初始密码</label>
              <input v-model.trim="addForm.password" type="password" placeholder="至少 12 位，包含两类字符" />
            </div>
            <label class="check">
              <input v-model="addForm.force_reset" type="checkbox" />
              首次登录后要求本人修改密码
            </label>
          </div>
        </div>

        <div class="mfoot">
          <button class="btn btn-ghost" type="button" @click="closeAdd">取消</button>
          <span class="spacer"></span>
          <button class="btn btn-primary" type="button" :disabled="saving" @click="submitAdd">
            {{ saving ? "提交中..." : "确认新增" }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import { listAdminAuditLogs } from "../../api/audit";
import {
  createAdminCadreAccount,
  createAdminCadreAuthorization,
  deleteAdminCadreAuthorization,
  listAdminCadreAuthorizations,
  resetAdminCadreAccountPassword,
  updateAdminCadreAuthorization,
} from "../../api/cadre";
import { useAuthStore } from "../../stores/auth";
import { extractApiError } from "../../utils/admin-ui";
import { translateAuditAction } from "../../utils/audit";

const authStore = useAuthStore();
const PAGE_SIZE = 7;

const roleLevelOptions = [
  { value: "super_admin", label: "最高权限" },
  { value: "cadre", label: "一般权限" },
];
const accountRoleOptions = [
  { value: "super_admin", label: "超级管理员" },
  { value: "cadre", label: "普通管理员" },
  { value: "readonly", label: "只读协办" },
];
const statusOptions = [
  { value: "active", label: "启用中" },
  { value: "disabled", label: "已停用" },
];

const isSuperAdmin = computed(() => authStore.user?.role_key === "super_admin");

// 干部固定展示顺序（名单外的新增干部排到末尾、按 id）
const CADRE_ORDER = ["得胜村委会", "示例人员5", "示例人员6", "示例人员3", "示例人员4", "示例人员2", "示例人员1"];
function sortCadres(rows) {
  const rank = (name) => {
    const i = CADRE_ORDER.indexOf(String(name || "").trim());
    return i === -1 ? CADRE_ORDER.length : i;
  };
  return [...rows].sort((a, b) => {
    const diff = rank(a.real_name) - rank(b.real_name);
    return diff !== 0 ? diff : (a.id || 0) - (b.id || 0);
  });
}

// 干部名单
const items = ref([]);
const loading = ref(false);
const saving = ref(false);
const errorMessage = ref("");

// 审计日志
const auditRows = ref([]);
const auditLoading = ref(false);
const auditPage = ref(1);

const totalPages = computed(() => Math.max(1, Math.ceil(auditRows.value.length / PAGE_SIZE)));
const pagedAudit = computed(() => {
  const start = (auditPage.value - 1) * PAGE_SIZE;
  return auditRows.value.slice(start, start + PAGE_SIZE);
});

// 编辑弹窗
const editVisible = ref(false);
const activeItem = ref(null);
const modalError = ref("");
const editForm = reactive({
  office_title: "",
  role_level: "cadre",
  admin_role_key: "cadre",
  status: "active",
});
const accountForm = reactive({
  login_name: "",
  password: "",
  force_reset: true,
});
const resetForm = reactive({
  new_password: "",
  force_reset: true,
});

// 新增弹窗
const addVisible = ref(false);
const addForm = reactive({
  real_name: "",
  office_title: "",
  scope: "village",
  role_level: "cadre",
  create_account: false,
  login_name: "",
  admin_role_key: "cadre",
  password: "",
  force_reset: true,
});

const canDeleteActive = computed(
  () => !!activeItem.value && !activeItem.value.admin_account_exists && !activeItem.value.is_default
);

function avatarText(name) {
  const text = String(name || "").trim();
  return text ? text.slice(0, 1) : "村";
}
function officeTitleLabel(value) {
  return String(value || "").trim() || "未设置职务";
}
function roleLabel(value) {
  return roleLevelOptions.find((o) => o.value === value)?.label || "一般权限";
}
function accountRoleLabel(value) {
  return accountRoleOptions.find((o) => o.value === value)?.label || value || "-";
}
function statusPillText(item) {
  if (!item) return "-";
  if (!item.admin_account_exists && item.status === "active") return "未创建";
  return item.status === "active" ? "启用中" : "已停用";
}
function statusPillClass(item) {
  if (!item) return "pill-no";
  if (item.status !== "active") return "pill-no";
  if (item.admin_account_exists) return item.admin_role_key === "super_admin" ? "pill-super" : "pill-on";
  return "pill-no";
}

function isValidAdminPassword(value) {
  const text = String(value || "").trim();
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((pattern) => pattern.test(text));
  return text.length >= 12 && classes.length >= 2;
}

function formatAuditTime(value) {
  const text = String(value || "").trim();
  if (!text) return "-";
  const dt = new Date(text);
  if (Number.isNaN(dt.getTime())) return text;
  const p = (n) => String(n).padStart(2, "0");
  const hm = `${p(dt.getHours())}:${p(dt.getMinutes())}`;
  return `${dt.getFullYear()}-${p(dt.getMonth() + 1)}-${p(dt.getDate())} ${hm}`;
}

async function loadCadres(preserveActiveId = 0) {
  if (!isSuperAdmin.value) return;
  loading.value = true;
  errorMessage.value = "";
  try {
    const rows = await listAdminCadreAuthorizations(authStore.token, {});
    items.value = sortCadres(Array.isArray(rows) ? rows : []);
    if (preserveActiveId) {
      const current = items.value.find((it) => it.id === preserveActiveId);
      if (current && editVisible.value) {
        activeItem.value = current;
      }
    }
  } catch (err) {
    errorMessage.value = extractApiError(err, "干部授权名单加载失败");
  } finally {
    loading.value = false;
  }
}

async function loadAudit() {
  if (!isSuperAdmin.value) return;
  auditLoading.value = true;
  try {
    const rows = await listAdminAuditLogs(authStore.token, { limit: 200 });
    auditRows.value = Array.isArray(rows) ? rows : [];
    auditPage.value = 1;
  } catch {
    auditRows.value = [];
  } finally {
    auditLoading.value = false;
  }
}

function openEdit(item) {
  activeItem.value = item;
  modalError.value = "";
  editForm.office_title = item.office_title || "";
  editForm.role_level = item.role_level || "cadre";
  editForm.admin_role_key = item.admin_role_key || (item.role_level === "super_admin" ? "super_admin" : "cadre");
  editForm.status = item.status || "active";
  accountForm.login_name = "";
  accountForm.password = "";
  accountForm.force_reset = true;
  resetForm.new_password = "";
  resetForm.force_reset = true;
  editVisible.value = true;
}
function closeEdit() {
  editVisible.value = false;
  activeItem.value = null;
}

async function saveEdit() {
  if (!activeItem.value) return;
  saving.value = true;
  modalError.value = "";
  try {
    const updated = await updateAdminCadreAuthorization(authStore.token, activeItem.value.id, {
      office_title: editForm.office_title,
      role_level: editForm.role_level,
      admin_role_key: editForm.admin_role_key,
      can_export_full_id: false,
      status: editForm.status,
    });
    activeItem.value = updated;
    await loadCadres(updated.id);
    await loadAudit();
  } catch (err) {
    modalError.value = extractApiError(err, "干部授权保存失败");
  } finally {
    saving.value = false;
  }
}

async function createAccount() {
  if (!activeItem.value) return;
  if (!String(accountForm.login_name || "").trim()) {
    modalError.value = "请先填写后台登录名。";
    return;
  }
  if (!isValidAdminPassword(accountForm.password)) {
    modalError.value = "初始密码至少 12 位，并包含至少两类字符。";
    return;
  }
  saving.value = true;
  modalError.value = "";
  try {
    const updated = await createAdminCadreAccount(authStore.token, activeItem.value.id, {
      login_name: accountForm.login_name,
      display_name: activeItem.value.real_name || "",
      password: accountForm.password,
      role_key: editForm.admin_role_key,
      force_reset: accountForm.force_reset,
    });
    activeItem.value = updated;
    await loadCadres(updated.id);
    await loadAudit();
  } catch (err) {
    modalError.value = extractApiError(err, "后台账号创建失败");
  } finally {
    saving.value = false;
  }
}

async function resetPassword() {
  if (!activeItem.value?.admin_account_exists) return;
  if (!isValidAdminPassword(resetForm.new_password)) {
    modalError.value = "新密码至少 12 位，并包含至少两类字符。";
    return;
  }
  saving.value = true;
  modalError.value = "";
  try {
    await resetAdminCadreAccountPassword(authStore.token, activeItem.value.id, {
      new_password: resetForm.new_password,
      force_reset: resetForm.force_reset,
    });
    resetForm.new_password = "";
    await loadAudit();
    modalError.value = "";
    closeEdit();
  } catch (err) {
    modalError.value = extractApiError(err, "后台密码重置失败");
  } finally {
    saving.value = false;
  }
}

async function removeCadre() {
  if (!activeItem.value) return;
  if (!window.confirm(`确认删除干部「${activeItem.value.real_name}」吗？该操作会记入审计日志。`)) {
    return;
  }
  saving.value = true;
  modalError.value = "";
  try {
    await deleteAdminCadreAuthorization(authStore.token, activeItem.value.id);
    closeEdit();
    await loadCadres();
    await loadAudit();
  } catch (err) {
    modalError.value = extractApiError(err, "删除干部失败");
  } finally {
    saving.value = false;
  }
}

function openAdd() {
  modalError.value = "";
  addForm.real_name = "";
  addForm.office_title = "";
  addForm.scope = "village";
  addForm.role_level = "cadre";
  addForm.create_account = false;
  addForm.login_name = "";
  addForm.admin_role_key = "cadre";
  addForm.password = "";
  addForm.force_reset = true;
  addVisible.value = true;
}
function closeAdd() {
  addVisible.value = false;
}

async function submitAdd() {
  if (!String(addForm.real_name || "").trim()) {
    modalError.value = "请填写干部姓名。";
    return;
  }
  if (addForm.create_account) {
    if (!String(addForm.login_name || "").trim()) {
      modalError.value = "勾选创建账号后，请填写后台登录名。";
      return;
    }
    if (!isValidAdminPassword(addForm.password)) {
      modalError.value = "初始密码至少 12 位，并包含至少两类字符。";
      return;
    }
  }
  saving.value = true;
  modalError.value = "";
  try {
    await createAdminCadreAuthorization(authStore.token, {
      real_name: addForm.real_name,
      office_title: addForm.office_title,
      role_level: addForm.role_level,
      can_export_full_id: false,
      status: "active",
      create_account: addForm.create_account,
      login_name: addForm.login_name,
      password: addForm.password,
      admin_role_key: addForm.admin_role_key,
      force_reset: addForm.force_reset,
    });
    closeAdd();
    await loadCadres();
    await loadAudit();
  } catch (err) {
    modalError.value = extractApiError(err, "新增干部失败");
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadCadres();
  loadAudit();
});
</script>

<style scoped>
.sys-page {
  display: grid;
  gap: 18px;
}

.permission-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: var(--card-shadow);
  padding: 20px 22px;
  color: var(--color-text-sub);
}

/* 两栏 */
.sys-grid {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 18px;
  align-items: start;
}

.card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: var(--card-shadow);
  display: flex;
  flex-direction: column;
}

.cardhead {
  display: flex;
  align-items: center;
  padding: 17px 22px;
  border-bottom: 1px solid var(--color-border-light);
  gap: 12px;
}
.cardhead h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.cardhead .meta {
  font-size: 12.5px;
  color: var(--color-text-hint);
}
.cardhead .meta-right {
  margin-left: auto;
}

.btn-add {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: var(--color-primary);
  color: #fff;
  border-radius: 9px;
  padding: 8px 15px;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 5px 12px -7px rgba(166, 61, 47, 0.55);
  line-height: 1;
}
.btn-add:hover {
  background: var(--color-primary-light);
}
.btn-add .plus {
  font-size: 16px;
}

/* 干部行 */
.crow-list {
  display: flex;
  flex-direction: column;
}
.crow {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 15px 22px;
  border-bottom: 1px solid var(--color-border-light);
  cursor: pointer;
  background: transparent;
  border-left: none;
  border-right: none;
  border-top: none;
  width: 100%;
  text-align: left;
  font: inherit;
  transition: background 0.12s;
}
.crow:last-child {
  border-bottom: none;
}
.crow:hover {
  background: #fbf8f1;
}
.crow .ava {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-primary-pale);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  font-family: var(--font-serif);
  flex-shrink: 0;
}
.crow .info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.crow .info .nm {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text);
}
.crow .info .role {
  font-size: 12.5px;
  color: var(--color-text-hint);
  margin-top: 3px;
}
.crow .acc {
  text-align: right;
  margin-right: 6px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.crow .acc .a1 {
  font-size: 13px;
  color: var(--color-text-sub);
  font-family: ui-monospace, monospace;
}
.crow .acc .a1-empty {
  color: var(--color-text-hint);
  font-family: inherit;
}
.crow .acc .a2 {
  font-size: 11.5px;
  color: var(--color-text-hint);
}
.crow .arr {
  color: var(--color-text-hint);
  font-size: 18px;
}

.pill {
  font-size: 12px;
  padding: 3px 11px;
  border-radius: 13px;
  font-weight: 500;
  display: inline-block;
  white-space: nowrap;
}
.pill-on {
  background: #e9f0e7;
  color: var(--color-matcha);
}
.pill-no {
  background: #f1ece0;
  color: var(--color-text-hint);
}
.pill-super {
  background: var(--color-primary-pale);
  color: var(--color-primary);
}

/* 审计日志 */
.logbody {
  display: flex;
  flex-direction: column;
}
.lrow {
  display: flex;
  gap: 13px;
  padding: 13px 22px;
  border-bottom: 1px solid var(--color-border-light);
}
.lrow .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  margin-top: 7px;
  flex-shrink: 0;
}
.lrow .lc {
  flex: 1;
  min-width: 0;
}
.lrow .human {
  font-size: 14px;
  color: var(--color-text);
}
.lrow .human b {
  font-weight: 500;
}
.lrow .keytag {
  display: inline-block;
  font-size: 11px;
  color: var(--color-text-hint);
  font-family: ui-monospace, monospace;
  background: #f4efe3;
  border: 1px solid var(--color-border-light);
  padding: 2px 8px;
  border-radius: 6px;
  margin-top: 6px;
}
.lrow .tm {
  font-size: 12px;
  color: var(--color-text-hint);
  white-space: nowrap;
  flex-shrink: 0;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 16px;
  border-top: 1px solid var(--color-border-light);
}
.pager button {
  min-width: 32px;
  height: 32px;
  border: 1px solid var(--color-border);
  background: #fff;
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  color: var(--color-text-sub);
  cursor: pointer;
  padding: 0 8px;
}
.pager button:hover:not(:disabled) {
  background: #f7f2e8;
}
.pager button.on {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}
.pager button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.pager .ellip {
  color: var(--color-text-hint);
  font-size: 13px;
  padding: 0 2px;
}
.pager .page-ind {
  font-size: 13px;
  color: var(--color-text-sub);
  min-width: 86px;
  text-align: center;
}

.empty-block,
.inline-error {
  padding: 16px 22px;
  font-size: 14px;
  color: var(--color-text-sub);
}
.inline-error {
  margin: 14px 22px 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: #fef2f2;
  color: #991b1b;
}

/* ===== 弹窗 ===== */
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
  width: 640px;
  max-width: 100%;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 30px 70px -20px rgba(40, 25, 15, 0.5);
}
.mhead {
  padding: 24px 28px 18px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: flex-start;
}
.mhead .ava {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: var(--color-primary-pale);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  font-weight: 600;
  font-family: var(--font-serif);
  margin-right: 14px;
  flex-shrink: 0;
}
.mhead .ht {
  flex: 1;
}
.mhead .ht h2 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 21px;
  font-weight: 600;
}
.mhead .ht .sub {
  font-size: 12.5px;
  color: var(--color-text-hint);
  margin-top: 5px;
}
.mhead .pill {
  margin-right: 12px;
  margin-top: 4px;
}
.mhead .close {
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

.ov-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--color-border-light);
  border: 1px solid var(--color-border-light);
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 22px;
}
.ov-cell {
  background: #ffffff;
  padding: 14px 18px;
}
.ov-cell .k {
  font-size: 12px;
  color: var(--color-text-hint);
  margin-bottom: 6px;
}
.ov-cell .v {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text);
}
.ov-cell .v.mono {
  font-family: ui-monospace, monospace;
}

.form-sec {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-matcha);
  margin: 0 0 14px;
}
.frow {
  margin-bottom: 15px;
}
.frow label {
  font-size: 12.5px;
  color: var(--color-text-hint);
  display: block;
  margin-bottom: 7px;
}
.frow .req {
  color: var(--color-primary);
}
.frow select,
.frow input {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 11px 13px;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  background: #fff;
  color: var(--color-text);
}
.frow select:focus,
.frow input:focus {
  border-color: var(--color-primary);
}
.frow input.readonly {
  background: #ffffff;
  color: var(--color-text-hint);
}
.frow.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.check {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13.5px;
  color: var(--color-text-sub);
  margin: 6px 0 16px;
  cursor: pointer;
}
.check input {
  width: 17px;
  height: 17px;
  accent-color: var(--color-primary);
}
.check .tip {
  font-size: 12px;
  color: var(--color-text-hint);
}
.divider {
  height: 1px;
  background: var(--color-border-light);
  margin: 8px 0 18px;
}
.acc-block {
  margin-top: 16px;
}

.mfoot {
  padding: 16px 28px;
  border-top: 1px solid var(--color-border-light);
  display: flex;
  gap: 12px;
  background: #ffffff;
  align-items: center;
}
.mfoot .spacer {
  flex: 1;
}
.btn {
  border: none;
  border-radius: 10px;
  padding: 0 20px;
  height: 44px;
  font-family: inherit;
  font-size: 14.5px;
  font-weight: 500;
  cursor: pointer;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-primary {
  background: var(--color-primary);
  color: #fff;
  box-shadow: 0 6px 14px -8px rgba(166, 61, 47, 0.55);
}
.btn-ghost {
  background: #fff;
  border: 1px solid var(--color-border);
  color: var(--color-text-sub);
}
.btn-danger-ghost {
  background: #fff;
  border: 1px solid #e0c4be;
  color: var(--color-primary);
}

@media (max-width: 1100px) {
  .sys-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 720px) {
  .ov-grid,
  .frow.two {
    grid-template-columns: 1fr;
  }

  .sys-page {
    gap: 12px;
  }

  .card {
    border-radius: 10px;
  }

  .cardhead {
    padding: 12px;
    flex-wrap: wrap;
  }

  .cardhead .meta-right {
    margin-left: 0;
  }

  .btn-add {
    min-height: 42px;
  }

  .crow {
    padding: 14px 12px;
    display: grid;
    grid-template-columns: 40px minmax(0, 1fr) auto;
    gap: 8px 10px;
    align-items: center;
  }

  .crow .ava {
    grid-row: 1 / span 2;
  }

  .crow .acc {
    grid-column: 2;
    grid-row: 2;
    margin-right: 0;
    text-align: left;
  }

  .crow .pill {
    grid-column: 3;
    grid-row: 1;
  }

  .crow .arr {
    grid-column: 3;
    grid-row: 2;
    justify-self: end;
  }

  .lrow {
    padding: 12px;
    display: grid;
    grid-template-columns: 8px minmax(0, 1fr);
  }

  .lrow .tm {
    grid-column: 2;
    white-space: normal;
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
    align-items: center;
  }

  .mhead .ava,
  .mhead .pill {
    display: none;
  }

  .mhead .ht h2 {
    font-size: 18px;
  }

  .mbody {
    padding: 12px;
    overscroll-behavior: contain;
  }

  .mfoot {
    padding: 12px 12px calc(12px + env(safe-area-inset-bottom));
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .mfoot .spacer {
    display: none;
  }

  .mfoot .btn {
    width: 100%;
    padding: 0 10px;
  }
}
</style>
