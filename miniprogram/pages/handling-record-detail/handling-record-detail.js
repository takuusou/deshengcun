const { request } = require("../../utils/request");
const { getErrorMessage } = require("../../utils/messages");
const { resolveViewerProfile, ensureVerifiedVillager } = require("../../utils/access");
const { normalizePhotoUrl, normalizePhotoUrls } = require("../../utils/photo-url");
const { formatPhoneDisplay } = require("../../utils/phone");
const { buildRecordExtraRows, DEFAULT_RECORD_EXTRA_SKIP_KEYS } = require("../../utils/record");

function mapStatus(raw) {
  const s = String(raw || "pending").trim().toLowerCase();
  if (s === "resolved") return { group: "done", label: "已办结" };
  if (s === "rejected" || s === "closed") return { group: "back", label: "已退回" };
  return { group: "doing", label: "处理中" };
}

function formatDateTime(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  const m = text.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}`;
  return text.slice(0, 16).replace("T", " ");
}

function buildGovDetail(item) {
  const st = mapStatus(item?.status);
  const isCert = item?.service_key === "certificate";
  const option = String(item?.selected_option || "").trim();
  const serviceTitle = String(item?.service_title || "").trim();
  const title = isCert
    ? (option ? `开具证明：${option}` : (serviceTitle || "开具证明"))
    : (serviceTitle || option || "政务办理");
  const fields = [];
  if (isCert && option) fields.push({ k: "证明类型", v: option });
  buildRecordExtraRows(item?.extra_fields, { skipKeys: DEFAULT_RECORD_EXTRA_SKIP_KEYS, limit: 8 }).forEach((row) => {
    if (row.value) fields.push({ k: row.label, v: row.value });
  });
  if (item?.note) fields.push({ k: "备注", v: String(item.note).trim() });
  return {
    source: "gov",
    raw_id: Number(item?.id || 0),
    group: st.group,
    status_label: st.label,
    title,
    type_label: isCert ? "开具证明" : (serviceTitle || "政务办理"),
    submitted_at: formatDateTime(item?.created_at),
    reply_title: st.group === "back" ? "退回原因" : "处理结果",
    reply: String(item?.cadre_reply || "").trim(),
    fields,
    materials: [],
    attachments: normalizePhotoUrls(item?.supporting_photo_urls || []),
    // 电子证明：办结开证明时村委生成的盖章文书，存在 reply_photo_urls
    certificate_urls: isCert ? normalizePhotoUrls(item?.reply_photo_urls || []) : [],
    can_resubmit: st.group === "back",
    resubmit_url: "/pages/service/service",
  };
}

function buildRequestDetail(item) {
  const st = mapStatus(item?.status);
  const t = String(item?.request_type || "").trim().toLowerCase();
  const typeLabel =
    t === "complaint" ? "随手拍" : t === "dibao" ? "低保申请" : t === "tekun" ? "特困认定" : "服务需求";
  const fields = [];
  let materials = [];
  if (t === "dibao" || t === "tekun") {
    // 低保/特困的 content 是材料清单 JSON，解析成"材料名 ×份数"，不暴露原文
    try {
      const parsed = JSON.parse(item?.content || "{}");
      if (Array.isArray(parsed?.materials)) {
        materials = parsed.materials
          .filter((m) => Number(m?.count || 0) > 0)
          .map((m) => ({ name: String(m?.name || "").trim() || "材料", count: Number(m.count) }));
      }
    } catch (e) {
      materials = [];
    }
  } else if (item?.content) {
    fields.push({ k: "内容", v: String(item.content).trim() });
  }
  if (item?.contact_phone) fields.push({ k: "联系电话", v: formatPhoneDisplay(item.contact_phone) });
  let resubmitUrl;
  if (t === "dibao") resubmitUrl = "/pages/dibao/dibao";
  else if (t === "tekun") resubmitUrl = "/pages/tekun/tekun";
  else resubmitUrl = `/pages/requests/requests?intentType=${t === "complaint" ? "complaint" : "service"}`;
  return {
    source: "request",
    raw_id: Number(item?.id || 0),
    group: st.group,
    status_label: st.label,
    title: String(item?.title || typeLabel).trim() || typeLabel,
    type_label: typeLabel,
    submitted_at: formatDateTime(item?.created_at),
    reply_title: st.group === "back" ? "退回原因" : "处理结果",
    reply: String(item?.reply_text || "").trim(),
    fields,
    materials,
    attachments: normalizePhotoUrls(item?.photo_urls || []),
    certificate_urls: [],
    can_resubmit: st.group === "back",
    resubmit_url: resubmitUrl,
  };
}

Page({
  data: {
    source: "",
    recordId: 0,
    loading: false,
    detail: null,
  },
  onLoad(options) {
    const source = String(options?.source || "").trim();
    const recordId = Number(options?.id || 0);
    if (!source || !recordId) {
      wx.showToast({ title: "记录参数无效", icon: "none" });
      wx.navigateBack({ delta: 1 });
      return;
    }
    this.setData({ source, recordId });
  },
  async onShow() {
    if (!this.data.source || !this.data.recordId) return;
    const profile = await resolveViewerProfile({ refresh: true, silent: true });
    if (!profile) {
      await ensureVerifiedVillager({
        title: "查看记录需登录",
        content: "查看个人办理详情前，请先登录并完成基础实名登记。",
      });
      this.setData({ detail: null });
      return;
    }
    this.loadDetail();
  },
  async loadDetail() {
    this.setData({ loading: true });
    try {
      let detail = null;
      if (this.data.source === "gov") {
        const row = await request({ path: `/gov/applications/${this.data.recordId}` });
        detail = buildGovDetail(row);
      } else {
        const row = await request({ path: `/requests/${this.data.recordId}` });
        detail = buildRequestDetail(row);
      }
      this.setData({ detail });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
      this.setData({ detail: null });
    } finally {
      this.setData({ loading: false });
    }
  },
  previewAttachment(e) {
    const current = normalizePhotoUrl(e.currentTarget.dataset.current || "");
    const urls = normalizePhotoUrls(this.data.detail?.attachments || []);
    if (!current || !urls.length) return;
    wx.previewImage({ current, urls });
  },
  previewCertificate(e) {
    const current = normalizePhotoUrl(e.currentTarget.dataset.current || "");
    const urls = normalizePhotoUrls(this.data.detail?.certificate_urls || []);
    if (!current || !urls.length) return;
    wx.previewImage({ current, urls });
  },
  saveCertificate(e) {
    const url = normalizePhotoUrl(e.currentTarget.dataset.current || "") ||
      normalizePhotoUrls(this.data.detail?.certificate_urls || [])[0];
    if (!url) return;
    wx.showLoading({ title: "保存中", mask: true });
    wx.downloadFile({
      url,
      success: (res) => {
        if (res.statusCode !== 200 || !res.tempFilePath) {
          wx.hideLoading();
          wx.showToast({ title: "下载失败", icon: "none" });
          return;
        }
        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => {
            wx.hideLoading();
            wx.showToast({ title: "已保存到相册", icon: "success" });
          },
          fail: (err) => {
            wx.hideLoading();
            if (String(err?.errMsg || "").includes("auth")) {
              wx.showModal({
                title: "需要相册权限",
                content: "保存电子证明需要您授权保存到相册，请在设置中开启。",
                confirmText: "去设置",
                success: (r) => {
                  if (r.confirm) wx.openSetting();
                },
              });
            } else {
              wx.showToast({ title: "保存失败", icon: "none" });
            }
          },
        });
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({ title: "下载失败", icon: "none" });
      },
    });
  },
  resubmit() {
    const detail = this.data.detail;
    if (!detail || !detail.can_resubmit) return;
    const url = detail.resubmit_url || "/pages/service/service";
    wx.navigateTo({
      url,
      fail() {
        wx.switchTab({ url: "/pages/service/service" });
      },
    });
  },
});
