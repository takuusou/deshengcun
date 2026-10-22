const DEFAULT_SHARE_TITLE = "得胜服务通";
const DEFAULT_SHARE_IMAGE_URL = "/assets/brand/wei-renmin-fuwu.jpg";
const DEFAULT_SHARE_PATH = "/pages/home/home";

function showDefaultShareMenu() {
  if (typeof wx.showShareMenu === "function") {
    wx.showShareMenu({
      menus: ["shareAppMessage", "shareTimeline"],
    });
  }
}

function normalizeText(value, fallback) {
  const text = String(value || "").trim();
  return text || fallback;
}

function buildSharePath(path, query) {
  const normalizedPath = normalizeText(path, DEFAULT_SHARE_PATH);
  const normalizedQuery = String(query || "").trim().replace(/^\?+/, "");
  return normalizedQuery ? `${normalizedPath}?${normalizedQuery}` : normalizedPath;
}

function buildShareAppMessage(options = {}) {
  return {
    title: normalizeText(options.title, DEFAULT_SHARE_TITLE),
    path: buildSharePath(options.path, options.query),
    imageUrl: normalizeText(options.imageUrl, DEFAULT_SHARE_IMAGE_URL),
  };
}

function buildShareTimeline(options = {}) {
  return {
    title: normalizeText(options.title, DEFAULT_SHARE_TITLE),
    query: String(options.query || "").trim().replace(/^\?+/, ""),
    imageUrl: normalizeText(options.imageUrl, DEFAULT_SHARE_IMAGE_URL),
  };
}

module.exports = {
  showDefaultShareMenu,
  buildShareAppMessage,
  buildShareTimeline,
};
