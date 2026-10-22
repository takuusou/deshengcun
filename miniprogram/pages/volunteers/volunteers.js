const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const { resolveViewerProfile, openAuthCenter } = require("../../utils/access");
const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");

const RECORD_TABS = [
  { value: "all", label: "全部" },
  { value: "doing", label: "处理中" },
  { value: "done", label: "已办结" },
  { value: "back", label: "已退回" },
];

// 后端原始状态 → 三档统一状态
function mapStatus(raw) {
  const s = String(raw || "pending").trim().toLowerCase();
  if (s === "resolved") {
    return { group: "done", label: "已办结" };
  }
  if (s === "rejected" || s === "closed") {
    return { group: "back", label: "已退回" };
  }
  return { group: "doing", label: "处理中" };
}

function shortDate(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  const m = text.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[1]}-${m[2]}-${m[3]}` : text.slice(0, 10);
}

function buildGovRecord(item) {
  const st = mapStatus(item?.status);
  const isCert = item?.service_key === "certificate";
  const option = String(item?.selected_option || "").trim();
  const serviceTitle = String(item?.service_title || "").trim();
  let title;
  if (isCert) {
    title = option ? `开具证明：${option}` : (serviceTitle || "开具证明");
  } else {
    title = serviceTitle || option || "政务办理";
  }
  return {
    record_id: `gov_${item.id}`,
    raw_id: Number(item?.id || 0),
    source: "gov",
    title,
    type_label: isCert ? "开具证明" : (serviceTitle || "政务办理"),
    group: st.group,
    status_label: st.label,
    date: shortDate(item?.created_at),
    sort_time: String(item?.updated_at || item?.created_at || ""),
  };
}

function buildRequestRecord(item) {
  const st = mapStatus(item?.status);
  const t = String(item?.request_type || "").trim().toLowerCase();
  const typeLabel =
    t === "complaint" ? "随手拍" : t === "dibao" ? "低保申请" : t === "tekun" ? "特困认定" : "服务需求";
  return {
    record_id: `request_${item.id}`,
    raw_id: Number(item?.id || 0),
    source: "request",
    title: String(item?.title || typeLabel).trim() || typeLabel,
    type_label: typeLabel,
    group: st.group,
    status_label: st.label,
    date: shortDate(item?.created_at),
    sort_time: String(item?.updated_at || item?.created_at || ""),
  };
}

Page({
  data: {
    hasProfile: false,
    loading: false,
    recordTabs: RECORD_TABS.map((t) => ({ ...t, count: 0 })),
    recordTab: "all",
    doingCount: 0,
    allRecords: [],
    displayRecords: [],
  },

  onLoad() {
    showDefaultShareMenu();
  },

  async onShow() {
    const profile = await resolveViewerProfile({ refresh: true, silent: true });
    this.setData({ hasProfile: !!profile });
    this.loadData(!!profile);
  },

  async loadData(hasProfile) {
    if (!hasProfile) {
      this.setData({ allRecords: [], displayRecords: [], doingCount: 0 });
      return;
    }
    this.setData({ loading: true });
    try {
      const [govRows, requestRows] = await Promise.all([
        request({ path: "/gov/applications" }),
        request({ path: "/requests" }),
      ]);
      const allRecords = []
        .concat((govRows || []).map(buildGovRecord))
        .concat((requestRows || []).map(buildRequestRecord))
        .sort((a, b) => String(b.sort_time || "").localeCompare(String(a.sort_time || "")));
      const doingCount = allRecords.filter((r) => r.group === "doing").length;
      this.setData(
        {
          allRecords,
          doingCount,
          recordTabs: RECORD_TABS.map((t) => ({
            ...t,
            count:
              t.value === "all"
                ? allRecords.length
                : allRecords.filter((r) => r.group === t.value).length,
          })),
        },
        () => this.applyFilters()
      );
    } catch (err) {
      this.setData({ allRecords: [], displayRecords: [], doingCount: 0 });
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },

  applyFilters() {
    const tab = this.data.recordTab;
    let records = [...(this.data.allRecords || [])];
    if (tab !== "all") {
      records = records.filter((r) => r.group === tab);
    }
    this.setData({ displayRecords: records });
  },

  switchRecordTab(e) {
    const tab = String(e.currentTarget.dataset.tab || "");
    if (!tab || tab === this.data.recordTab) return;
    this.setData({ recordTab: tab }, () => this.applyFilters());
  },

  goAuthCenter() {
    openAuthCenter();
  },

  goServicePage() {
    wx.switchTab({ url: "/pages/service/service" });
  },

  openRecordDetail(e) {
    const source = String(e.currentTarget.dataset.source || "").trim();
    const recordId = Number(e.currentTarget.dataset.recordId || 0);
    if (!source || !recordId) return;
    wx.navigateTo({
      url: `/pages/handling-record-detail/handling-record-detail?source=${encodeURIComponent(source)}&id=${recordId}`,
    });
  },

  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜服务通 - 办理记录", path: "/pages/volunteers/volunteers" });
  },

  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通 - 办理记录" });
  },
});
