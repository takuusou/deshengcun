const { request } = require("./request");
const {
  getToken,
  getUserProfile,
  setUserProfile,
  clearSession,
} = require("./auth");
const { getErrorMessage } = require("./messages");

function hasToken() {
  return !!getToken();
}

function isVerifiedVillager(profile) {
  return !!profile && profile.auth_status === "verified";
}

function openAuthCenter() {
  wx.navigateTo({ url: "/pages/entry/entry" });
}

function promptForAuth(options = {}) {
  const title = options.title || "提交需登记身份信息";
  const content =
    options.content || "提交前请先登录并完成基础实名登记。";
  const confirmText = options.confirmText || "去登录";
  const cancelText = options.cancelText || "先返回";
  return new Promise((resolve) => {
    wx.showModal({
      title,
      content,
      confirmText,
      cancelText,
      success(res) {
        if (res.confirm) {
          openAuthCenter();
        }
        resolve(false);
      },
      fail() {
        resolve(false);
      },
    });
  });
}

async function resolveViewerProfile(options = {}) {
  const token = getToken();
  if (!token) {
    return null;
  }
  const localProfile = getUserProfile();
  if (localProfile && !options.refresh) {
    return localProfile;
  }
  try {
    const profile = await request({ path: "/auth/me" });
    setUserProfile(profile);
    return profile;
  } catch (err) {
    const detail = String(err?.detail || err?.message || "").trim();
    if (detail === "invalid_token" || detail === "token_expired") {
      clearSession();
      return null;
    }
    if (!options.silent) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    }
    return localProfile || null;
  }
}

async function ensureVerifiedVillager(options = {}) {
  const profile = await resolveViewerProfile({ refresh: true, silent: true });
  if (isVerifiedVillager(profile)) {
    return true;
  }
  return promptForAuth(options);
}

function showGuestBrowsePromptOnce() {
  if (hasToken()) {
    return;
  }
  const app = getApp();
  if (app?.globalData?.guestBrowsePromptShown) {
    return;
  }
  if (app?.globalData) {
    app.globalData.guestBrowsePromptShown = true;
  }
  wx.showModal({
    title: "可先浏览小程序",
    content: "您现在可以先查看通知、公开和政务内容。办理证明、提交诉求、报名活动时，需要先登录并完成基础实名登记。",
    confirmText: "去登录",
    cancelText: "先看看",
    success(res) {
      if (res.confirm) {
        openAuthCenter();
      }
    },
  });
}

module.exports = {
  hasToken,
  isVerifiedVillager,
  openAuthCenter,
  promptForAuth,
  resolveViewerProfile,
  ensureVerifiedVillager,
  showGuestBrowsePromptOnce,
};
