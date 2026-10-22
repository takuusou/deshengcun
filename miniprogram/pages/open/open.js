const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const { resolveViewerProfile } = require("../../utils/access");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");
const { normalizePhotoUrl } = require("../../utils/photo-url");

const DEFAULT_INTRO_TEXT =
  "得胜村位于湖南省平江县上塔市镇，下辖叶家组、如家组、何家组、胡墩组、新屋组、徐家组、鲁家组、下西组、花园组。村级治理以通知公开、议事协同、志愿服务和数字公开为主线，持续提升基层服务效率。";
const OPEN_METRIC_FALLBACK = [
  { key: "village_groups", label: "村组", value: "9", iconSrc: "/assets/icons/village-groups-red.svg" },
  { key: "households", label: "家庭", value: "538", iconSrc: "/assets/icons/house.svg" },
  { key: "population", label: "人口", value: "1744", iconSrc: "/assets/icons/users-red.svg" },
  { key: "party_members", label: "党员", value: "42", iconSrc: "/assets/icons/star-red.svg" },
];

function numericText(value, fallback) {
  const text = String(value || "").trim();
  const match = text.match(/\d+/);
  return match ? match[0] : fallback;
}

function buildMetricDisplay(profile = {}) {
  return OPEN_METRIC_FALLBACK.map((item) => ({
    ...item,
    value: numericText(profile[item.key], item.value),
  }));
}

Page({
  data: {
    statsDisplay: OPEN_METRIC_FALLBACK,
    introText: DEFAULT_INTRO_TEXT,
    villagePhotoUrl: "",
  },
  onLoad() {
    showDefaultShareMenu();
  },
  async onShow() {
    await resolveViewerProfile({ refresh: true, silent: true });
    await this.loadPageData();
  },
  async loadPageData() {
    try {
      const profile = await request({ path: "/open/profile" });
      this.setData({
        statsDisplay: buildMetricDisplay(profile),
        villagePhotoUrl: normalizePhotoUrl(profile?.village_photo_url),
        introText: String(profile?.village_intro || "").trim() || DEFAULT_INTRO_TEXT,
      });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    }
  },
  previewCover() {
    const currentImage = this.data.villagePhotoUrl;
    if (!currentImage) {
      return;
    }
    wx.previewImage({
      current: currentImage,
      urls: [currentImage],
    });
  },
  onShareAppMessage() {
    return buildShareAppMessage({
      title: "得胜服务通 - 村务公开",
      path: "/pages/open/open",
    });
  },
  onShareTimeline() {
    return buildShareTimeline({
      title: "得胜服务通 - 村务公开",
    });
  },
});
