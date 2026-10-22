const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");
const { normalizePhotoUrl } = require("../../utils/photo-url");

function buildItem(item) {
  return {
    id: Number(item?.id || 0),
    title: String(item?.name || "").trim(),
    subtitle: String(item?.subtitle || "").trim(),
    cover_url: normalizePhotoUrl(item?.cover_url),
  };
}

Page({
  data: {
    loading: false,
    items: [],
  },

  onLoad() {
    showDefaultShareMenu();
    this.loadProducts();
  },

  onPullDownRefresh() {
    this.loadProducts().finally(() => wx.stopPullDownRefresh());
  },

  async loadProducts() {
    this.setData({ loading: true });
    try {
      const rows = await request({ path: "/products" });
      this.setData({ items: (rows || []).map((item) => buildItem(item)) });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
      this.setData({ items: [] });
    } finally {
      this.setData({ loading: false });
    }
  },

  tapCard(e) {
    const id = Number(e.currentTarget.dataset.id || 0);
    if (!id) {
      return;
    }
    wx.navigateTo({ url: `/pages/shop-detail/shop-detail?id=${id}` });
  },

  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜好物", path: "/pages/shop/shop" });
  },

  onShareTimeline() {
    return buildShareTimeline({ title: "得胜好物" });
  },
});
