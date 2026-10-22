const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const { openAuthCenter, resolveViewerProfile } = require("../../utils/access");
const { formatLocalDateTime } = require("../../utils/date");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");
const { normalizePhotoUrl } = require("../../utils/photo-url");
const { dialPhoneNumber } = require("../../utils/phone");

const HOME_SHARE_TITLE = "得胜服务通";
const HOME_SHARE_PATH = "/pages/home/home";
const MONTH_SHORT_TEXT = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

function buildNoticeDateParts(value) {
  const source = value ? new Date(value) : null;
  if (!source || Number.isNaN(source.getTime())) {
    return {
      dayText: "--",
      monthText: "NOW",
    };
  }
  return {
    dayText: String(source.getDate()).padStart(2, "0"),
    monthText: MONTH_SHORT_TEXT[source.getMonth()] || "NOW",
  };
}

Page({
  data: {
    profile: null,
    heroSlides: [],
    heroCurrent: 0,
    noticeItems: [],
    miniProgramLinks: [
      {
        key: "tax_social_security",
        title: "湘税社保",
        subtitle: "医保社保服务",
        theme: "red",
        logoSrc: "/assets/external-links/xiang-tax-social.png",
        iconSrc: "/assets/icons/card-red.svg",
        logoScale: 1.08,
        logoOffsetY: -1,
        shortLink: "#小程序://湘税社保/xT3ZxNEV4bwUDJd",
        searchKeyword: "湘税社保",
      },
      {
        key: "human_resources",
        title: "智慧人社",
        subtitle: "人社待遇服务",
        theme: "blue",
        logoSrc: "/assets/external-links/hunan-smart-hr.jpg",
        iconSrc: "/assets/icons/person-blue.svg",
        logoScale: 0.94,
        logoOffsetY: 0,
        shortLink: "#小程序://湖南智慧人社/rNHSOo7WamI2q3f",
        searchKeyword: "湖南智慧人社",
      },
      {
        key: "rural_land_contract",
        title: "土地承包",
        subtitle: "土地承包服务",
        theme: "green",
        logoSrc: "/assets/external-links/rural-land-contract.png",
        iconSrc: "/assets/icons/layers-green.svg",
        logoScale: 0.94,
        logoOffsetY: 0,
        appId: "wx0000000000000000",
        searchKeyword: "农村土地承包合同网签",
      },
      {
        key: "xiang_easy",
        title: "湘易办",
        subtitle: "政务服务",
        theme: "blue",
        logoSrc: "",
        iconSrc: "/assets/icons/grid-green.svg",
        shortLink: "#小程序://湘易办/767kvgJgBDgySyg",
        searchKeyword: "湘易办",
        manualSearchOnly: false,
      },
      {
        key: "reward_assistance_annual_review",
        title: "奖扶年审",
        subtitle: "奖扶年审服务",
        theme: "red",
        logoSrc: "",
        iconSrc: "/assets/icons/calendar-check-red.svg",
        appId: "wx0000000000000000",
        searchKeyword: "奖扶年审小助手",
      },
    ],
    phoneCurrent: 0,
    phoneItems: [
      { tag: "", tagLabel: "村委会服务电话", num: "<CONFIGURE_CONTACT_PHONE>" },
      { tag: "报警", tagLabel: "公安报警", num: "110" },
      { tag: "急救", tagLabel: "医疗急救", num: "120" },
      { tag: "火警", tagLabel: "火警电话", num: "119" },
    ],
    noticeSubscribeAvailable: false,
    noticeSubscribeEnabled: false,
    noticeSubscribeStatus: "unknown",
    noticeSubscribeTemplateId: "",
    noticeSubscribeButtonText: "登录后开启通知",
    noticeSubscribeHint: "登录后可开启微信服务通知提醒。",
    noticeSubscribeLoading: false,
    noticeSubscribePromptTitle: "开启村务通知提醒",
    noticeSubscribePromptContent: "开启后，村委发布通知、政策通知和重要公告时，微信会通过服务通知提醒您。",
  },
  async refreshProfile() {
    const profile = await resolveViewerProfile({ refresh: true, silent: true });
    this.setData({
      profile,
    });
    return true;
  },
  onLoad() {
    showDefaultShareMenu();
  },
  resetNoticeSubscribeState() {
    const hasProfile = !!this.data.profile;
    this.setData({
      noticeSubscribeAvailable: false,
      noticeSubscribeEnabled: false,
      noticeSubscribeStatus: "unknown",
      noticeSubscribeTemplateId: "",
      noticeSubscribeButtonText: hasProfile ? "订阅服务消息" : "登录后开启通知",
      noticeSubscribeHint: hasProfile
        ? "开启后，村委发布通知、政策通知和重要公告时，微信会通过服务通知提醒您。"
        : "登录后可开启微信服务通知提醒。",
      noticeSubscribeLoading: false,
      noticeSubscribePromptTitle: "开启村务通知提醒",
      noticeSubscribePromptContent: "开启后，村委发布通知、政策通知和重要公告时，微信会通过服务通知提醒您。",
    });
  },
  buildNoticeSubscribeHint(status) {
    if (!this.data.profile) {
      return "登录后可开启微信服务通知提醒。";
    }
    if (!status?.available) {
      return "村委通知服务暂未开启，请稍后再试。";
    }
    if (status?.is_enabled) {
      return "已开启，村委发布通知、政策通知和重要公告会通过微信服务通知提醒您。";
    }
    if (status?.current_status === "reject" || status?.current_status === "delivery_rejected") {
      return "您当前未开启服务通知，可重新点击开启。";
    }
    return String(status?.prompt_content || "开启后，村委发布通知会通过微信服务通知提醒您。").trim();
  },
  async loadNoticeSubscribeStatus() {
    if (!this.data.profile) {
      this.resetNoticeSubscribeState();
      return null;
    }
    this.setData({ noticeSubscribeLoading: true });
    try {
      const status = await request({ path: "/notice-subscriptions/status" });
      this.setData({
        noticeSubscribeAvailable: !!status?.available,
        noticeSubscribeEnabled: !!status?.is_enabled,
        noticeSubscribeStatus: String(status?.current_status || "unknown"),
        noticeSubscribeTemplateId: String(status?.template_id || ""),
        noticeSubscribeButtonText: String(status?.button_text || "订阅服务消息"),
        noticeSubscribeHint: this.buildNoticeSubscribeHint(status),
        noticeSubscribePromptTitle: String(status?.prompt_title || "开启村务通知提醒"),
        noticeSubscribePromptContent: String(
          status?.prompt_content || "开启后，村委发布通知会通过微信服务通知提醒您。"
        ),
      });
      return status;
    } catch (err) {
      this.resetNoticeSubscribeState();
      return null;
    } finally {
      this.setData({ noticeSubscribeLoading: false });
    }
  },
  async requestNoticeSubscription(scene = "manual") {
    if (this.data.noticeSubscribeLoading) {
      return;
    }
    if (!this.data.profile) {
      wx.showModal({
        title: "请先登录",
        content: "开启服务通知前，请先完成微信登录。",
        confirmText: "去登录",
        cancelText: "先看看",
        success(res) {
          if (res.confirm) {
            openAuthCenter();
          }
        },
      });
      return;
    }
    if (!this.data.noticeSubscribeAvailable || !this.data.noticeSubscribeTemplateId) {
      wx.showToast({ title: "村委正在配置通知模板", icon: "none" });
      return;
    }
    if (this.data.noticeSubscribeEnabled) {
      wx.showToast({ title: "您已开启通知提醒", icon: "none" });
      return;
    }
    if (typeof wx.requestSubscribeMessage !== "function") {
      wx.showToast({ title: "当前微信版本不支持", icon: "none" });
      return;
    }

    const templateId = String(this.data.noticeSubscribeTemplateId || "").trim();
    this.setData({ noticeSubscribeLoading: true });
    try {
      const subscribeResult = await new Promise((resolve, reject) => {
        wx.requestSubscribeMessage({
          tmplIds: [templateId],
          success: resolve,
          fail: reject,
        });
      });
      const backendStatus = await request({
        path: "/notice-subscriptions/record",
        method: "POST",
        data: {
          scene,
          template_statuses: {
            [templateId]: String(subscribeResult?.[templateId] || ""),
          },
          err_msg: String(subscribeResult?.errMsg || ""),
        },
      });
      this.setData({
        noticeSubscribeAvailable: !!backendStatus?.available,
        noticeSubscribeEnabled: !!backendStatus?.is_enabled,
        noticeSubscribeStatus: String(backendStatus?.current_status || "unknown"),
        noticeSubscribeButtonText: String(backendStatus?.button_text || "订阅服务消息"),
        noticeSubscribeHint: this.buildNoticeSubscribeHint(backendStatus),
      });
      if (String(subscribeResult?.[templateId] || "") === "accept") {
        wx.showToast({ title: "已开启通知提醒", icon: "success" });
        return;
      }
      wx.showToast({ title: "您这次没有开启通知", icon: "none" });
    } catch (err) {
      const errCode = Number(err?.errCode || 0);
      if (errCode === 20004 && typeof wx.openAppAuthorizeSetting === "function") {
        wx.showModal({
          title: "通知开关已关闭",
          content: "您已关闭微信服务通知主开关，是否前往微信设置重新开启？",
          confirmText: "去设置",
          cancelText: "暂不",
          success(res) {
            if (res.confirm) {
              wx.openAppAuthorizeSetting({});
            }
          },
        });
      } else {
        wx.showToast({ title: getErrorMessage(err), icon: "none" });
      }
      await this.loadNoticeSubscribeStatus();
    } finally {
      this.setData({ noticeSubscribeLoading: false });
    }
  },
  buildHomeData(notices) {
    const noticeRows = (notices || [])
      .slice(0, 3)
      .map((item) => {
        return {
          id: item.id,
          title: item.title || "村务通知",
          timeText: formatLocalDateTime(item.created_at),
        };
      });

    const heroSlides = (notices || [])
      .filter((item) => !!item?.is_home_top)
      .slice(0, 6)
      .map((item) => ({
        id: `notice_${item.id}`,
        noticeId: item.id,
        url: normalizePhotoUrl(item?.photo_urls?.[0]),
        title: item.title || "重要通知",
        subtitle: item.publisher
          ? `${item.publisher} · ${formatLocalDateTime(item.created_at)}`
          : formatLocalDateTime(item.created_at),
      }));
    if (!heroSlides.length) {
      heroSlides.push(
        { id: "fallback_1", noticeId: 0, url: "", title: "得胜服务通", subtitle: "发布重要通知后，这里会展示首页置顶内容" },
        { id: "fallback_2", noticeId: 0, url: "", title: "政策通知与村务公开", subtitle: "支持最多 6 条重要通知轮播展示" },
        { id: "fallback_3", noticeId: 0, url: "", title: "政务办理与村民自治", subtitle: "重要村务内容会同步到首页展示" }
      );
    }

    this.setData({
      noticeItems: noticeRows,
      heroSlides,
      heroCurrent: 0,
    });
  },
  async loadHomeData() {
    try {
      const notices = await request({ path: "/notices" });
      this.buildHomeData(notices);
    } catch (err) {
      this.buildHomeData([]);
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    }
  },
  findMiniProgramLink(key) {
    return (this.data.miniProgramLinks || []).find((item) => item.key === key) || null;
  },
  showManualSearchTip(item) {
    const keyword = String(item?.searchKeyword || item?.title || "").trim();
    if (!keyword) {
      wx.showToast({ title: "暂未配置搜索词", icon: "none" });
      return;
    }
    wx.setClipboardData({
      data: keyword,
      success: () => {
        wx.showModal({
          title: item.title || "常用小程序",
          content: `这个小程序暂时没有可直接跳转的链接。已复制搜索词“${keyword}”，请在微信顶部搜索栏粘贴后打开。`,
          showCancel: false,
          confirmText: "我知道了",
        });
      },
      fail: () => {
        wx.showModal({
          title: item.title || "常用小程序",
          content: `这个小程序暂时没有可直接跳转的链接。请在微信顶部搜索栏搜索“${keyword}”后打开。`,
          showCancel: false,
          confirmText: "我知道了",
        });
      },
    });
  },
  fallbackToShortLink(item) {
    const shortLink = String(item?.shortLink || "").trim();
    if (!shortLink) {
      this.showManualSearchTip(item);
      return;
    }
    wx.setClipboardData({
      data: shortLink,
      success: () => {
        wx.showModal({
          title: item.title || "常用小程序",
          content: "暂时无法直接打开，已复制小程序短链。把它发送到微信聊天窗口后点击，即可打开。",
          showCancel: false,
          confirmText: "我知道了",
        });
      },
      fail: () => {
        wx.showModal({
          title: item.title || "常用小程序",
          content: "暂时无法直接打开，请稍后再试。",
          showCancel: false,
          confirmText: "我知道了",
        });
      },
    });
  },
  openMiniProgramLink(e) {
    const key = String(e.currentTarget.dataset.key || "").trim();
    const item = this.findMiniProgramLink(key);
    if (!item) {
      wx.showToast({ title: "入口未配置", icon: "none" });
      return;
    }
    if (item.appId) {
      if (typeof wx.navigateToMiniProgram !== "function") {
        this.showManualSearchTip(item);
        return;
      }
      wx.navigateToMiniProgram({
        appId: item.appId,
        fail: () => {
          this.showManualSearchTip(item);
        },
      });
      return;
    }
    if (item.manualSearchOnly || !item.shortLink) {
      this.showManualSearchTip(item);
      return;
    }
    if (typeof wx.navigateToMiniProgram !== "function") {
      this.fallbackToShortLink(item);
      return;
    }
    wx.navigateToMiniProgram({
      shortLink: item.shortLink,
      fail: () => {
        this.fallbackToShortLink(item);
      },
    });
  },
  onPhoneChange(e) {
    this.setData({ phoneCurrent: Number(e?.detail?.current || 0) });
  },
  callCurrentPhone() {
    const current = Number(this.data.phoneCurrent || 0);
    const phoneNumber = String(this.data.phoneItems?.[current]?.num || "").trim();
    if (!phoneNumber) {
      wx.showToast({ title: "暂未配置联系电话", icon: "none" });
      return;
    }
    dialPhoneNumber(phoneNumber);
  },
  async onShow() {
    const ok = await this.refreshProfile();
    if (!ok) {
      return;
    }
    this.loadHomeData();
    this.loadNoticeSubscribeStatus();
  },
  onShareAppMessage() {
    return buildShareAppMessage({
      title: HOME_SHARE_TITLE,
      path: HOME_SHARE_PATH,
    });
  },
  onShareTimeline() {
    return buildShareTimeline({
      title: HOME_SHARE_TITLE,
    });
  },
  goMoreNotices() {
    wx.navigateTo({ url: "/pages/notices/notices" });
  },
  openNoticeDetail(e) {
    const id = Number(e.currentTarget.dataset.id);
    if (!id) {
      return;
    }
    wx.navigateTo({ url: `/pages/notice-detail/notice-detail?id=${id}` });
  },
  onHeroChange(e) {
    const current = Number(e.detail?.current || 0);
    this.setData({ heroCurrent: Number.isNaN(current) ? 0 : current });
  },
  tapHero(e) {
    const noticeId = Number(e.currentTarget.dataset.noticeId || 0);
    if (!noticeId) {
      return;
    }
    wx.navigateTo({ url: `/pages/notice-detail/notice-detail?id=${noticeId}` });
  },
  goSubscribeTips() {
    this.requestNoticeSubscription("home_button");
  },
});
