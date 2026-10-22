const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const {
  getToken,
  setToken,
  getUserProfile,
  setUserProfile,
  clearSession,
  revokeServerSession,
} = require("../../utils/auth");
const {
  formatPhoneDisplay,
} = require("../../utils/phone");

const REALNAME_STATUS_TEXT = {
  unsubmitted: "未登记",
  pending: "待确认",
  verified: "已完成",
  rejected: "未通过",
};

const AUTH_STATUS_TEXT = {
  unverified: "未完成",
  partial: "进行中",
  verified: "已完成",
};

const ROSTER_MATCH_STATUS_TEXT = {
  unmatched: "待按姓名身份证核验",
  matched: "已命中名单",
  not_configured: "名单未配置",
};

const REQUIRED_CONSENTS = ["privacy_policy", "sensitive_identity"];

Page({
  data: {
    currentStep: 1,
    isLoggedIn: false,
    profile: null,
    boundPhoneText: "",
    realNameInput: "",
    idCardInput: "",
    realnameStatusText: "未登记",
    authStatusText: "未完成",
    canEnterResident: false,
    policyVersion: "",
    policyTitle: "隐私政策",
    policyContent: "",
    consentMap: {},
    consentPrivacyText: "未同意",
    consentIdentityText: "未同意",
    consentSummaryText: "未同意",
    rosterMatchStatusText: "未匹配",
    displayName: "",
    villageGroupText: "",
    showVillageGroup: false,
    step1Done: false,
    step2Done: false,
    step3Done: false,
  },
  hasConsent(consentType) {
    const consentMap = this.data.consentMap || {};
    return consentMap[consentType] === "agreed";
  },
  refreshStepFlags(profile) {
    const currentProfile = profile || this.data.profile || {};
    const step1Done =
      !!this.data.isLoggedIn &&
      REQUIRED_CONSENTS.every((consentType) => this.hasConsent(consentType));
    const step2Done = !!currentProfile.phone_bound && !!currentProfile.phone_verified_at;
    const step3Done = (currentProfile.auth_status || "unverified") === "verified";
    this.setData({
      step1Done,
      step2Done,
      step3Done,
    });
  },
  autoStepByProgress() {
    if (!this.data.isLoggedIn) {
      this.setData({ currentStep: 1 });
      return;
    }
    if (!this.data.step1Done) {
      this.setData({ currentStep: 1 });
      return;
    }
    const profile = this.data.profile || {};
    if (!profile.phone_bound || !profile.phone_verified_at) {
      this.setData({ currentStep: 2 });
      return;
    }
    this.setData({ currentStep: 3 });
  },
  applyConsents(items) {
    const map = {};
    (items || []).forEach((item) => {
      if (!item || !item.consent_type) {
        return;
      }
      map[item.consent_type] = item.status;
    });
    this.setData(
      {
        consentMap: map,
        consentPrivacyText: map.privacy_policy === "agreed" ? "已同意" : "未同意",
        consentIdentityText: map.sensitive_identity === "agreed" ? "已同意" : "未同意",
        consentSummaryText:
          map.privacy_policy === "agreed" &&
          map.sensitive_identity === "agreed"
            ? "已同意"
            : "未同意",
      },
      () => {
      this.refreshStepFlags();
      this.autoStepByProgress();
      }
    );
  },
  updateFromProfile(profile) {
    if (!profile) {
      return;
    }
    setUserProfile(profile);
    const canEnterResident =
      profile.auth_status === "verified";
    const displayName = profile.real_name || profile.nickname || "微信用户";
    const villageGroupText = String(profile.village_group || "").trim();
    this.setData(
      {
        isLoggedIn: true,
        profile,
        boundPhoneText: formatPhoneDisplay(profile.phone || ""),
        displayName,
        villageGroupText,
        showVillageGroup: !!villageGroupText,
        realNameInput: profile.real_name || "",
        idCardInput: "",
        realnameStatusText: REALNAME_STATUS_TEXT[profile.realname_status] || "未登记",
        authStatusText: AUTH_STATUS_TEXT[profile.auth_status] || "未完成",
        canEnterResident,
        rosterMatchStatusText:
          ROSTER_MATCH_STATUS_TEXT[profile.roster_match_status] || "未匹配",
      },
      () => {
        this.refreshStepFlags(profile);
        this.autoStepByProgress();
      }
    );
  },
  resetResidentSession() {
    clearSession();
    this.setData(
      {
        currentStep: 1,
        isLoggedIn: false,
        profile: null,
        boundPhoneText: "",
        realNameInput: "",
        idCardInput: "",
        realnameStatusText: "未登记",
        authStatusText: "未完成",
        canEnterResident: false,
        consentMap: {},
        consentPrivacyText: "未同意",
        consentIdentityText: "未同意",
        consentSummaryText: "未同意",
        rosterMatchStatusText: "未匹配",
        displayName: "",
        villageGroupText: "",
        showVillageGroup: false,
        step1Done: false,
        step2Done: false,
        step3Done: false,
      },
      () => {
        this.refreshStepFlags();
      }
    );
  },
  async refreshProfile() {
    const token = getToken();
    if (!token) {
      this.resetResidentSession();
      return;
    }
    try {
      const profile = await request({ path: "/auth/me" });
      this.updateFromProfile(profile);
    } catch (err) {
      const detail = String(err?.detail || err?.message || "").trim();
      if (detail === "invalid_token" || detail === "token_expired") {
        this.resetResidentSession();
      }
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    }
  },
  async loadPolicyAndConsents() {
    try {
      const policy = await request({ path: "/privacy/policy" });
      this.setData({
        policyVersion: policy.version,
        policyTitle: policy.title,
        policyContent: policy.content,
      });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
      return;
    }
    if (!this.data.isLoggedIn) {
      return;
    }
    try {
      const consents = await request({ path: "/privacy/consents" });
      this.applyConsents(consents.items || []);
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    }
  },
  onShow() {
    const token = getToken();
    const cached = getUserProfile();
    if (token && cached) {
      this.updateFromProfile(cached);
      this.loadPolicyAndConsents();
      this.refreshProfile();
      return;
    }
    if (token) {
      this.refreshProfile().then(() => {
        this.loadPolicyAndConsents();
      });
      return;
    }
    this.resetResidentSession();
    this.loadPolicyAndConsents();
  },
  showPolicyDialog() {
    const content = this.data.policyContent || "请先获取隐私政策内容。";
    wx.showModal({
      title: this.data.policyTitle || "隐私政策",
      content,
      showCancel: false,
      confirmText: "我已知晓",
    });
  },
  async wechatLogin() {
    wx.login({
      success: async (res) => {
        if (!res.code) {
          wx.showToast({ title: "微信登录失败", icon: "none" });
          return;
        }
        try {
          const result = await request({
            path: "/auth/wechat-login",
            method: "POST",
            data: { code: res.code },
          });
          setToken(result.token);
          this.updateFromProfile(result.user);
          await this.loadPolicyAndConsents();
          wx.showToast({ title: "登录成功", icon: "success" });
        } catch (err) {
          wx.showToast({ title: getErrorMessage(err), icon: "none" });
        }
      },
      fail: () => {
        wx.showToast({ title: "无法调用微信登录", icon: "none" });
      },
    });
  },
  async agreeAllConsents() {
    if (!this.data.isLoggedIn) {
      wx.showToast({ title: "请先微信登录", icon: "none" });
      return;
    }
    if (!this.data.policyVersion) {
      wx.showToast({ title: "隐私政策加载失败", icon: "none" });
      return;
    }
    const missing = REQUIRED_CONSENTS.filter((consentType) => !this.hasConsent(consentType));
    if (!missing.length) {
      wx.showToast({ title: "已完成授权", icon: "success" });
      this.refreshStepFlags();
      this.autoStepByProgress();
      return;
    }
    try {
      const data = await request({
        path: "/privacy/consent",
        method: "POST",
        data: {
          policy_version: this.data.policyVersion,
          consent_types: missing,
        },
      });
      this.applyConsents(data.items || []);
      wx.showToast({ title: "授权成功", icon: "success" });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    }
  },
  goStep(e) {
    const step = Number(e.currentTarget.dataset.step || 1);
    if (Number.isNaN(step) || step < 1 || step > 3) {
      return;
    }
    if (step === 2 && !this.data.step1Done) {
      wx.showToast({ title: "请先完成微信登录和授权", icon: "none" });
      return;
    }
    if (step === 3 && !this.data.step2Done) {
      wx.showToast({ title: "请先绑定手机号", icon: "none" });
      return;
    }
    this.setData({ currentStep: step });
  },
  async bindPhoneByWechat(e) {
    if (!this.data.step1Done) {
      wx.showToast({ title: "请先完成第一步", icon: "none" });
      return;
    }
    const detail = e && e.detail ? e.detail : {};
    const phoneCode = String(detail.code || "").trim();
    if (!phoneCode) {
      const errMsg = String(detail.errMsg || "").trim();
      if (/cancel/i.test(errMsg)) {
        wx.showToast({ title: "您已取消手机号授权", icon: "none" });
        return;
      }
      wx.showToast({ title: "未获取到手机号授权码", icon: "none" });
      return;
    }
    wx.showLoading({ title: "绑定中", mask: true });
    try {
      const profile = await request({
        path: "/auth/bind-phone",
        method: "POST",
        data: { phone_code: phoneCode },
        timeout: 60000,
      });
      let latestProfile = profile;
      try {
        latestProfile = await request({
          path: "/auth/me",
          timeout: 30000,
          skipCadreRedirect: true,
        });
      } catch (refreshErr) {
        latestProfile = profile;
      }
      const nextProfile = {
        ...(this.data.profile || {}),
        ...(latestProfile || profile || {}),
        phone_bound: true,
        phone_verified_at:
          String((latestProfile || profile || {}).phone_verified_at || "").trim() || new Date().toISOString(),
      };
      this.updateFromProfile(nextProfile);
      this.setData({
        step2Done: true,
        currentStep: 3,
      });
      wx.showToast({ title: "手机号已完成微信验证", icon: "success" });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    } finally {
      wx.hideLoading();
    }
  },
  onRealNameInput(e) {
    this.setData({ realNameInput: e.detail.value });
  },
  onIdCardInput(e) {
    this.setData({ idCardInput: e.detail.value });
  },
  async submitRealname() {
    if (!this.data.step2Done) {
      wx.showToast({ title: "请先完成手机号绑定", icon: "none" });
      return;
    }
    if (!this.data.realNameInput || !this.data.idCardInput) {
      wx.showToast({ title: "请填写姓名和身份证号", icon: "none" });
      return;
    }
    try {
      const profile = await request({
        path: "/auth/realname-submit",
        method: "POST",
        data: {
          real_name: this.data.realNameInput,
          id_card_number: this.data.idCardInput,
        },
      });
      this.updateFromProfile(profile);
      this.setData({ idCardInput: "" });
      if (profile.auth_status === "verified") {
        wx.showToast({
          title: "基础实名登记已完成",
          icon: "success",
        });
        setTimeout(() => {
          this.enterResident();
        }, 350);
        return;
      }
      wx.showToast({
        title: "身份信息已提交",
        icon: "success",
      });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    }
  },
  enterResident() {
    if (!this.data.canEnterResident) {
      wx.showToast({ title: "请先完成基础实名登记", icon: "none" });
      return;
    }
    wx.switchTab({ url: "/pages/home/home" });
  },
  async logout() {
    try {
      await revokeServerSession();
    } catch (err) {
      // Server-side logout failure should not block local logout.
    }
    this.resetResidentSession();
    wx.showToast({ title: "已退出", icon: "success" });
  },
  async withdrawAllConsents() {
    if (!this.data.isLoggedIn) {
      wx.showToast({ title: "当前未登录", icon: "none" });
      return;
    }
    wx.showModal({
      title: "撤回授权",
      content: "撤回后将清空基础实名登记信息，并退出登录。是否继续？",
      success: async (res) => {
        if (!res.confirm) {
          return;
        }
        try {
          await request({
            path: "/privacy/withdraw",
            method: "POST",
            data: { reason: "用户主动撤回" },
          });
          this.resetResidentSession();
          wx.showToast({ title: "已撤回并退出", icon: "success" });
        } catch (err) {
          wx.showToast({ title: getErrorMessage(err), icon: "none" });
        }
      },
    });
  },
});
