<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-badge">得胜村</div>
      <h1 class="login-title">得胜村便民服务程序后台管理</h1>
      <p class="login-sub">用于村干部登录和日常业务管理。</p>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label class="field">
          <span>登录账号</span>
          <input v-model.trim="form.login_name" type="text" placeholder="请输入后台账号" autocomplete="username" />
        </label>

        <label v-if="mfaRequired" class="field">
          <span>双因素验证码</span>
          <input
            v-model.trim="form.mfa_code"
            type="text"
            inputmode="numeric"
            maxlength="32"
            placeholder="请输入6位动态验证码或恢复码"
            autocomplete="one-time-code"
          />
        </label>

        <label class="field">
          <span>登录密码</span>
          <input v-model="form.password" type="password" placeholder="请输入后台密码" autocomplete="current-password" />
        </label>

        <div v-if="errorText" class="error-box">{{ errorText }}</div>

        <button class="primary-btn" type="submit" :disabled="submitting">
          {{ submitting ? "登录中..." : "登录后台" }}
        </button>
      </form>
    </div>
    <footer class="login-footer">
      <div class="footer-org">平江县上塔市镇得胜村村委会</div>
      <div class="footer-icp">
        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">湘ICP备2026012359号-2</a>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../../stores/auth";
import { extractApiError } from "../../utils/admin-ui";

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();

const form = reactive({
  login_name: "",
  password: "",
  mfa_code: "",
});

const submitting = ref(false);
const errorText = ref("");
const mfaRequired = ref(false);

function mapError(err) {
  return extractApiError(err, "登录失败，请稍后重试。");
}

async function handleSubmit() {
  if (!form.login_name || !form.password) {
    errorText.value = "请先填写账号和密码。";
    return;
  }
  submitting.value = true;
  errorText.value = "";
  try {
    await authStore.login(form);
    const needsSetup = Boolean(
      authStore.user?.password_reset_required || authStore.user?.mfa_setup_required
    );
    const redirect = needsSetup
      ? "/security-setup"
      : String(route.query.redirect || "/").trim() || "/";
    router.replace(redirect);
  } catch (err) {
    const detail = String(err?.response?.data?.detail || "");
    if (detail === "admin_mfa_code_required") {
      mfaRequired.value = true;
      form.mfa_code = "";
      errorText.value = "密码验证通过，请输入身份验证器中的6位动态验证码。";
    } else if (detail === "invalid_admin_mfa_code") {
      mfaRequired.value = true;
      form.mfa_code = "";
      errorText.value = "动态验证码或恢复码不正确。";
    } else {
      errorText.value = mapError(err);
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: 32px;
  background: #ffffff;
}

@media (max-width: 640px) {
  .login-page {
    place-items: start center;
    align-content: center;
    padding: max(20px, env(safe-area-inset-top)) 16px max(20px, env(safe-area-inset-bottom));
  }

  .login-card {
    border-radius: 16px;
    padding: 22px 18px;
  }

  .login-title {
    font-size: 24px;
    line-height: 1.35;
    letter-spacing: 0.04em;
  }

  .login-form {
    margin-top: 20px;
  }

  .login-footer {
    margin-top: 22px;
  }
}

.login-card {
  width: min(520px, 100%);
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(229, 221, 203, 0.92);
  border-radius: 24px;
  padding: 26px 28px;
  box-shadow: 0 22px 48px rgba(26, 22, 18, 0.12);
}

.login-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #f5e8e6;
  color: #a63d2f;
  font-size: 13px;
  font-weight: 700;
}

.login-title {
  margin: 18px 0 0;
  font-size: 30px;
  line-height: 1.2;
  color: #1a1612;
  font-family: "Songti SC", "STSong", Georgia, serif;
  letter-spacing: 0.06em;
}

.login-sub {
  margin: 10px 0 0;
  color: #7a6e64;
  font-size: 14px;
}

.login-form {
  margin-top: 24px;
  display: grid;
  gap: 16px;
}

.field {
  display: grid;
  gap: 8px;
  font-size: 14px;
  color: #5c5047;
}

.field input {
  height: 48px;
  border-radius: 12px;
  border: 1px solid #e5ddcb;
  padding: 0 14px;
  background: #fff;
}

.error-box {
  border-radius: 12px;
  background: #fef2f2;
  color: #b91c1c;
  padding: 12px 14px;
  font-size: 14px;
}

.primary-btn {
  height: 48px;
  border: 0;
  border-radius: 12px;
  background: linear-gradient(135deg, #a63d2f 0%, #c04535 100%);
  color: #fff;
  cursor: pointer;
  font-weight: 700;
  box-shadow: 0 12px 24px rgba(166, 61, 47, 0.16);
}

.primary-btn:disabled {
  opacity: 0.7;
  cursor: default;
}

.login-footer {
  margin-top: 28px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.footer-org {
  color: #1a1a1a;
  font-size: 13px;
}

.footer-icp a {
  color: #2563eb;
  font-size: 13px;
  text-decoration: none;
}

.footer-icp a:hover {
  text-decoration: underline;
}
</style>
