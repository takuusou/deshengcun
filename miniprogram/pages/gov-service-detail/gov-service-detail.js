const { request } = require("../../utils/request");
const { uploadImages } = require("../../utils/upload");
const { getErrorMessage, getRoleText } = require("../../utils/messages");
const {
  compactPhone,
  dialPhoneNumber,
  formatPhoneDisplay,
  formatPhoneInput,
  isValidMobilePhone,
} = require("../../utils/phone");
const {
  resolveViewerProfile,
  ensureVerifiedVillager,
} = require("../../utils/access");

const CERT_GENDER_OPTIONS = ["男", "女", "未知"];
const VILLAGE_GROUP_OPTIONS = [
  "选择村组",
  "得胜村",
  "叶家组",
  "如家组",
  "何家组",
  "胡墩组",
  "新屋组",
  "徐家组",
  "鲁家组",
  "下西组",
  "花园组",
];
const INFO_APPLY_NOTE_KEYS = new Set(["remark", "note"]);
const INFO_APPLY_BASE_KEYS = new Set([
  "name",
  "real_name",
  "applicant_name",
  "phone",
  "mobile",
  "contact_phone",
  "contact_mobile",
  "contact",
]);
const INFO_APPLY_PHONE_KEYS = new Set([
  "phone",
  "mobile",
  "contactphone",
  "contactmobile",
  "contact",
]);
const ID_CARD_PATTERN = /^(\d{15}|\d{17}[0-9Xx])$/;
const DEFAULT_RELATION_OPTIONS = ["请选择关系"];
const RELATIONSHIP_OPTIONS = [
  ...DEFAULT_RELATION_OPTIONS,
  "父子",
  "母子",
  "父女",
  "母女",
  "夫妻",
  "爷孙",
  "奶孙",
  "外祖孙",
  "兄弟",
  "姐妹",
  "兄妹",
  "姐弟",
  "姑侄",
  "舅侄",
  "叔侄",
  "伯侄",
];
const CERTIFICATE_RELATION_OPTIONS_MAP = {
  relationship: RELATIONSHIP_OPTIONS,
  kinship_1st: RELATIONSHIP_OPTIONS,
  kinship_2nd: RELATIONSHIP_OPTIONS,
  spouse_relation: [...DEFAULT_RELATION_OPTIONS, "夫妻"],
};
const COMMON_CERTIFICATE_ORDER = [
  "relationship",
  "marriage_status",
  "family_difficulty",
  "employment",
  "spouse_relation",
  "household",
];
const COMMON_CERTIFICATE_KEYS = new Set(COMMON_CERTIFICATE_ORDER);

function normalizeCertificateKey(value) {
  return String(value || "").trim().toLowerCase();
}

function isRelationshipCertificateKey(value) {
  const key = normalizeCertificateKey(value);
  return !!CERTIFICATE_RELATION_OPTIONS_MAP[key];
}

function getRelationOptionsByCertificateKey(value) {
  const key = normalizeCertificateKey(value);
  return CERTIFICATE_RELATION_OPTIONS_MAP[key] || DEFAULT_RELATION_OPTIONS;
}

function isLikelyIdCard(value) {
  return ID_CARD_PATTERN.test(String(value || "").trim());
}

function getGenderFromIdCard(idCard) {
  const text = String(idCard || "").trim();
  let genderDigit = NaN;
  if (text.length === 18) {
    if (!/^\d{17}[\dXx]$/.test(text) || !getBirthDateFromIdCard(text)) return null;
    genderDigit = parseInt(text.charAt(16), 10);
  } else if (text.length === 15) {
    if (!/^\d{15}$/.test(text) || !getBirthDateFromIdCard(text)) return null;
    genderDigit = parseInt(text.charAt(14), 10);
  } else {
    return null;
  }
  if (Number.isNaN(genderDigit)) return null;
  return genderDigit % 2 === 0 ? "女" : "男";
}

function getBirthDateFromIdCard(idCard) {
  const text = String(idCard || "").trim();
  let raw = "";
  if (text.length === 18 && /^\d{17}[\dXx]$/.test(text)) {
    raw = text.slice(6, 14);
  } else if (text.length === 15 && /^\d{15}$/.test(text)) {
    raw = `19${text.slice(6, 12)}`;
  } else {
    return null;
  }
  const year = Number(raw.slice(0, 4));
  const month = Number(raw.slice(4, 6));
  const day = Number(raw.slice(6, 8));
  const date = new Date(year, month - 1, day);
  if (
    Number.isNaN(date.getTime()) ||
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null;
  }
  return date;
}

function getAgeFromBirthDate(birthDate, now = new Date()) {
  if (!(birthDate instanceof Date) || Number.isNaN(birthDate.getTime())) {
    return null;
  }
  let age = now.getFullYear() - birthDate.getFullYear();
  const monthDiff = now.getMonth() - birthDate.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < birthDate.getDate())) {
    age -= 1;
  }
  return age >= 0 && age < 130 ? age : null;
}

