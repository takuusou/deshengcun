const { request } = require("../../../utils/request");
const {
  getToken,
  getUserProfile,
  setToken,
  setUserProfile,
} = require("../../../utils/auth");
const { resolveViewerProfile } = require("../../../utils/access");
const { getErrorMessage } = require("../../../utils/messages");
const { compactPhone, dialPhoneNumber, formatPhoneInput, isValidMobilePhone } = require("../../../utils/phone");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../../utils/share");

function modalConfirm(options) {
  return new Promise((resolve) => {
    wx.showModal({
      title: options.title,
      content: options.content,
      confirmText: options.confirmText || "确定",
      cancelText: options.cancelText || "取消",
      success(res) {
        resolve(!!res.confirm);
      },
      fail() {
        resolve(false);
      },
    });
  });
}

function wxLoginCode() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(res) {
        if (res.code) {
          resolve(res.code);
          return;
        }
        reject(new Error("invalid_wechat_code"));
      },
      fail(err) {
        reject(err);
      },
    });
  });
}

function buildActivity(item) {
  const scheduleText = String(item?.schedule_text || "").trim();
  const location = String(item?.location || "").trim();
  const target = String(item?.target || "").trim();
  const deadline = String(item?.signup_deadline || "").trim();
  return {
    ...item,
    id: Number(item?.id || 0),
    title: String(item?.title || "").trim(),
    schedule_text: scheduleText,
    location,
    target,
    signup_deadline: deadline,
    contact_phone: String(item?.contact_phone || "").trim(),
    metaRows: [
      { label: "时间", value: scheduleText || "待村委会通知" },
      { label: "地点", value: location || "待村委会通知" },
      { label: "对象", value: target || "热心村民均可 · 自愿参与" },
      { label: "截止", value: deadline || "以村委通知为准" },
    ],
  };
}

Page({
  data: {
    loading: false,
    activities: [],
    openActivities: [],
    pastActivities: [],
    pastDisplay: [],
    showAllPast: false,
    showSignup: false,
    selectedActivity: null,
    formName: "",
    formPhone: "",
    submitting: false,
  },

  onLoad() {
    showDefaultShareMenu();
    this.loadActivities();
  },

  onPullDownRefresh() {
    this.loadActivities().finally(() => wx.stopPullDownRefresh());
  },

  async loadActivities() {
    this.setData({ loading: true });
    try {
      const rows = await request({ path: "/volunteer-activities" });
      const activities = (rows || []).map((item) => buildActivity(item));
      const openActivities = activities.filter((item) => item.is_open);
      const pastActivities = activities.filter((item) => !item.is_open);
      this.setData(
        {
          activities,
          openActivities,
          pastActivities,
        },
        () => this.refreshPastDisplay()
      );
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
      this.setData({
        activities: [],
        openActivities: [],
        pastActivities: [],
        pastDisplay: [],
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  noop() {},

  refreshPastDisplay() {
    const pastActivities = this.data.pastActivities || [];
    this.setData({
      pastDisplay: this.data.showAllPast ? pastActivities : pastActivities.slice(0, 3),
    });
  },

  togglePast() {
    this.setData({ showAllPast: !this.data.showAllPast }, () => this.refreshPastDisplay());
  },

  async ensureWechatLoginOnly() {
    const token = getToken();
    if (token) {
      const profile = await resolveViewerProfile({ refresh: true, silent: true });
      if (profile) {
        return profile;
      }
    }
    const confirmed = await modalConfirm({
      title: "报名需微信登录",
      content: "报名只用于关联您的微信账号和联系电话，不需要填写身份证，也不做人脸核验。",
      confirmText: "微信登录",
      cancelText: "先看看",
    });
    if (!confirmed) {
      return null;
    }
    try {
      wx.showLoading({ title: "登录中", mask: true });
      const code = await wxLoginCode();
      const result = await request({
        path: "/auth/wechat-login",
        method: "POST",
        data: { code },
      });
      setToken(result.token || "");
      setUserProfile(result.user || null);
      return result.user || getUserProfile();
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
      return null;
    } finally {
      wx.hideLoading();
    }
  },

  async openSignup(e) {
    const activityId = Number(e.currentTarget.dataset.id || 0);
    const activity = (this.data.activities || []).find((item) => item.id === activityId);
    if (!activity) {
      return;
    }
    if (!activity.is_open) {
      wx.showToast({ title: "该活动已停止报名", icon: "none" });
      return;
    }
    if (activity.signed_up) {
      wx.showToast({ title: "您已报名该活动", icon: "none" });
      return;
    }
    const profile = await this.ensureWechatLoginOnly();
    if (!profile) {
      return;
    }
    this.setData({
      selectedActivity: activity,
      showSignup: true,
      formName: profile.real_name || profile.nickname || "",
      formPhone: "",
    });
  },

  closeSignup() {
    if (this.data.submitting) {
      return;
    }
    this.setData({
      showSignup: false,
      selectedActivity: null,
      formName: "",
      formPhone: "",
    });
  },

  onNameInput(e) {
    this.setData({ formName: String(e.detail.value || "").slice(0, 50) });
  },

  onPhoneInput(e) {
    this.setData({ formPhone: formatPhoneInput(e.detail.value) });
  },

  async submitSignup() {
    const activity = this.data.selectedActivity;
    if (!activity?.id || this.data.submitting) {
      return;
    }
    const name = String(this.data.formName || "").trim();
    const phone = compactPhone(this.data.formPhone);
    if (!name) {
      wx.showToast({ title: "请填写姓名", icon: "none" });
      return;
    }
    if (!isValidMobilePhone(phone)) {
      wx.showToast({ title: "请输入11位手机号", icon: "none" });
      return;
    }
    this.setData({ submitting: true });
    try {
      await request({
        path: `/volunteer-activities/${activity.id}/signup`,
        method: "POST",
        data: { name, phone },
      });
      wx.showToast({ title: "报名成功", icon: "success" });
      this.setData({
        showSignup: false,
        selectedActivity: null,
        formName: "",
        formPhone: "",
      });
      this.loadActivities();
    } catch (err) {
      const detail = String(err?.detail || "").trim();
      wx.showToast({
        title: detail === "signup_conflict" ? "您已报名该活动" : getErrorMessage(err),
        icon: "none",
      });
    } finally {
      this.setData({ submitting: false });
    }
  },

  callContact(e) {
    const activityId = Number(e.currentTarget.dataset.id || 0);
    const activity = (this.data.activities || []).find((item) => item.id === activityId);
    const phoneNumber = String(activity?.contact_phone || "").trim();
    if (!phoneNumber) {
      wx.showToast({ title: "村委暂未填写联系电话", icon: "none" });
      return;
    }
    dialPhoneNumber(phoneNumber, { emptyToastTitle: "村委暂未填写联系电话" });
  },

  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜服务通 - 志愿服务", path: "/pages/services/volunteer/volunteer" });
  },

  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通 - 志愿服务" });
  },
});
