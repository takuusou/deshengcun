const { request } = require("../../utils/request");
const { uploadImages } = require("../../utils/upload");
const { getErrorMessage } = require("../../utils/messages");
const { ensureVerifiedVillager } = require("../../utils/access");

const DEFAULT_CONFIG = {
  requestType: "",
  title: "材料上传",
  subtitle: "材料收集",
  introText: "请先备齐材料，再点下一步逐项拍照上传。",
  doneTitle: "材料已提交",
  doneMessage: "村委会已收到你的材料，会尽快为你办理。办理进度会通过微信通知你。",
  emptyReceiptText: "本次未上传照片材料，村委会后续会与你核实。",
};

function normalizeConfig(config = {}) {
  return {
    ...DEFAULT_CONFIG,
    ...(config || {}),
  };
}

function normalizeMaterials(materials = []) {
  return (materials || []).map((item, index) => ({
    key: String(item.key || `material_${index + 1}`),
    name: String(item.name || ""),
    shortName: String(item.shortName || item.name || `材料${index + 1}`),
    desc: String(item.desc || ""),
    index: index + 1,
    photos: Array.isArray(item.photos) ? item.photos : [],
    done: false,
    current: index === 0,
    pending: index > 0,
    nodeClass: index === 0 ? "cur" : "todo",
    linkClass: "",
  }));
}

function decorateMaterials(materials, currentIndex) {
  return (materials || []).map((item, index) => {
    const done = Array.isArray(item.photos) && item.photos.length > 0;
    let nodeClass = "todo";
    if (done) nodeClass = "done";
    if (index === currentIndex && !done) nodeClass = "cur";
    return {
      ...item,
      done,
      current: index === currentIndex,
      pending: index > currentIndex && !done,
      nodeClass,
      linkClass: index < currentIndex || done ? "passed" : "",
    };
  });
}

function buildReceiptItems(materials) {
  return (materials || [])
    .filter((item) => Array.isArray(item.photos) && item.photos.length > 0)
    .map((item) => ({
      key: item.key,
      name: item.name,
      count: item.photos.length,
    }));
}

