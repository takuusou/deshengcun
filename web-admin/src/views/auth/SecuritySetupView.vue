<template>
  <main class="setup-page">
    <section class="setup-card">
      <div class="badge">后台安全设置</div>
      <h1>完成账号安全配置</h1>
      <p class="intro">完成以下步骤前，账号不能进入业务后台。</p>

      <div v-if="errorText" class="error-box">{{ errorText }}</div>
      <div v-if="statusText" class="success-box">{{ statusText }}</div>

      <form v-if="authStore.user?.password_reset_required" class="section" @submit.prevent="changePassword">
        <h2>第一步：修改初始密码</h2>
        <p>新密码至少12位，并包含字母、数字或符号中的至少两类。</p>
        <label>
          <span>当前密码</span>
          <input v-model="passwordForm.current_password" type="password" autocomplete="current-password" />
        </label>
        <label>
          <span>新密码</span>
          <input v-model="passwordForm.new_password" type="password" autocomplete="new-password" />
        </label>
        <label>
          <span>再次输入新密码</span>
          <input v-model="passwordForm.confirm_password" type="password" autocomplete="new-password" />
        </label>
        <button type="submit" :disabled="busy">{{ busy ? "处理中..." : "确认修改密码" }}</button>
      </form>

      <section v-else-if="authStore.user?.mfa_setup_required" class="section">
        <h2>第二步：绑定双因素认证</h2>
        <p>使用微信“腾讯身份验证器”、Microsoft Authenticator、1Password等TOTP应用添加账号。</p>

        <button v-if="!mfaSetup" type="button" :disabled="busy" @click="startMfaSetup">
          {{ busy ? "生成中..." : "生成绑定密钥" }}
        </button>

        <template v-else>
          <div class="secret-box">
            <div>发行方：{{ mfaSetup.issuer }}</div>
            <div>账号：{{ mfaSetup.account_label }}</div>
            <div class="secret">{{ mfaSetup.secret }}</div>
            <a :href="mfaSetup.otpauth_uri">尝试在本机身份验证器中打开</a>
          </div>
          <label>
            <span>身份验证器中的6位验证码</span>
            <input v-model.trim="mfaCode" type="text" inputmode="numeric" maxlength="6" autocomplete="one-time-code" />
          </label>
          <button type="button" :disabled="busy" @click="confirmMfa">
            {{ busy ? "验证中..." : "验证并启用" }}
          </button>
        </template>
      </section>

      <section v-else-if="recoveryCodes.length" class="section">
        <h2>保存一次性恢复码</h2>
        <p>每个恢复码只能使用一次。请离线保存，不要截图上传到聊天或网盘。</p>
        <pre>{{ recoveryCodes.join("\n") }}</pre>
        <button type="button" @click="finishSetup">我已安全保存，进入后台</button>
      </section>

      <section v-else class="section">
        <h2>安全设置已完成</h2>
        <button type="button" @click="finishSetup">进入后台</button>
      </section>

      <button class="logout" type="button" @click="logout">退出当前账号</button>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../../stores/auth";
import { extractApiError } from "../../utils/admin-ui";

const authStore = useAuthStore();
const router = useRouter();
const busy = ref(false);
const errorText = ref("");
const statusText = ref("");
const mfaSetup = ref(null);
const mfaCode = ref("");
const recoveryCodes = ref([]);
const passwordForm = reactive({
  current_password: "",
  new_password: "",
  confirm_password: "",
});

async function changePassword() {
  errorText.value = "";
  statusText.value = "";
  if (passwordForm.new_password.length < 12) {
    errorText.value = "新密码至少需要12位。";
    return;
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    errorText.value = "两次输入的新密码不一致。";
    return;
  }
  busy.value = true;
  try {
    await authStore.updatePassword({
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password,
    });
    await authStore.fetchMe();
    passwordForm.current_password = "";
    passwordForm.new_password = "";
    passwordForm.confirm_password = "";
    statusText.value = "密码已修改，请继续绑定双因素认证。";
  } catch (error) {
    errorText.value = extractApiError(error, "密码修改失败，请稍后重试。");
  } finally {
    busy.value = false;
  }
}

async function startMfaSetup() {
  busy.value = true;
  errorText.value = "";
  try {
    mfaSetup.value = await authStore.beginMfaSetup();
  } catch (error) {
    errorText.value = extractApiError(error, "生成双因素绑定信息失败。");
  } finally {
    busy.value = false;
  }
}

async function confirmMfa() {
  if (!/^\d{6}$/.test(mfaCode.value)) {
    errorText.value = "请输入身份验证器显示的6位验证码。";
    return;
  }
  busy.value = true;
  errorText.value = "";
  try {
    const result = await authStore.confirmMfaSetup(mfaCode.value);
    recoveryCodes.value = Array.isArray(result?.recovery_codes) ? result.recovery_codes : [];
    mfaCode.value = "";
    mfaSetup.value = null;
    statusText.value = "双因素认证已启用。";
  } catch (error) {
    errorText.value = extractApiError(error, "验证码不正确或已经过期。");
  } finally {
    busy.value = false;
  }
}

function finishSetup() {
  recoveryCodes.value = [];
  router.replace("/");
}

async function logout() {
  await authStore.logout();
  router.replace("/login");
}
</script>

<style scoped>
.setup-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: #f7f4ee;
}
.setup-card {
  width: min(620px, 100%);
  padding: 28px;
  border: 1px solid #e5ddcb;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 20px 44px rgba(26, 22, 18, 0.12);
}
.badge { color: #a63d2f; font-weight: 700; }
h1 { margin: 12px 0 4px; }
.intro, .section p { color: #6b625a; line-height: 1.7; }
.section { display: grid; gap: 14px; margin-top: 24px; }
.section h2 { margin: 0; font-size: 20px; }
label { display: grid; gap: 7px; }
input { height: 44px; padding: 0 12px; border: 1px solid #d9d0c0; border-radius: 10px; }
button { min-height: 44px; padding: 0 16px; border: 0; border-radius: 10px; background: #a63d2f; color: #fff; font-weight: 700; cursor: pointer; }
button:disabled { opacity: 0.6; cursor: default; }
.logout { margin-top: 22px; background: transparent; color: #6b625a; border: 1px solid #d9d0c0; }
.error-box, .success-box { margin-top: 16px; padding: 12px; border-radius: 10px; }
.error-box { background: #fef2f2; color: #b91c1c; }
.success-box { background: #ecfdf5; color: #047857; }
.secret-box, pre { padding: 14px; border-radius: 10px; background: #f7f4ee; overflow-wrap: anywhere; }
.secret { margin: 8px 0; font-family: ui-monospace, monospace; font-weight: 700; letter-spacing: 0.08em; }
pre { white-space: pre-wrap; line-height: 1.7; }
</style>
