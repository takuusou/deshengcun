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

function buildProgram(item) {
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
      { label: "对象", value: target || "有就业培训需求的村民" },
      { label: "截止", value: deadline || "以村委通知为准" },
    ],
  };
}

Page({
  data: {
    loading: false,
    programs: [],
    openPrograms: [],
    pastPrograms: [],
    pastDisplay: [],
    showAllPast: false,
    showSignup: false,
    selectedProgram: null,
    formName: "",
    formPhone: "",
    submitting: false,
  },

  onLoad() {
    showDefaultShareMenu();
    this.loadPrograms();
  },

  onPullDownRefresh() {
    this.loadPrograms().finally(() => wx.stopPullDownRefresh());
  },

  async loadPrograms() {
    this.setData({ loading: true });
    try {
      const rows = await request({ path: "/training-programs" });
      const programs = (rows || []).map((item) => buildProgram(item));
      const openPrograms = programs.filter((item) => item.is_open);
      const pastPrograms = programs.filter((item) => !item.is_open);
      this.setData(
        {
          programs,
          openPrograms,
          pastPrograms,
        },
        () => this.refreshPastDisplay()
      );
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
      this.setData({
        programs: [],
        openPrograms: [],
        pastPrograms: [],
        pastDisplay: [],
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  noop() {},

  refreshPastDisplay() {
    const pastPrograms = this.data.pastPrograms || [];
    this.setData({
      pastDisplay: this.data.showAllPast ? pastPrograms : pastPrograms.slice(0, 3),
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
    const programId = Number(e.currentTarget.dataset.id || 0);
    const program = (this.data.programs || []).find((item) => item.id === programId);
    if (!program) {
      return;
    }
    if (!program.is_open) {
      wx.showToast({ title: "该培训已停止报名", icon: "none" });
      return;
    }
    if (program.signed_up) {
      wx.showToast({ title: "您已报名该培训", icon: "none" });
      return;
    }
    const profile = await this.ensureWechatLoginOnly();
    if (!profile) {
      return;
    }
    this.setData({
      selectedProgram: program,
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
      selectedProgram: null,
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
    const program = this.data.selectedProgram;
    if (!program?.id || this.data.submitting) {
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
        path: `/training-programs/${program.id}/signup`,
        method: "POST",
        data: { name, phone },
      });
      wx.showToast({ title: "报名成功", icon: "success" });
      this.setData({
        showSignup: false,
        selectedProgram: null,
        formName: "",
        formPhone: "",
      });
      this.loadPrograms();
    } catch (err) {
      const detail = String(err?.detail || "").trim();
      wx.showToast({
        title: detail === "signup_conflict" ? "您已报名该培训" : getErrorMessage(err),
        icon: "none",
      });
    } finally {
      this.setData({ submitting: false });
    }
  },

  callContact(e) {
    const programId = Number(e.currentTarget.dataset.id || 0);
    const program = (this.data.programs || []).find((item) => item.id === programId);
    const phoneNumber = String(program?.contact_phone || "").trim();
    if (!phoneNumber) {
      wx.showToast({ title: "村委暂未填写联系电话", icon: "none" });
      return;
    }
    dialPhoneNumber(phoneNumber, { emptyToastTitle: "村委暂未填写联系电话" });
  },

  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜服务通 - 就业培训", path: "/pages/services/training/training" });
  },

  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通 - 就业培训" });
  },
});
