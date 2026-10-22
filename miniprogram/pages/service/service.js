const { request } = require("../../utils/request");
const { resolveViewerProfile, ensureVerifiedVillager } = require("../../utils/access");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");

const GOV_SERVICE_CARDS = [
  {
    key: "certificate",
    title: "开具证明",
    iconSrc: "/assets/icons/document.svg",
    serviceKeys: ["certificate"],
    fallbackTitle: "开具证明",
    fallbackContent: "请说明需要开具的证明类型、用途和联系电话。",
  },
  {
    key: "lowincome",
    title: "低保申请",
    iconSrc: "/assets/icons/shield-check-red.svg",
    serviceKeys: ["lowincome", "dibao"],
    matchWords: ["低保"],
    fallbackTitle: "低保申请",
    fallbackContent: "请说明家庭人口、收入来源、主要困难和联系电话，村委会将核实后协助办理。",
  },
  {
    key: "poverty",
    title: "特困认证",
    iconSrc: "/assets/icons/circle-plus-red.svg",
    serviceKeys: ["poverty", "special_care", "tekun"],
    matchWords: ["特困"],
    fallbackTitle: "特困认证",
    fallbackContent: "请说明认定对象、困难情况、照护情况和联系电话，村委会将核实后协助办理。",
  },
];

const CIVIC_CARDS = [
  { key: "snapshot", title: "随手拍", iconSrc: "/assets/icons/camera-red.svg" },
  { key: "training", title: "就业培训", iconSrc: "/assets/icons/graduation-red.svg" },
  { key: "volunteer", title: "志愿服务", iconSrc: "/assets/icons/users-red.svg" },
  { key: "proposal", title: "建议", iconSrc: "/assets/icons/chat-red.svg" },
];

function matchGovService(rows, card) {
  const serviceKeys = new Set(card.serviceKeys || []);
  const matchWords = card.matchWords || [];
  return (
    (rows || []).find((item) => serviceKeys.has(String(item?.service_key || "").trim())) ||
    (rows || []).find((item) => matchWords.some((word) => String(item?.title || "").includes(word))) ||
    null
  );
}

function buildRequestUrl(title, content, options = {}) {
  const requestType = options.requestType || "service";
  const mode = options.mode || "";
  return (
    "/pages/requests/requests?intentType=" +
    encodeURIComponent(requestType) +
    "&intentTitle=" +
    encodeURIComponent(title || "便民服务") +
    "&intentContent=" +
    encodeURIComponent(content || "请填写需要村委会协助办理的事项。") +
    (mode ? `&intentMode=${encodeURIComponent(mode)}` : "")
  );
}

Page({
  data: {
    govServiceCards: GOV_SERVICE_CARDS,
    civicCards: CIVIC_CARDS,
    govServiceFallbacks: {},
  },
  onLoad() {
    showDefaultShareMenu();
  },
  async onShow() {
    await resolveViewerProfile({ refresh: true, silent: true });
    this.loadGovServices();
  },
  async loadGovServices() {
    try {
      const rows = await request({ path: "/gov/services" });
      const govServiceFallbacks = {};
      GOV_SERVICE_CARDS.forEach((card) => {
        govServiceFallbacks[card.key] = {
          title: card.fallbackTitle,
          content: card.fallbackContent,
        };
      });
      const govServiceCards = GOV_SERVICE_CARDS.map((card) => {
        const matched = matchGovService(rows, card);
        return {
          ...card,
          serviceId: Number(matched?.id || 0),
        };
      });
      this.setData({
        govServiceCards,
        govServiceFallbacks,
      });
    } catch (_) {
      const govServiceFallbacks = {};
      GOV_SERVICE_CARDS.forEach((card) => {
        govServiceFallbacks[card.key] = {
          title: card.fallbackTitle,
          content: card.fallbackContent,
        };
      });
      this.setData({
        govServiceCards: GOV_SERVICE_CARDS.map((card) => ({ ...card, serviceId: 0 })),
        govServiceFallbacks,
      });
    }
  },
  async openGovService(e) {
    const key = String(e.currentTarget.dataset.key || "");
    if (key === "lowincome") {
      wx.navigateTo({ url: "/pages/dibao/dibao" });
      return;
    }
    if (key === "poverty") {
      wx.navigateTo({ url: "/pages/tekun/tekun" });
      return;
    }
    const id = Number(e.currentTarget.dataset.id || 0);
    if (id) {
      wx.navigateTo({ url: `/pages/gov-service-detail/gov-service-detail?id=${id}` });
      return;
    }
    const fallback = this.data.govServiceFallbacks?.[key] || {};
    const ok = await ensureVerifiedVillager();
    if (!ok) return;
    wx.navigateTo({ url: buildRequestUrl(fallback.title, fallback.content) });
  },
  async tapCivic(e) {
    const key = String(e.currentTarget.dataset.key || "");
    if (key === "proposal") {
      const ok = await ensureVerifiedVillager();
      if (!ok) return;
      wx.navigateTo({ url: "/pages/services/proposal/proposal" });
      return;
    }
    if (key === "snapshot") {
      const ok = await ensureVerifiedVillager();
      if (!ok) return;
      wx.navigateTo({
        url: buildRequestUrl("随手拍环境上报", "", {
          requestType: "complaint",
          mode: "snapshot",
        }),
      });
      return;
    }
    if (key === "volunteer") {
      wx.navigateTo({ url: "/pages/services/volunteer/volunteer" });
      return;
    }
    if (key === "training") {
      wx.navigateTo({ url: "/pages/services/training/training" });
    }
  },
  goMyRecords() {
    wx.navigateTo({ url: "/pages/volunteers/volunteers" });
  },
  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜服务通 - 便民服务", path: "/pages/service/service" });
  },
  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通 - 便民服务" });
  },
});
