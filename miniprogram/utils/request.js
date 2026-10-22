const { getApiBase, getCloudbaseConfig } = require("./api");

const REQUEST_TIMEOUT_MS = 30000;
const RECOVERABLE_SESSION_ERRORS = new Set(["invalid_token", "token_expired"]);
let sessionRecoveryPromise = null;

function getGlobalData() {
  const app = typeof getApp === "function" ? getApp() : null;
  return app?.globalData || null;
}

function currentProfileRole() {
  const token = wx.getStorageSync("token") || "";
  return token ? "villager" : "guest";
}

function redirectCadreAccess(detail) {
  const globalData = getGlobalData();
  if (!globalData) {
    return;
  }
  const reason = String(detail || "").trim();
  const content =
    reason === "cadre_authorization_required"
      ? "当前小程序不再作为干部主要工作入口，干部管理已迁移到电脑端 Web 后台，请使用后台账号在浏览器登录。"
      : "村干部工作台正在迁移到电脑端 Web 后台，请改用后台账号在浏览器登录处理村务。";
  if (globalData.cadreRedirecting) {
    return;
  }
  globalData.cadreRedirecting = true;
  wx.showModal({
    title: "请改用干部 Web 后台",
    content,
    showCancel: false,
    confirmText: "知道了",
    complete() {
      setTimeout(() => {
        const latestGlobalData = getGlobalData();
        if (latestGlobalData) {
          latestGlobalData.cadreRedirecting = false;
        }
      }, 300);
    },
  });
}

function buildHeaders(options) {
  const role = options.role || currentProfileRole();
  const token = Object.prototype.hasOwnProperty.call(options, "token")
    ? options.token
    : wx.getStorageSync("token") || "";
  return {
    "content-type": "application/json",
    "X-Role": role,
    "X-Token": token,
  };
}

function shouldUseCloudContainer(options) {
  if (options.forceHttp) {
    return false;
  }
  const cloudbase = getCloudbaseConfig();
  return !!(
    cloudbase.enabled &&
    cloudbase.envId &&
    cloudbase.service &&
    wx.cloud &&
    typeof wx.cloud.callContainer === "function"
  );
}

function performHttpRequest(options, headers) {
  const base = getApiBase();
  const url = `${base}${options.path}`;
  return new Promise((resolve, reject) => {
    wx.request({
      url,
      method: options.method || "GET",
      data: options.data || {},
      header: headers,
      timeout: options.timeout || REQUEST_TIMEOUT_MS,
      success: resolve,
      fail: reject,
    });
  });
}

function performCloudRequest(options, headers) {
  const cloudbase = getCloudbaseConfig();
  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: { env: cloudbase.envId },
      path: `/api/v1${options.path}`,
      method: options.method || "GET",
      header: {
        ...headers,
        "X-WX-SERVICE": cloudbase.service,
      },
      data: options.data || {},
      timeout: options.timeout || REQUEST_TIMEOUT_MS,
      success: resolve,
      fail: reject,
    });
  });
}

function normalizeContainerResponse(res) {
  if (res && typeof res.statusCode === "number") {
    return res;
  }
  return {
    statusCode: Number(res?.statusCode || 500) || 500,
    data: res?.data || res || {},
  };
}

function requestOnce(options) {
  const headers = buildHeaders(options);
  const executor = shouldUseCloudContainer(options) ? performCloudRequest : performHttpRequest;
  return executor(options, headers).then((rawRes) => {
    const res = normalizeContainerResponse(rawRes);
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.data;
    }
    const detail = String(res.data?.detail || "").trim();
    if (
      !options.skipCadreRedirect &&
      (detail === "cadre_stepup_required" || detail === "cadre_authorization_required")
    ) {
      redirectCadreAccess(detail);
    }
    return Promise.reject(res.data || { detail: "request_failed" });
  });
}

function getWechatLoginCode() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(result) {
        const code = String(result?.code || "").trim();
        if (!code) {
          reject({ detail: "invalid_wechat_code" });
          return;
        }
        resolve(code);
      },
      fail: reject,
    });
  });
}

function recoverVillagerSession(options) {
  if (sessionRecoveryPromise) {
    return sessionRecoveryPromise;
  }
  sessionRecoveryPromise = getWechatLoginCode()
    .then((code) =>
      requestOnce({
        path: "/auth/wechat-login",
        method: "POST",
        data: { code },
        role: "guest",
        token: "",
        forceHttp: !!options.forceHttp,
        skipAuthRecovery: true,
      })
    )
    .then((result) => {
      const token = String(result?.token || "").trim();
      if (!token) {
        return Promise.reject({ detail: "invalid_token" });
      }
      wx.setStorageSync("token", token);
      const globalData = getGlobalData();
      if (globalData) {
        globalData.userProfile = result?.user || null;
      }
      return result;
    })
    .finally(() => {
      sessionRecoveryPromise = null;
    });
  return sessionRecoveryPromise;
}

function shouldRecoverSession(options, error, hadToken) {
  if (!hadToken || options.skipAuthRecovery || options.sessionRecoveryAttempted) {
    return false;
  }
  if (options.path === "/auth/wechat-login" || options.path === "/auth/logout") {
    return false;
  }
  const detail = String(error?.detail || "").trim();
  return RECOVERABLE_SESSION_ERRORS.has(detail);
}

function request(options) {
  const hadToken = !!wx.getStorageSync("token");
  return requestOnce(options).catch(async (error) => {
    if (!shouldRecoverSession(options, error, hadToken)) {
      return Promise.reject(error);
    }
    await recoverVillagerSession(options);
    return requestOnce({
      ...options,
      sessionRecoveryAttempted: true,
    });
  });
}

module.exports = {
  request,
};