Component({
  options: {
    styleIsolation: "isolated",
  },
  properties: {
    config: {
      type: Object,
      value: {},
    },
    materialItems: {
      type: Array,
      value: [],
    },
  },
  data: {
    step: "prepare",
    flowConfig: normalizeConfig(),
    materials: [],
    currentIndex: 0,
    currentMaterial: null,
    uploadedCount: 0,
    totalCount: 0,
    nextButtonText: "下一项",
    receiptItems: [],
    submitting: false,
  },
  lifetimes: {
    attached() {
      this._ready = true;
      this.resetFlow();
    },
  },
  observers: {
    "config, materialItems": function () {
      if (!this._ready) return;
      this.resetFlow();
    },
  },
  methods: {
    resetFlow() {
      const flowConfig = normalizeConfig(this.data.config);
      const materials = normalizeMaterials(this.data.materialItems);
      this.setData(
        {
          step: "prepare",
          flowConfig,
          materials,
          currentIndex: 0,
        },
        () => this.refreshDerivedState()
      );
    },
    refreshDerivedState(next = {}) {
      const currentIndex = Number(
        Object.prototype.hasOwnProperty.call(next, "currentIndex") ? next.currentIndex : this.data.currentIndex
      );
      const sourceMaterials = next.materials || this.data.materials || [];
      const materials = decorateMaterials(sourceMaterials, currentIndex);
      const currentMaterial = materials[currentIndex] || materials[0] || null;
      const uploadedCount = materials.filter((item) => item.done).length;
      const receiptItems = buildReceiptItems(materials);
      const { materials: ignoredMaterials, currentIndex: ignoredCurrentIndex, ...rest } = next;
      this.setData({
        ...rest,
        materials,
        currentIndex,
        currentMaterial,
        uploadedCount,
        totalCount: materials.length,
        receiptItems,
        nextButtonText: currentIndex >= materials.length - 1 ? "提交给村委" : "下一项",
      });
    },
    startUpload() {
      this.refreshDerivedState({ step: "upload", currentIndex: 0 });
    },
    chooseCurrentPhotos() {
      const currentIndex = Number(this.data.currentIndex || 0);
      const materials = [...(this.data.materials || [])];
      const current = materials[currentIndex];
      if (!current) return;
      const photos = Array.isArray(current.photos) ? current.photos : [];
      const remain = 9 - photos.length;
      if (remain <= 0) {
        wx.showToast({ title: "每项最多上传9张", icon: "none" });
        return;
      }
      wx.chooseMedia({
        count: remain,
        mediaType: ["image"],
        sourceType: ["album", "camera"],
        success: (res) => {
          const paths = (res?.tempFiles || []).map((item) => item.tempFilePath).filter(Boolean);
          if (!paths.length) return;
          materials[currentIndex] = {
            ...current,
            photos: photos.concat(paths).slice(0, 9),
          };
          this.refreshDerivedState({ materials });
        },
      });
    },
    removeCurrentPhoto(e) {
      const photoIndex = Number(e.currentTarget.dataset.index);
      const currentIndex = Number(this.data.currentIndex || 0);
      const materials = [...(this.data.materials || [])];
      const current = materials[currentIndex];
      const photos = [...(current?.photos || [])];
      if (Number.isNaN(photoIndex) || photoIndex < 0 || photoIndex >= photos.length) {
        return;
      }
      photos.splice(photoIndex, 1);
      materials[currentIndex] = { ...current, photos };
      this.refreshDerivedState({ materials });
    },
    previewCurrentPhoto(e) {
      const current = String(e.currentTarget.dataset.current || "");
      const urls = this.data.currentMaterial?.photos || [];
      if (!current || !urls.length) return;
      wx.previewImage({ current, urls });
    },
    goNextMaterial() {
      const materials = this.data.materials || [];
      const currentIndex = Number(this.data.currentIndex || 0);
      if (currentIndex < materials.length - 1) {
        this.refreshDerivedState({ currentIndex: currentIndex + 1 });
        return;
      }
      this.submitMaterials();
    },
    async submitMaterials() {
      if (this.data.submitting) {
        return;
      }
      const requestType = String(this.data.flowConfig?.requestType || "").trim().toLowerCase();
      if (requestType !== "dibao" && requestType !== "tekun") {
        // 未配置业务类型时退回旧的本地回执流程，避免误调接口。
        this.refreshDerivedState({ step: "done" });
        this.triggerEvent("submitted", {
          materials: this.data.materials,
          receiptItems: this.data.receiptItems,
        });
        return;
      }

      const ok = await ensureVerifiedVillager({
        title: "提交材料需登记身份信息",
        content: "提交申请材料前，请先登录并完成基础实名登记。",
      });
      if (!ok) {
        return;
      }

      const materials = this.data.materials || [];
      const hasAnyPhoto = materials.some(
        (item) => Array.isArray(item.photos) && item.photos.length > 0
      );
      if (!hasAnyPhoto) {
        wx.showToast({ title: "请至少上传一项材料照片", icon: "none" });
        return;
      }

      this.setData({ submitting: true });
      wx.showLoading({ title: "正在提交...", mask: true });
      try {
        const manifest = [];
        const flatPhotoUrls = [];
        for (const item of materials) {
          const photos = Array.isArray(item.photos) ? item.photos : [];
          const urls = photos.length ? await uploadImages(photos, "villager", "request") : [];
          manifest.push({ key: item.key, name: item.name, count: urls.length });
          flatPhotoUrls.push(...urls);
        }
        const title = String(this.data.flowConfig?.title || "申请材料").trim();
        const content = JSON.stringify({ flow: "material", kind: requestType, materials: manifest });
        await request({
          path: "/requests",
          method: "POST",
          data: {
            request_type: requestType,
            title,
            content,
            contact_phone: "",
            photo_urls: flatPhotoUrls,
          },
        });
        wx.hideLoading();
        wx.showToast({ title: "提交成功", icon: "success" });
        this.refreshDerivedState({ step: "done" });
        this.triggerEvent("submitted", {
          materials: this.data.materials,
          receiptItems: this.data.receiptItems,
        });
      } catch (err) {
        wx.hideLoading();
        wx.showToast({ title: getErrorMessage(err), icon: "none" });
      } finally {
        this.setData({ submitting: false });
      }
    },
    returnBack() {
      const pages = getCurrentPages();
      if (pages.length > 1) {
        wx.navigateBack({ delta: 1 });
        return;
      }
      wx.switchTab({ url: "/pages/service/service" });
    },
    viewMySubmissions() {
      wx.switchTab({ url: "/pages/me/me" });
    },
  },
});