function formatBirthDateText(birthDate) {
  if (!(birthDate instanceof Date) || Number.isNaN(birthDate.getTime())) {
    return "";
  }
  const year = birthDate.getFullYear();
  const month = String(birthDate.getMonth() + 1).padStart(2, "0");
  const day = String(birthDate.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getIdCardInfo(idCard) {
  const gender = getGenderFromIdCard(idCard);
  const birthDate = getBirthDateFromIdCard(idCard);
  const age = getAgeFromBirthDate(birthDate);
  if (!gender || age === null) {
    return null;
  }
  return { gender, age, birthDate: formatBirthDateText(birthDate) };
}

function maskPhoneForSummary(value) {
  const text = String(value || "").trim();
  if (!text) return "手机号待补充";
  if (text.includes("*")) return text;
  return formatPhoneDisplay(text) || text;
}

function normalizeGenderText(value) {
  const text = String(value || "").trim();
  return CERT_GENDER_OPTIONS.includes(text) ? text : "";
}

function normalizeKnownGenderText(value) {
  const text = normalizeGenderText(value);
  return text && text !== "未知" ? text : "";
}

function splitCertificateTitle(title) {
  const text = String(title || "").trim();
  const match = text.match(/^(.+?)(（.+）)$/);
  if (!match) {
    return { main: text, note: "" };
  }
  return { main: match[1], note: match[2] };
}

function decorateCertificateOption(item) {
  const key = String(item?.key || "").trim();
  const title = String(item?.title || "").trim();
  const parts = splitCertificateTitle(title);
  return {
    ...item,
    key,
    title,
    display_title: parts.main || title,
    display_note: parts.note,
    is_common: COMMON_CERTIFICATE_KEYS.has(key),
  };
}
function certGenderToIndex(value) {
  const text = String(value || "").trim();
  const index = CERT_GENDER_OPTIONS.findIndex((item) => item === text);
  return index >= 0 ? index : 2;
}

function isGenderFieldText(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) {
    return false;
  }
  const compact = text.replace(/[\s_-]/g, "");
  return compact === "gender" || compact === "sex" || compact === "性别";
}

function isPhoneFieldText(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) {
    return false;
  }
  const compact = text.replace(/[\s_-]/g, "");
  return (
    INFO_APPLY_PHONE_KEYS.has(compact) ||
    compact === "电话" ||
    compact === "手机号" ||
    compact === "手机号码" ||
    compact === "联系电话" ||
    compact === "联系方式"
  );
}

function isAddressFieldText(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) {
    return false;
  }
  const compact = text.replace(/[\s_-]/g, "");
  return (
    compact.includes("address") ||
    compact.includes("location") ||
    compact.includes("地址") ||
    compact.includes("住址") ||
    compact.includes("所在地") ||
    compact.includes("经营场所")
  );
}

function buildAddressText(region, village, detail) {
  const regionText = Array.isArray(region) ? region.filter(Boolean).join(" ") : "";
  const villageText =
    village && village !== VILLAGE_GROUP_OPTIONS[0] ? String(village).trim() : "";
  const detailText = String(detail || "").trim();
  return [regionText, villageText, detailText].filter(Boolean).join(" ");
}

function normalizeInfoField(item) {
  const key = String(item?.key || "").trim();
  const label = String(item?.label || key).trim();
  if (!key) {
    return null;
  }
  const lowered = key.toLowerCase();
  return {
    key,
    lowered,
    label,
    placeholder: String(item?.placeholder || item?.label || "").trim(),
    is_gender: isGenderFieldText(key) || isGenderFieldText(label),
    is_phone: isPhoneFieldText(key) || isPhoneFieldText(label),
    is_address: isAddressFieldText(key) || isAddressFieldText(label),
  };
}

function shouldSkipInfoField(field) {
  if (!field) {
    return true;
  }
  if (INFO_APPLY_NOTE_KEYS.has(field.lowered)) {
    return true;
  }
  if (INFO_APPLY_BASE_KEYS.has(field.lowered)) {
    return true;
  }
  return false;
}

