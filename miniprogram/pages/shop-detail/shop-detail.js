const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const { buildShareAppMessage, buildShareTimeline } = require("../../utils/share");
const { normalizePhotoUrl } = require("../../utils/photo-url");

function buildDetail(item) {
  const sections = [
    { heading: "历史渊源", body: String(item?.history || "").trim() },
    { heading: "传统制法", body: String(item?.craft || "").trim() },
    { heading: "风味特点", body: String(item?.flavor || "").trim() },
  ].filter((section) => section.body);
  return {
    id: Number(item?.id || 0),
    title: String(item?.name || "").trim(),
    subtitle: String(item?.subtitle || "").trim(),
    detail_img_url: normalizePhotoUrl(item?.detail_img_url),
    sections,
  };
}

Page({
  data: {
    detail: null,
  },
  async onLoad(options) {
    const id = Number(options.id || 0);
    if (!id) {
      wx.showToast({ title: "内容不存在", icon: "none" });
      wx.navigateBack();
      return;
    }
    try {
      const row = await request({ path: `/products/${id}` });
      const detail = buildDetail(row);
      this.setData({ detail });
      wx.setNavigationBarTitle({ title: detail.title || "得胜好物" });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
      wx.navigateBack();
    }
  },
  onShareAppMessage() {
    const { detail } = this.data;
    return buildShareAppMessage({
      title: detail ? `得胜好物 · ${detail.title}` : "得胜好物",
      path: `/pages/shop-detail/shop-detail?id=${detail ? detail.id : ""}`,
    });
  },
  onShareTimeline() {
    const { detail } = this.data;
    return buildShareTimeline({
      title: detail ? `得胜好物 · ${detail.title}` : "得胜好物",
    });
  },
});
