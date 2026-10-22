const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const { clearSession, revokeServerSession } = require("../../utils/auth");
const { openAuthCenter, resolveViewerProfile } = require("../../utils/access");

Page({
  data: {
    profile: null,
    roleLabel: "游客浏览",
    isLoggedIn: false,
    authBadgeText: "",
    isAuthVerified: false,
    isAuthPartial: false,
    applyCount: 0,
  },
  applyGuestState() {
    this.setData({
      profile: null,
      roleLabel: "游客浏览",
      isLoggedIn: false,
      authBadgeText: "",
      isAuthVerified: false,
      isAuthPartial: false,
      applyCount: 0,
    });
  },
  async refreshProfile() {
    const profile = await resolveViewerProfile({ refresh: true, silent: true });
    if (!profile) {
      this.applyGuestState();
      return null;
    }
    const authStatus = String(profile.auth_status || "").trim().toLowerCase();
    this.setData({
      profile,
      roleLabel: "村民账号",
      isLoggedIn: true,
      authBadgeText: authStatus === "verified" ? "已认证成功" : authStatus === "partial" ? "认证中" : "待认证",
      isAuthVerified: authStatus === "verified",
      isAuthPartial: authStatus === "partial",
    });
    return profile;
  },
  async refreshCounts() {
    if (!this.data.isLoggedIn) {
      this.setData({
        applyCount: 0,
      });
      return;
    }
    try {
      const [govRows, requestRows] = await Promise.all([
        request({ path: "/gov/applications" }),
        request({ path: "/requests" }),
      ]);
      const allRows = [].concat(govRows || []).concat(requestRows || []);
      this.setData({
        applyCount: allRows.length,
      });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    }
  },
  async onShow() {
    await this.refreshProfile();
    await this.refreshCounts();
  },
  goAuthCenter() {
    openAuthCenter();
  },
  openApplications() {
    wx.navigateTo({ url: "/pages/volunteers/volunteers" });
  },
  openHelp() {
    wx.navigateTo({ url: "/pages/help/help" });
  },
  openPrivacy() {
    wx.navigateTo({ url: "/pages/privacy/privacy" });
  },
  async logout() {
    try {
      await revokeServerSession();
    } catch (err) {
      // Ignore server-side logout failure and still clear local session.
    }
    clearSession();
    this.applyGuestState();
    wx.showToast({ title: "已退出登录", icon: "success" });
  },
});