Page({
  data: {
    roleLabel: "游客",
    serviceId: 0,
    detail: null,
    loading: false,
    submitting: false,
    profile: null,
    applicantName: "",
    applicantPhone: "",
    applicantGender: "",
    applicantIdCard: "",
    applicantBirthDate: "",
    applicantAge: null,
    applicantIdentityMeta: "",
    applicantSummary: "实名信息待登记",
    userInfoExpanded: false,
    idCardPlaceholder: "不填则使用实名身份证号",
    note: "",
    formInputs: {},
    infoFormFields: [],
    certificateItems: [],
    visibleCertificateItems: [],
    certificateTotal: 0,
    certificateListExpanded: false,
    viewAllCertificateText: "查看全部证明",
    certificateStep: "choose",
    certificateSelectionOpen: true,
    selectedCertificateKey: "",
    selectedCertificateTitle: "",
    isRelationshipCertificate: false,
    relationOptions: DEFAULT_RELATION_OPTIONS,
    relationIndex: 0,
    relatedIdCardHint: "",
    relatedGenderNeedsManual: false,
    certStepChooseDone: false,
    certStepFillNow: false,
    certStepFillDone: false,
    certStepPreviewNow: false,
    certStepChooseClass: "now",
    certStepChooseText: "1",
    certStepFillClass: "todo",
    certStepFillText: "2",
    certStepPreviewClass: "todo",
    previewApplicantName: "",
    previewApplicantGender: "未知",
    previewApplicantIdCard: "",
    localSupportingPhotos: [],
    certGenderOptions: CERT_GENDER_OPTIONS,
    certGenderIndex: 2,
    relatedGenderIndex: 2,
    infoGenderIndexMap: {},
    addressRegionMap: {},
    addressRegionTextMap: {},
    addressVillageMap: {},
    addressVillageIndexMap: {},
    addressDetailMap: {},
    villageGroupOptions: VILLAGE_GROUP_OPTIONS,
    trainingTab: "job",
    selectedTrainingOptions: [],
    selectedJobKey: "",
    selectedJobTitle: "",
  },
  onLoad(options) {
    const id = Number(options?.id || 0);
    if (!id) {
      wx.showToast({ title: "服务参数无效", icon: "none" });
      wx.navigateBack({ delta: 1 });
      return;
    }
    this.setData({ serviceId: id });
  },
  isValidPhone(phone) {
    return isValidMobilePhone(phone);
  },
  decorateDetail(detail) {
    if (!detail) {
      return null;
    }
    const payload = detail.detail_payload || {};
    return {
      ...detail,
      contact_phone_text: formatPhoneDisplay(detail.contact_phone || ""),
      detail_payload: {
        ...payload,
        jobs: (payload.jobs || []).map((item) => ({
          ...item,
          contact_phone_text: formatPhoneDisplay(item.contact_phone || ""),
        })),
      },
    };
  },
  buildVisibleCertificateItems(items = [], expanded = false) {
    const rows = Array.isArray(items) ? items : [];
    if (expanded) {
      return rows;
    }
    const commonRows = COMMON_CERTIFICATE_ORDER
      .map((key) => rows.find((item) => item.key === key))
      .filter(Boolean);
    return commonRows.length ? commonRows : rows.slice(0, 6);
  },
  refreshCertificateDerivedState(extraData = {}) {
    const formInputs = { ...(extraData.formInputs || this.data.formInputs || {}) };
    const profile = this.data.profile || {};
    const profileIdCard = String(profile.id_card_number || "").trim();
    if (!String(formInputs.id_card || "").trim() && profileIdCard) {
      formInputs.id_card = profileIdCard;
    }
    const selectedCertificateKey =
      extraData.selectedCertificateKey !== undefined
        ? extraData.selectedCertificateKey
        : this.data.selectedCertificateKey;
    const isRelationshipCertificate =
      extraData.isRelationshipCertificate !== undefined
        ? extraData.isRelationshipCertificate
        : this.data.isRelationshipCertificate;
    const requestedStep =
      extraData.certificateStep !== undefined
        ? extraData.certificateStep
        : this.data.certificateStep || "choose";
    const relatedIdText = String(formInputs.related_id_card || "").trim();
    const relatedInfo = getIdCardInfo(relatedIdText);
    if (relatedInfo) {
      formInputs.related_gender = relatedInfo.gender;
    }
    const applicantIdCard = String(formInputs.id_card || profileIdCard || "").trim();
    const profileGender = normalizeKnownGenderText(profile.gender || "");
    const ownIdInfo = getIdCardInfo(applicantIdCard);
    if (profileGender) {
      formInputs.gender = profileGender;
    } else if (ownIdInfo) {
      formInputs.gender = ownIdInfo.gender;
    }
    const applicantName = String(
      extraData.applicantName !== undefined ? extraData.applicantName : this.data.applicantName || ""
    ).trim();
    const applicantGender =
      normalizeGenderText(formInputs.gender || this.data.applicantGender || "") ||
      ownIdInfo?.gender ||
      "未知";
    const applicantBirthDate = String(profile.birth_date || ownIdInfo?.birthDate || "").trim();
    const applicantAge =
      profile.age !== undefined && profile.age !== null && profile.age !== ""
        ? Number(profile.age)
        : ownIdInfo?.age ?? null;
    const applicantPhone =
      String(
        extraData.applicantPhone !== undefined ? extraData.applicantPhone : this.data.applicantPhone || ""
      ).trim() ||
      String(profile.phone || "").trim();
    const applicantIdentityMeta = applicantIdCard
      ? ownIdInfo
        ? `${applicantBirthDate || ownIdInfo.birthDate} · ${applicantAge} 岁 · ${applicantGender}`
        : "身份证号待确认"
      : "实名身份证号待带入";
    const applicantSummary = applicantName
      ? `${applicantName} · ${applicantGender} · ${
          applicantAge !== null && !Number.isNaN(applicantAge) ? `${applicantAge}岁 · ` : ""
        }${maskPhoneForSummary(applicantPhone)}`
      : "完成实名后自动带入本人信息";
    const hasSelection = !!String(selectedCertificateKey || "").trim();
    const relationshipReady =
      !isRelationshipCertificate ||
      (!!String(formInputs.related_name || "").trim() &&
        !!relatedInfo &&
        !!String(formInputs.relation_type || "").trim());
    const fillReady = hasSelection && relationshipReady;
    let certificateStep = hasSelection ? requestedStep : "choose";
    if (!["choose", "fill", "preview"].includes(certificateStep)) {
      certificateStep = hasSelection ? "fill" : "choose";
    }
    if (certificateStep === "preview" && !fillReady) {
      certificateStep = "fill";
    }
    const previewNow = certificateStep === "preview";
    this.setData({
      formInputs,
      applicantGender,
      applicantIdCard,
      applicantBirthDate,
      applicantAge,
      applicantIdentityMeta,
      applicantSummary,
      relatedIdCardHint: relatedIdText
        ? relatedInfo
          ? `已自动识别：${relatedInfo.gender} · ${relatedInfo.age} 岁 · ${relatedInfo.birthDate}`
          : "身份证号格式不正确，需手动选择性别"
        : "",
      relatedGenderNeedsManual: !!relatedIdText && !relatedInfo,
      certGenderIndex: certGenderToIndex(formInputs.gender),
      relatedGenderIndex: certGenderToIndex(formInputs.related_gender),
      certificateStep,
      certStepChooseDone: hasSelection,
      certStepFillNow: hasSelection && certificateStep === "fill",
      certStepFillDone: previewNow,
      certStepPreviewNow: previewNow,
      certStepChooseClass: hasSelection ? "done" : "now",
      certStepChooseText: hasSelection ? "✓" : "1",
      certStepFillClass: previewNow ? "done" : hasSelection ? "now" : "todo",
      certStepFillText: previewNow ? "✓" : "2",
      certStepPreviewClass: previewNow ? "now" : "todo",
      previewApplicantName: applicantName || "待填写姓名",
      previewApplicantGender: applicantGender || "待确认性别",
      previewApplicantIdCard: applicantIdCard,
    });
  },
  prefillFromProfile(profile) {
    if (!profile) {
      this.setData({
        profile: null,
        roleLabel: "游客",
        applicantName: "",
        applicantPhone: "",
        applicantGender: "",
        applicantIdCard: "",
        applicantBirthDate: "",
        applicantAge: null,
        applicantIdentityMeta: "",
        applicantSummary: "实名信息待登记",
        idCardPlaceholder: "不填则使用实名身份证号",
      });
      return;
    }
    const name = profile?.real_name || profile?.nickname || "";
    const phone = this.isValidPhone(profile?.phone || "") ? profile.phone : "";
    const gender = normalizeKnownGenderText(profile?.gender || "");
    const idCardNumber = String(profile?.id_card_number || "").trim();
    const idCardMasked = String(profile?.id_card_masked || "").trim();
    const idInfo = getIdCardInfo(idCardNumber);
    const applicantName = String(this.data.applicantName || "").trim() || name;
    const currentApplicantPhone = String(this.data.applicantPhone || "").trim();
    const applicantPhone = this.isValidPhone(currentApplicantPhone)
      ? currentApplicantPhone
      : formatPhoneInput(phone);
    const formInputs = { ...(this.data.formInputs || {}) };
    if (idCardNumber && !String(formInputs.id_card || "").trim()) {
      formInputs.id_card = idCardNumber;
    }
    if (!String(formInputs.gender || "").trim()) {
      formInputs.gender = gender || idInfo?.gender || "未知";
    }
    const nextData = {
      profile,
      roleLabel: getRoleText(profile?.role || "villager"),
      applicantName,
      applicantPhone,
      applicantGender: gender || idInfo?.gender || "未知",
      applicantSummary: applicantName
        ? `${applicantName} · ${gender || idInfo?.gender || "未知"} · ${
            profile?.age !== undefined && profile?.age !== null && profile?.age !== ""
              ? `${profile.age}岁 · `
              : idInfo
                ? `${idInfo.age}岁 · `
                : ""
          }${maskPhoneForSummary(profile?.phone || applicantPhone)}`
        : "完成实名后自动带入本人信息",
      applicantIdCard: idCardNumber,
      applicantBirthDate: String(profile?.birth_date || idInfo?.birthDate || "").trim(),
      applicantAge:
        profile?.age !== undefined && profile?.age !== null && profile?.age !== ""
          ? Number(profile.age)
          : idInfo?.age ?? null,
      applicantIdentityMeta: idCardNumber
        ? `${profile?.birth_date || idInfo?.birthDate || "生日待确认"} · ${
            profile?.age !== undefined && profile?.age !== null && profile?.age !== ""
              ? profile.age
              : idInfo?.age || "年龄待确认"
          } 岁 · ${gender || idInfo?.gender || "性别待确认"}`
        : "实名身份证号待带入",
      idCardPlaceholder: idCardNumber ? "已从实名信息带入" : idCardMasked ? `默认使用 ${idCardMasked}` : "不填则使用实名身份证号",
    };
    let shouldSyncFormInputs = false;
    if (
      Object.prototype.hasOwnProperty.call(formInputs, "name") &&
      !String(formInputs.name || "").trim() &&
      applicantName
    ) {
      formInputs.name = applicantName;
      shouldSyncFormInputs = true;
    }
    if (
      Object.prototype.hasOwnProperty.call(formInputs, "phone") &&
      !String(formInputs.phone || "").trim() &&
      applicantPhone
    ) {
      formInputs.phone = applicantPhone;
      shouldSyncFormInputs = true;
    }
    if (
      Object.prototype.hasOwnProperty.call(formInputs, "gender") &&
      (gender || idInfo?.gender)
    ) {
      formInputs.gender = gender || idInfo.gender;
      shouldSyncFormInputs = true;
    }
    if (idCardNumber) {
      formInputs.id_card = idCardNumber;
      shouldSyncFormInputs = true;
    }
    if (shouldSyncFormInputs) {
      nextData.formInputs = formInputs;
    }
    this.setData(nextData, () => {
      this.refreshCertificateDerivedState(nextData);
    });
  },
  async refreshProfile() {
    const profile = await resolveViewerProfile({ refresh: true, silent: true });
    this.prefillFromProfile(profile);
    return true;
  },
  async onShow() {
    const ok = await this.refreshProfile();
    if (!ok) {
      return;
    }
    const currentDetailId = Number(this.data.detail?.id || 0);
    if (!currentDetailId || currentDetailId !== Number(this.data.serviceId || 0)) {
      await this.loadDetail();
    }
  },
  initFormState(detail) {
    const payload = detail?.detail_payload || {};
    const formInputs = {};
    const infoGenderIndexMap = {};
    const addressRegionMap = {};
    const addressRegionTextMap = {};
    const addressVillageMap = {};
    const addressVillageIndexMap = {};
    const addressDetailMap = {};
    const infoFormFields = [];
    const detailType = detail?.detail_type;
    if (detailType === "info_apply") {
      const fields = payload.form_fields || [];
      fields.forEach((item) => {
        const field = normalizeInfoField(item);
        if (shouldSkipInfoField(field)) {
          return;
        }
        infoFormFields.push(field);
        if (field.is_gender) {
          formInputs[field.key] = "未知";
          infoGenderIndexMap[field.key] = 2;
        } else if (field.is_address) {
          formInputs[field.key] = "";
          addressRegionMap[field.key] = [];
          addressRegionTextMap[field.key] = "";
          addressVillageMap[field.key] = "";
          addressVillageIndexMap[field.key] = 0;
          addressDetailMap[field.key] = "";
        } else {
          formInputs[field.key] = "";
        }
      });
    }
    if (detailType === "certificate") {
      formInputs.name = this.data.applicantName || "";
      formInputs.gender = normalizeGenderText(this.data.profile?.gender || this.data.applicantGender || "") || "未知";
      formInputs.id_card = "";
      formInputs.job_desc = "";
      formInputs.related_name = "";
      formInputs.related_gender = "未知";
      formInputs.related_id_card = "";
      formInputs.relation_type = "";
      formInputs.spouse = "";
      formInputs.spouse_id_card = "";
      formInputs.marital_status = "";
      formInputs.home_address = "";
    }
    if (detailType === "employment_training") {
      formInputs.name = this.data.applicantName || "";
      formInputs.phone = this.data.applicantPhone || "";
      formInputs.remark = "";
    }
    const certList = (payload.certificates || []).map(decorateCertificateOption);
    const jobs = payload.jobs || [];
    const firstJob = jobs[0] || {};
    const visibleCertificateItems = this.buildVisibleCertificateItems(certList, false);
    this.setData({
      formInputs,
      infoFormFields,
      certificateItems: certList,
      visibleCertificateItems,
      certificateTotal: certList.length,
      certificateListExpanded: false,
      viewAllCertificateText: `查看全部证明（共 ${certList.length} 种）`,
      certificateStep: "choose",
      certificateSelectionOpen: detailType === "certificate",
      selectedCertificateKey: "",
      selectedCertificateTitle: "",
      isRelationshipCertificate: false,
      relationOptions: DEFAULT_RELATION_OPTIONS,
      relationIndex: 0,
      relatedIdCardHint: "",
      relatedGenderNeedsManual: false,
      localSupportingPhotos: [],
      certGenderIndex: certGenderToIndex(formInputs.gender),
      relatedGenderIndex: certGenderToIndex(formInputs.related_gender),
      infoGenderIndexMap,
      addressRegionMap,
      addressRegionTextMap,
      addressVillageMap,
      addressVillageIndexMap,
      addressDetailMap,
      selectedJobKey: firstJob.job_key || "",
      selectedJobTitle: firstJob.title || "",
      selectedTrainingOptions: [],
      trainingTab: "job",
    }, () => {
      if (detailType === "certificate") {
        this.refreshCertificateDerivedState({ formInputs, selectedCertificateKey: "" });
      }
    });
  },
  async loadDetail() {
    this.setData({ loading: true });
    try {
      const rawDetail = await request({ path: `/gov/services/${this.data.serviceId}` });
      if (rawDetail?.service_key === "employment_training" || rawDetail?.detail_type === "employment_training") {
        wx.redirectTo({ url: "/pages/services/training/training" });
        return;
      }
      const detail = this.decorateDetail(rawDetail);
      this.setData({ detail }, () => {
        this.initFormState(detail);
      });
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
    } finally {
      this.setData({ loading: false });
    }
  },
  async ensureCanApply() {
    return ensureVerifiedVillager({
      title: "政务办理需登记身份信息",
      content: "提交证明或政务申请前，请先登录并完成基础实名登记。",
    });
  },
  onApplicantNameInput(e) {
    const applicantName = e.detail.value;
    const formInputs = { ...(this.data.formInputs || {}) };
    const nextData = { applicantName };
    if (Object.prototype.hasOwnProperty.call(formInputs, "name")) {
      formInputs.name = applicantName;
      nextData.formInputs = formInputs;
    }
    this.setData(nextData, () => {
      this.refreshCertificateDerivedState(nextData);
    });
  },
  onApplicantPhoneInput(e) {
    const applicantPhone = formatPhoneInput(e.detail.value);
    const formInputs = { ...(this.data.formInputs || {}) };
    const nextData = { applicantPhone };
    if (Object.prototype.hasOwnProperty.call(formInputs, "phone")) {
      formInputs.phone = applicantPhone;
      nextData.formInputs = formInputs;
    }
    this.setData(nextData, () => {
      this.refreshCertificateDerivedState(nextData);
    });
  },
  onNoteInput(e) {
    this.setData({ note: e.detail.value });
  },
  onFormInput(e) {
    const key = e.currentTarget.dataset.key;
    if (!key) {
      return;
    }
    const field = (this.data.infoFormFields || []).find((item) => item.key === key);
    const formInputs = { ...(this.data.formInputs || {}) };
    formInputs[key] = field?.is_phone ? formatPhoneInput(e.detail.value) : e.detail.value;
    this.setData({ formInputs }, () => {
      if (this.data.detail?.detail_type === "certificate") {
        this.refreshCertificateDerivedState({ formInputs });
      }
    });
  },
  onAddressRegionChange(e) {
    const key = String(e.currentTarget.dataset.key || "").trim();
    if (!key) {
      return;
    }
    const region = e.detail.value || [];
    const addressRegionMap = { ...(this.data.addressRegionMap || {}) };
    const addressRegionTextMap = { ...(this.data.addressRegionTextMap || {}) };
    addressRegionMap[key] = region;
    addressRegionTextMap[key] = region.filter(Boolean).join(" ");
    this.setData({ addressRegionMap, addressRegionTextMap });
  },
  onAddressVillageChange(e) {
    const key = String(e.currentTarget.dataset.key || "").trim();
    if (!key) {
      return;
    }
    const index = Number(e.detail.value || 0);
    const safeIndex =
      Number.isNaN(index) || index < 0 || index >= VILLAGE_GROUP_OPTIONS.length ? 0 : index;
    const addressVillageIndexMap = { ...(this.data.addressVillageIndexMap || {}) };
    const addressVillageMap = { ...(this.data.addressVillageMap || {}) };
    addressVillageIndexMap[key] = safeIndex;
    addressVillageMap[key] =
      safeIndex > 0 ? VILLAGE_GROUP_OPTIONS[safeIndex] : "";
    this.setData({ addressVillageIndexMap, addressVillageMap });
  },
  onAddressDetailInput(e) {
    const key = String(e.currentTarget.dataset.key || "").trim();
    if (!key) {
      return;
    }
    const value = e.detail.value;
    const formInputs = { ...(this.data.formInputs || {}) };
    const addressDetailMap = { ...(this.data.addressDetailMap || {}) };
    formInputs[key] = value;
    addressDetailMap[key] = value;
    this.setData({ formInputs, addressDetailMap });
  },
  onCertificateGenderChange(e) {
    const index = Number(e.detail.value);
    const safeIndex =
      Number.isNaN(index) || index < 0 || index >= CERT_GENDER_OPTIONS.length ? 2 : index;
    const formInputs = { ...(this.data.formInputs || {}) };
    formInputs.gender = CERT_GENDER_OPTIONS[safeIndex];
    this.setData({
      certGenderIndex: safeIndex,
      formInputs,
    }, () => {
      this.refreshCertificateDerivedState({ formInputs });
    });
  },
  onCertificateRelatedGenderChange(e) {
    const index = Number(e.detail.value);
    const safeIndex =
      Number.isNaN(index) || index < 0 || index >= CERT_GENDER_OPTIONS.length ? 2 : index;
    const formInputs = { ...(this.data.formInputs || {}) };
    formInputs.related_gender = CERT_GENDER_OPTIONS[safeIndex];
    this.setData({
      relatedGenderIndex: safeIndex,
      formInputs,
    }, () => {
      this.refreshCertificateDerivedState({ formInputs });
    });
  },
  onRelationChange(e) {
    const options = this.data.relationOptions || DEFAULT_RELATION_OPTIONS;
    const index = Number(e.detail.value);
    const safeIndex =
      Number.isNaN(index) || index < 0 || index >= options.length ? 0 : index;
    const formInputs = { ...(this.data.formInputs || {}) };
    formInputs.relation_type = safeIndex > 0 ? options[safeIndex] : "";
    this.setData({
      relationIndex: safeIndex,
      formInputs,
    }, () => {
      this.refreshCertificateDerivedState({ formInputs });
    });
  },
  onInfoGenderChange(e) {
    const key = String(e.currentTarget.dataset.key || "").trim();
    if (!key) {
      return;
    }
    const index = Number(e.detail.value);
    const safeIndex =
      Number.isNaN(index) || index < 0 || index >= CERT_GENDER_OPTIONS.length ? 2 : index;
    const formInputs = { ...(this.data.formInputs || {}) };
    const infoGenderIndexMap = { ...(this.data.infoGenderIndexMap || {}) };
    formInputs[key] = CERT_GENDER_OPTIONS[safeIndex];
    infoGenderIndexMap[key] = safeIndex;
    this.setData({ formInputs, infoGenderIndexMap });
  },
  chooseCertificate(e) {
    const key = e.currentTarget.dataset.key;
    const title = e.currentTarget.dataset.title;
    if (!key) {
      return;
    }
    const isRelationship = isRelationshipCertificateKey(key);
    const relationOptions = getRelationOptionsByCertificateKey(key);
    const formInputs = { ...(this.data.formInputs || {}) };
    const currentRelation = String(formInputs.relation_type || "").trim();
    const relationIndex = relationOptions.indexOf(currentRelation);
    if (relationIndex < 0) {
      formInputs.relation_type = "";
    }
    if (isRelationship) {
      formInputs.job_desc = "";
    } else {
      formInputs.related_name = "";
      formInputs.related_gender = "未知";
      formInputs.related_id_card = "";
      formInputs.relation_type = "";
    }
    this.setData({
      selectedCertificateKey: key,
      selectedCertificateTitle: title || "",
      certificateStep: "fill",
      certificateSelectionOpen: false,
      isRelationshipCertificate: isRelationship,
      relationOptions,
      relationIndex: relationIndex > 0 ? relationIndex : 0,
      relatedGenderIndex: isRelationship ? certGenderToIndex(formInputs.related_gender) : 2,
      formInputs,
    }, () => {
      this.refreshCertificateDerivedState({
        formInputs,
        selectedCertificateKey: key,
        isRelationshipCertificate: isRelationship,
        certificateStep: "fill",
      });
    });
  },
  changeCertificate() {
    this.setData({
      certificateStep: "choose",
      certificateSelectionOpen: true,
    }, () => {
      this.refreshCertificateDerivedState({ certificateStep: "choose" });
    });
  },
  toggleCertificateList() {
    const certificateListExpanded = !this.data.certificateListExpanded;
    const visibleCertificateItems = this.buildVisibleCertificateItems(
      this.data.certificateItems,
      certificateListExpanded
    );
    this.setData({
      certificateListExpanded,
      visibleCertificateItems,
      viewAllCertificateText: certificateListExpanded
        ? "收起常用证明"
        : `查看全部证明（共 ${this.data.certificateTotal} 种）`,
    });
  },
  toggleUserInfo() {
    this.setData({
      userInfoExpanded: !this.data.userInfoExpanded,
    });
  },
  buildCertificateExtraFields(options = {}) {
    const silent = !!options.silent;
    if (!this.data.selectedCertificateKey) {
      if (!silent) {
        wx.showToast({ title: "请选择证明类型", icon: "none" });
      }
      return null;
    }
    const formInputs = { ...(this.data.formInputs || {}) };
    const applicantIdCard = String(formInputs.id_card || this.data.profile?.id_card_number || "").trim();
    const ownIdInfo = getIdCardInfo(applicantIdCard);
    if (applicantIdCard && !ownIdInfo) {
      if (!silent) {
        wx.showToast({ title: "本人身份证号格式不正确", icon: "none" });
      }
      return null;
    }
    const profileGender = normalizeKnownGenderText(this.data.profile?.gender || "");
    const ownGender = profileGender || ownIdInfo?.gender || formInputs.gender || "未知";
    const extra = {
      certificate_key: this.data.selectedCertificateKey,
      certificate_title: this.data.selectedCertificateTitle,
      name: formInputs.name || this.data.applicantName || "",
      gender: ownGender,
    };
    if (applicantIdCard) {
      extra.id_card = applicantIdCard;
    }
    if (this.data.isRelationshipCertificate) {
      if (!String(formInputs.related_name || "").trim()) {
        if (!silent) {
          wx.showToast({ title: "请填写对方姓名", icon: "none" });
        }
        return null;
      }
      const relatedInfo = getIdCardInfo(formInputs.related_id_card);
      if (!relatedInfo) {
        if (!silent) {
          wx.showToast({ title: "请填写对方正确的身份证号", icon: "none" });
        }
        return null;
      }
      if (!String(formInputs.relation_type || "").trim()) {
        if (!silent) {
          wx.showToast({ title: "请选择关系类型", icon: "none" });
        }
        return null;
      }
      extra.related_name = String(formInputs.related_name || "").trim();
      extra.related_gender = relatedInfo.gender || formInputs.related_gender || "未知";
      extra.related_id_card = String(formInputs.related_id_card || "").trim();
      extra.relation_type = String(formInputs.relation_type || "").trim();
    } else if (String(formInputs.job_desc || "").trim()) {
      extra.job_desc = String(formInputs.job_desc || "").trim();
    }
    return extra;
  },
  async goCertificatePreview() {
    const ok = await this.ensureCanApply();
    if (!ok) {
      return;
    }
    const extra = this.buildCertificateExtraFields();
    if (!extra) {
      return;
    }
    this.setData({ certificateStep: "preview" }, () => {
      this.refreshCertificateDerivedState({ certificateStep: "preview" });
      if (typeof wx.pageScrollTo === "function") {
        wx.pageScrollTo({ scrollTop: 0, duration: 180 });
      }
    });
  },
  editCertificateFromPreview() {
    this.setData({ certificateStep: "fill" }, () => {
      this.refreshCertificateDerivedState({ certificateStep: "fill" });
    });
  },
  switchTrainingTab(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab || tab === this.data.trainingTab) {
      return;
    }
    this.setData({ trainingTab: tab });
  },
  onTrainingOptionsChange(e) {
    this.setData({ selectedTrainingOptions: e.detail.value || [] });
  },
  chooseJob(e) {
    const jobKey = e.currentTarget.dataset.jobKey;
    const jobTitle = e.currentTarget.dataset.jobTitle;
    if (!jobKey) {
      return;
    }
    this.setData({
      selectedJobKey: jobKey,
      selectedJobTitle: jobTitle || "",
    });
  },
  makePhoneCall() {
    const phone = compactPhone(this.data.detail?.contact_phone || "");
    if (!phone || !/^\d{6,20}$/.test(phone)) {
      wx.showToast({ title: "联系方式待完善", icon: "none" });
      return;
    }
    dialPhoneNumber(phone, { emptyToastTitle: "联系方式待完善" });
  },
  previewDetailPhoto(e) {
    const current = e.currentTarget.dataset.current || "";
    const urls = this.data.detail?.detail_payload?.image_urls || [];
    if (!current || !urls.length) {
      return;
    }
    wx.previewImage({ current, urls });
  },
  async chooseSupportingPhotos() {
    const ok = await this.ensureCanApply();
    if (!ok) {
      return;
    }
    const remain = 9 - (this.data.localSupportingPhotos || []).length;
    if (remain <= 0) {
      wx.showToast({ title: "最多上传9张", icon: "none" });
      return;
    }
    wx.chooseImage({
      count: remain,
      sizeType: ["compressed"],
      sourceType: ["album", "camera"],
      success: (res) => {
        const paths = (res?.tempFilePaths || []).filter(Boolean);
        this.setData({
          localSupportingPhotos: (this.data.localSupportingPhotos || []).concat(paths).slice(0, 9),
        });
      },
      fail: (err) => {
        if (String(err?.errMsg || "").includes("cancel")) {
          return;
        }
        wx.showToast({ title: "选择图片失败，请重试", icon: "none" });
      },
    });
  },
  removeSupportingPhoto(e) {
    const index = Number(e.currentTarget.dataset.index);
    const photos = [...(this.data.localSupportingPhotos || [])];
    if (Number.isNaN(index) || index < 0 || index >= photos.length) {
      return;
    }
    photos.splice(index, 1);
    this.setData({ localSupportingPhotos: photos });
  },
  previewSupportingPhoto(e) {
    const current = e.currentTarget.dataset.current || "";
    const urls = this.data.localSupportingPhotos || [];
    if (!current || !urls.length) {
      return;
    }
    wx.previewImage({ current, urls });
  },
  openExternalService() {
    const payload = this.data.detail?.detail_payload || {};
    const appName = payload.app_name || this.data.detail?.title || "政务服务";
    const confirmText = payload.confirm_text || `即将打开“${appName}”小程序`;
    wx.showModal({
      title: "跳转提示",
      content: confirmText,
      confirmText: "允许",
      success: (res) => {
        if (!res.confirm) {
          return;
        }
        wx.showToast({
          title: `请在微信中打开“${appName}”`,
          icon: "none",
        });
      },
    });
  },
  async submitApplication(selectedOption, extraFields, supportingPhotoUrls = [], options = {}) {
    const applicantName = String(this.data.applicantName || "").trim();
    const applicantPhone = compactPhone(this.data.applicantPhone);
    if (!applicantName) {
      wx.showToast({ title: "请填写申请人姓名", icon: "none" });
      return false;
    }
    if (applicantPhone && !this.isValidPhone(applicantPhone)) {
      wx.showToast({ title: "手机号格式不正确", icon: "none" });
      return false;
    }
    const manageSubmitting = options.manageSubmitting !== false;
    if (manageSubmitting) {
      this.setData({ submitting: true });
    }
    try {
      await request({
        path: "/gov/applications",
        method: "POST",
        timeout: 60000,
        data: {
          service_id: this.data.serviceId,
          applicant_name: applicantName,
          applicant_phone: applicantPhone,
          selected_option: selectedOption || "",
          note: this.data.note || "",
          supporting_photo_urls: supportingPhotoUrls || [],
          extra_fields: extraFields || {},
        },
      });
      wx.showToast({ title: "申请已提交", icon: "success" });
      this.setData({ note: "", localSupportingPhotos: [] });
      wx.navigateTo({
        url: `/pages/result/result?status=success&title=${encodeURIComponent(selectedOption || this.data.detail?.title || "政务申请")}`,
      });
      return true;
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
      return false;
    } finally {
      if (manageSubmitting) {
        this.setData({ submitting: false });
      }
    }
  },
  async submitCertificate() {
    const ok = await this.ensureCanApply();
    if (!ok) {
      return;
    }
    if (this.data.submitting) {
      return;
    }
    if (this.data.certificateStep !== "preview") {
      await this.goCertificatePreview();
      return;
    }
    const extra = this.buildCertificateExtraFields();
    if (!extra) {
      return;
    }
    this.setData({ submitting: true });
    let supportingPhotoUrls = [];
    try {
      supportingPhotoUrls = await uploadImages(
        this.data.localSupportingPhotos || [],
        "villager",
        "gov_apply"
      );
    } catch (err) {
      wx.showToast({ title: getErrorMessage(err), icon: "none" });
      this.setData({ submitting: false });
      return;
    }
    try {
      await this.submitApplication(
        `开具证明：${this.data.selectedCertificateTitle || this.data.selectedCertificateKey}`,
        extra,
        supportingPhotoUrls,
        { manageSubmitting: false }
      );
    } finally {
      this.setData({ submitting: false });
    }
  },
  async submitInfoApply() {
    const ok = await this.ensureCanApply();
    if (!ok) {
      return;
    }
    if (this.data.submitting) {
      return;
    }
    const detail = this.data.detail || {};
    const extraFields = { ...(this.data.formInputs || {}) };
    (this.data.infoFormFields || []).forEach((field) => {
      if (!field?.is_address) {
        return;
      }
      extraFields[field.key] = buildAddressText(
        this.data.addressRegionMap?.[field.key] || [],
        this.data.addressVillageMap?.[field.key] || "",
        this.data.addressDetailMap?.[field.key] || this.data.formInputs?.[field.key] || ""
      );
    });
    this.submitApplication(
      `${detail.title}申请`,
      extraFields
    );
  },
  async submitTrainingApply() {
    const ok = await this.ensureCanApply();
    if (!ok) {
      return;
    }
    if (this.data.submitting) {
      return;
    }
    const payload = this.data.detail?.detail_payload || {};
    if (this.data.trainingTab === "job") {
      if (!Array.isArray(payload.jobs) || !payload.jobs.length) {
        wx.showToast({ title: "暂时没有就业信息", icon: "none" });
        return;
      }
      if (!this.data.selectedJobKey) {
        wx.showToast({ title: "请选择岗位", icon: "none" });
        return;
      }
      const job = (payload.jobs || []).find((item) => item.job_key === this.data.selectedJobKey) || {};
      this.submitApplication(
        `就业报名：${this.data.selectedJobTitle || job.title || this.data.selectedJobKey}`,
        {
          apply_type: "job",
          job_key: this.data.selectedJobKey,
          job_title: this.data.selectedJobTitle || job.title || "",
          ...this.data.formInputs,
        }
      );
      return;
    }
    const options = this.data.selectedTrainingOptions || [];
    if (!options.length) {
      wx.showToast({ title: "请至少选择一个培训类型", icon: "none" });
      return;
    }
    this.submitApplication(
      `培训申请：${options.join("、")}`,
      {
        apply_type: "training",
        training_options: options,
        ...this.data.formInputs,
      }
    );
  },
});
