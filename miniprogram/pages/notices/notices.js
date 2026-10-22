const { request } = require("../../utils/request");
const { getErrorMessage, getRoleText } = require("../../utils/messages");
const { resolveViewerProfile } = require("../../utils/access");
const { formatLocalDateTime } = require("../../utils/date");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");

Page({
  data: {
    items: [],
    filteredItems: [],
    activeTab: "all",
    role: "villager",
    roleLabel: "游客",
    isCadre: false,
    loading: false,
  },
  onLoad() {
    showDefaultShareMenu();
  },
  async onShow() {
    const profile = await resolveViewerProfile({ refresh: true, silent: true });
    this.setData({
      role: profile ? "villager" : "guest",
      roleLabel: profile ? getRoleText("villager") : "游客",
      isCadre: false,
    });
    this.loadData();
  },
  async loadData() {
    this.setData({ loading: true });
    try {
      const rows = await request({ path: "/notices" });
      const items = (rows || [])
        .map((item) => {
          const content = String(item.content || "").replace(/\s+/g, " ").trim();
          return {
            ...item,
            time_text: formatLocalDateTime(item.created_at),
            content_preview: content.slice(0, 40),
            content_more: content.length > 40,
            sort_time: String(item.created_at || ""),
          };
        })
        .sort((a, b) => {
          return String(b.sort_time).localeCompare(String(a.sort_time));
        });
      this.setData({ items, filteredItems: items });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },
  previewItemPhoto(e) {
    const current = e.currentTarget.dataset.current || "";
    const itemIndex = Number(e.currentTarget.dataset.itemIndex);
    const urls = this.data.items?.[itemIndex]?.photo_urls || [];
    if (!current || !urls?.length) {
      return;
    }
    wx.previewImage({
      current,
      urls,
    });
  },
  openNoticeDetail(e) {
    const id = Number(e.currentTarget.dataset.id);
    if (!id) {
      return;
    }
    wx.navigateTo({ url: `/pages/notice-detail/notice-detail?id=${id}` });
  },
  onShareAppMessage() {
    return buildShareAppMessage({
      title: "得胜服务通 - 通知公告",
      path: "/pages/notices/notices",
    });
  },
  onShareTimeline() {
    return buildShareTimeline({
      title: "得胜服务通 - 通知公告",
    });
  },
});
