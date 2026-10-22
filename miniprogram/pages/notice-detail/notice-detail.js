const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const { formatLocalDateTime } = require("../../utils/date");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");
const { normalizePhotoUrls } = require("../../utils/photo-url");

Page({
  data: {
    noticeId: 0,
    loading: false,
    detail: null,
  },
  goBack() {
    wx.navigateBack();
  },
  onLoad(options) {
    showDefaultShareMenu();
    const noticeId = Number(options?.id || 0);
    if (!noticeId) {
      wx.showToast({ title: "通知参数无效", icon: "none" });
      wx.navigateBack({ delta: 1 });
      return;
    }
    this.setData({ noticeId });
    this.loadDetail();
  },
  async loadDetail() {
    if (!this.data.noticeId) {
      return;
    }
    this.setData({ loading: true });
    try {
      const detailRaw = await request({ path: `/notices/${this.data.noticeId}` });
      const detail = this.normalizeDetail(detailRaw);
      this.setData({ detail });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },
  normalizeDetail(detailRaw) {
    const detail = detailRaw || {};
    return {
      ...detail,
      photo_urls: normalizePhotoUrls(detail.photo_urls || []),
      created_at_text: formatLocalDateTime(detail.created_at),
    };
  },
  previewPhoto(e) {
    const current = e.currentTarget.dataset.current || "";
    const urls = this.data.detail?.photo_urls || [];
    if (!current || !urls.length) {
      return;
    }
    wx.previewImage({ current, urls });
  },
  onShareAppMessage() {
    const title = String(this.data.detail?.title || "").trim() || "得胜服务通 - 通知详情";
    return buildShareAppMessage({
      title,
      path: "/pages/notice-detail/notice-detail",
      query: `id=${this.data.noticeId || 0}`,
      imageUrl: this.data.detail?.photo_urls?.[0] || "",
    });
  },
  onShareTimeline() {
    const title = String(this.data.detail?.title || "").trim() || "得胜服务通 - 通知详情";
    return buildShareTimeline({
      title,
      query: `id=${this.data.noticeId || 0}`,
      imageUrl: this.data.detail?.photo_urls?.[0] || "",
    });
  },
});
