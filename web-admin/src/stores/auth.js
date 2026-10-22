import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
  beginAdminMfaSetup,
  changeAdminPassword,
  confirmAdminMfaSetup,
  fetchAdminMe,
  loginAdmin,
  logoutAdmin,
} from "../api/auth";

const TOKEN_KEY = "deshengcun_admin_token";
const IS_ADMIN_PREVIEW = import.meta.env.DEV && import.meta.env.VITE_ADMIN_PREVIEW === "1";
const PREVIEW_TOKEN = "deshengcun-local-ui-preview";
const PREVIEW_USER = {
  id: 0,
  login_name: "admin",
  real_name: "得胜村委会",
  display_name: "得胜村委会",
  role_key: "super_admin",
  office_title: "村委会管理员",
};

function readStoredToken() {
  if (IS_ADMIN_PREVIEW) {
    return window.sessionStorage.getItem(TOKEN_KEY) || PREVIEW_TOKEN;
  }
  try {
    return window.sessionStorage.getItem(TOKEN_KEY) || "";
  } catch (err) {
    return "";
  }
}

function writeStoredToken(token) {
  try {
    if (token) {
      window.sessionStorage.setItem(TOKEN_KEY, token);
      return;
    }
    window.sessionStorage.removeItem(TOKEN_KEY);
  } catch (err) {
    // Ignore storage failures in degraded browser modes.
  }
}

export const useAuthStore = defineStore("adminAuth", () => {
  const token = ref(readStoredToken());
  const user = ref(IS_ADMIN_PREVIEW && token.value ? PREVIEW_USER : null);
  const loadingProfile = ref(false);

  const isAuthenticated = computed(() => !!token.value && !!user.value);

  function setSession(nextToken, nextUser) {
    token.value = nextToken || "";
    user.value = nextUser || null;
    writeStoredToken(token.value);
  }

  function clearSession() {
    token.value = "";
    user.value = null;
    writeStoredToken("");
  }

  async function login(payload) {
    if (IS_ADMIN_PREVIEW) {
      const previewLoginName = String(payload?.login_name || "admin").trim() || "admin";
      const nextUser = {
        ...PREVIEW_USER,
        login_name: previewLoginName,
      };
      setSession(PREVIEW_TOKEN, nextUser);
      return {
        token: PREVIEW_TOKEN,
        user: nextUser,
      };
    }
    const result = await loginAdmin(payload);
    setSession(result.token || "", result.user || null);
    return result;
  }

  async function fetchMe() {
    if (IS_ADMIN_PREVIEW) {
      user.value = PREVIEW_USER;
      return PREVIEW_USER;
    }
    if (!token.value) {
      clearSession();
      return null;
    }
    loadingProfile.value = true;
    try {
      const profile = await fetchAdminMe(token.value);
      user.value = profile;
      return profile;
    } finally {
      loadingProfile.value = false;
    }
  }

  async function logout() {
    if (IS_ADMIN_PREVIEW) {
      clearSession();
      return;
    }
    if (token.value) {
      try {
        await logoutAdmin(token.value);
      } finally {
        clearSession();
      }
      return;
    }
    clearSession();
  }

  async function updatePassword(payload) {
    if (!token.value) {
      throw new Error("login_required");
    }
    return changeAdminPassword(token.value, payload);
  }

  async function beginMfaSetup() {
    if (!token.value) {
      throw new Error("login_required");
    }
    return beginAdminMfaSetup(token.value);
  }

  async function confirmMfaSetup(code) {
    if (!token.value) {
      throw new Error("login_required");
    }
    const result = await confirmAdminMfaSetup(token.value, code);
    if (result?.user) {
      user.value = result.user;
    }
    return result;
  }

  return {
    token,
    user,
    loadingProfile,
    isAuthenticated,
    setSession,
    clearSession,
    login,
    fetchMe,
    logout,
    updatePassword,
    beginMfaSetup,
    confirmMfaSetup,
  };
});
