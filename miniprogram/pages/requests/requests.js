const { request } = require("../../utils/request");
const { uploadImages } = require("../../utils/upload");
const { getErrorMessage } = require("../../utils/messages");
const {
  compactPhone,
  formatPhoneInput,
  isValidMobilePhone,
} = require("../../utils/phone");
const {
  resolveViewerProfile,
  ensureVerifiedVillager,
  isVerifiedVillager,
  openAuthCenter,
} = require("../../utils/access");

const REQUEST_TYPE_OPTIONS = [
  { value: "service", label: "服务需求" },
  { value: "complaint", label: "问题投诉" },
];

function getProfilePhone(profile) {
  const phone = String(profile?.phone || "").trim();
  return isValidMobilePhone(phone) ? phone : "";
}

Page({
  data: {
    canSubmitRequest: false,
    isSnapshotMode: false,
    snapshotCameraOpened: false,
    requestTypeOptions: REQUEST_TYPE_OPTIONS,
    requestType: "service",
    title: "",
    content: "",
    contactPhone: "",
    localPhotos: [],
    submitting: false,
  },
  onLoad(options) {
    const titleRaw = options?.intentTitle || "";
    const contentRaw = options?.intentContent || "";
    const typeRaw = String(options?.intentType || "").trim();
    const modeRaw = String(options?.intentMode || "").trim();
    const decode = (text) => {
      try {
        return decodeURIComponent(text);
      } catch (err) {
        return text;
      }
    };
    const title = decode(titleRaw);
    const content = decode(contentRaw);
    if (!title && !content) {
      return;
    }
    const requestType = REQUEST_TYPE_OPTIONS.some((item) => item.value === typeRaw) ? typeRaw : "service";
    const isSnapshotMode = modeRaw === "snapshot";
    const titlePrefix = requestType === "complaint" || isSnapshotMode ? "" : "合作咨询：";
    this.setData({
      isSnapshotMode,
      requestType,
      title: title ? `${titlePrefix}${title}` : "",
      content: content || "",
    });
  },
  onShow() {
    this.refreshAccess();
  },
  isValidPhone(value) {
    return isValidMobilePhone(value);
  },
  async refreshAccess() {
    const profile = await resolveViewerProfile({ refresh: true, silent: true });
    const profilePhone = getProfilePhone(profile);
    const nextData = {
      canSubmitRequest: isVerifiedVillager(profile),
    };
    if (profilePhone && !compactPhone(this.data.contactPhone)) {
      nextData.contactPhone = formatPhoneInput(profilePhone);
    }
    this.setData({
      ...nextData,
    });
    if (this.data.isSnapshotMode && isVerifiedVillager(profile) && !this.data.snapshotCameraOpened) {
      this.setData({ snapshotCameraOpened: true });
      setTimeout(() => {
        this.choosePhotos({ currentTarget: { dataset: { source: "camera" } } });
      }, 350);
    }
  },
  goAuthCenter() {
    openAuthCenter();
  },
  onTypeChange(e) {
    const value = e?.detail?.value;
    if (!value) {
      return;
    }
    this.setData({ requestType: value });
  },
  onTitleInput(e) {
    this.setData({ title: e.detail.value });
  },
  onContentInput(e) {
    this.setData({ content: e.detail.value });
  },
  onContactPhoneInput(e) {
    this.setData({ contactPhone: formatPhoneInput(e.detail.value) });
  },
  async choosePhotos(e = {}) {
    const ok = await ensureVerifiedVillager({
      title: "诉求提交需登记身份信息",
      content: "上传诉求图片前，请先登录并完成基础实名登记。",
    });
    if (!ok) {
      return;
    }
    const remain = 9 - (this.data.localPhotos || []).length;
    if (remain <= 0) {
      wx.showToast({ title: "最多上传9张", icon: "none" });
      return;
    }
    const source = String(e?.currentTarget?.dataset?.source || "");
    wx.chooseMedia({
      count: remain,
      mediaType: ["image"],
      sourceType: source === "camera" ? ["camera"] : ["album", "camera"],
      success: (res) => {
        const files = res?.tempFiles || [];
        const paths = files.map((f) => f.tempFilePath).filter(Boolean);
        this.setData({
          localPhotos: (this.data.localPhotos || []).concat(paths).slice(0, 9),
        });
      },
    });
  },
  removeLocalPhoto(e) {
    const index = Number(e.currentTarget.dataset.index);
    const photos = [...(this.data.localPhotos || [])];
    if (Number.isNaN(index) || index < 0 || index >= photos.length) {
      return;
    }
    photos.splice(index, 1);
    this.setData({ localPhotos: photos });
  },
  previewLocalPhoto(e) {
    const current = e.currentTarget.dataset.current || "";
    const urls = this.data.localPhotos || [];
    if (!current || !urls.length) {
      return;
    }
    wx.previewImage({ current, urls });
  },
  async submitRequest() {
    if (this.data.submitting) {
      return;
    }
    const ok = await ensureVerifiedVillager({
      title: "诉求提交需登记身份信息",
      content: "提交诉求前，请先登录并完成基础实名登记。",
    });
    if (!ok) {
      return;
    }
    if (!this.data.title || !this.data.content) {
      wx.showToast({ title: this.data.isSnapshotMode ? "请填写现场情况" : "请填写标题和内容", icon: "none" });
      return;
    }
    const contactPhone = compactPhone(this.data.contactPhone);
    if (contactPhone && !this.isValidPhone(contactPhone)) {
      wx.showToast({ title: "手机号格式不正确", icon: "none" });
      return;
    }
    this.setData({ submitting: true });
    try {
      const submittedTitle = this.data.title || "诉求服务";
      const photoUrls = await uploadImages(this.data.localPhotos || [], "villager", "request");
      await request({
        path: "/requests",
        method: "POST",
        data: {
          request_type: this.data.requestType,
          title: this.data.title,
          content: this.data.content,
          contact_phone: contactPhone,
          photo_urls: photoUrls,
        },
      });
      wx.showToast({ title: "提交成功", icon: "success" });
      this.setData({
        title: this.data.isSnapshotMode ? "随手拍环境上报" : "",
        content: "",
        contactPhone: contactPhone ? formatPhoneInput(contactPhone) : "",
        localPhotos: [],
      });
      wx.navigateTo({
        url: `/pages/result/result?status=success&title=${encodeURIComponent(submittedTitle)}`,
      });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
