const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");

const SECTION_HEADING_PATTERN = /^[一二三四五六七八九十百]+、(.+)$/;

function buildPolicySections(content) {
  const sections = [];
  let current = { title: "政策信息", paragraphs: [] };
  String(content || "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line) => {
      const heading = line.match(SECTION_HEADING_PATTERN);
      if (heading) {
        if (current.paragraphs.length) sections.push(current);
        current = { title: line, paragraphs: [] };
        return;
      }
      current.paragraphs.push(line);
    });
  if (current.paragraphs.length) sections.push(current);
  return sections;
}

Page({
  data: {
    loading: false,
    sections: [],
    loadFailed: false,
  },
  onLoad() {
    showDefaultShareMenu();
    this.loadPolicy();
  },
  async loadPolicy() {
    this.setData({ loading: true });
    try {
      const policy = await request({ path: "/privacy/policy" });
      this.setData({
        sections: buildPolicySections(policy?.content),
        loadFailed: false,
      });
    } catch (err) {
      this.setData({ loadFailed: true });
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },
  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜服务通 - 隐私政策", path: "/pages/privacy/privacy" });
  },
  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通 - 隐私政策" });
  },
});
