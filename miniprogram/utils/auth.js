const { request } = require("./request");

const TOKEN_KEY = "token";

function getGlobalData() {
  const app = typeof getApp === "function" ? getApp() : null;
  if (!app) {
    return null;
  }
  if (!app.globalData) {
    app.globalData = {};
  }
  return app.globalData;
}

function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || "";
}

function setToken(token) {
  wx.setStorageSync(TOKEN_KEY, token || "");
}

function clearToken() {
  wx.removeStorageSync(TOKEN_KEY);
}

function getUserProfile() {
  return getGlobalData()?.userProfile || null;
}

function setUserProfile(user) {
  const globalData = getGlobalData();
  if (globalData) {
    globalData.userProfile = user || null;
  }
}

function clearUserProfile() {
  const globalData = getGlobalData();
  if (globalData) {
    globalData.userProfile = null;
  }
}

function clearSession() {
  clearToken();
  clearUserProfile();
}

async function revokeServerSession() {
  const token = getToken();
  if (!token) {
    return;
  }
  await request({
    path: "/auth/logout",
    method: "POST",
    token,
    skipCadreRedirect: true,
    skipAuthRecovery: true,
  });
}

module.exports = {
  getToken,
  setToken,
  clearToken,
  getUserProfile,
  setUserProfile,
  clearUserProfile,
  clearSession,
  revokeServerSession,
};
