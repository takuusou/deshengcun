const { request } = require("../../../utils/request");
const { getToken } = require("../../../utils/auth");
const { ensureVerifiedVillager } = require("../../../utils/access");
const { getErrorMessage } = require("../../../utils/messages");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../../utils/share");

const MAX_LEN = 500;

Page({
  data: {
    content: "",
    count: 0,
    maxLen: MAX_LEN,
    submitting: false,
    submitted: false,
    alreadyToday: false,
  },

  onLoad() {
    showDefaultShareMenu();
  },

  onShow() {
    this.refreshTodayStatus();
  },

  async refreshTodayStatus() {
    // 已在本次会话提交成功的，保持成功态，不覆盖
    if (this.data.submitted) {
      return;
    }
    if (!getToken()) {
      this.setData({ alreadyToday: false });
      return;
    }
    try {
      const res = await request({ path: "/proposal/status" });
      this.setData({ alreadyToday: !!(res && res.submitted_today) });
    } catch (err) {
      // 查询失败不打扰用户，按可写态处理；提交时后端仍会强制拦截
      this.setData({ alreadyToday: false });
    }
  },

  onContentInput(e) {
    const value = String(e.detail.value || "").slice(0, MAX_LEN);
    this.setData({ content: value, count: value.length });
  },

  async submitProposal() {
    if (this.data.submitting) {
      return;
    }
    const content = String(this.data.content || "").trim();
    if (!content) {
      wx.showToast({ title: "请先写下您的建议", icon: "none" });
      return;
    }
    const verified = await ensureVerifiedVillager();
    if (!verified) {
      return;
    }
    this.setData({ submitting: true });
    try {
      await request({
        path: "/proposal",
        method: "POST",
        data: { content },
      });
      this.setData({ submitted: true, alreadyToday: false, content: "", count: 0 });
    } catch (err) {
      const detail = String(err?.detail || "").trim();
      if (detail === "proposal_daily_limit") {
        this.setData({ alreadyToday: true, content: "", count: 0 });
        wx.showToast({ title: "今天您已提交过了", icon: "none" });
      } else {
        wx.showToast({ title: getErrorMessage(err), icon: "none" });
      }
    } finally {
      this.setData({ submitting: false });
    }
  },

  goBack() {
    const pages = getCurrentPages();
    if (pages.length > 1) {
      wx.navigateBack({ delta: 1 });
      return;
    }
    wx.switchTab({ url: "/pages/service/service" });
  },

  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜服务通 - 建议", path: "/pages/services/proposal/proposal" });
  },

  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通 - 建议" });
  },
});
