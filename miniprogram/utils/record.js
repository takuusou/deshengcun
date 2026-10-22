const { formatPhoneDisplay } = require("./phone");

const RECORD_STATUS_TEXT_MAP = Object.freeze({
  pending: "待处理",
  processing: "处理中",
  resolved: "已处理",
  rejected: "已驳回",
  closed: "已取消",
});

const RECORD_PENDING_STATUS_SET = new Set(["pending", "processing"]);
const RECORD_RESULT_STATUS_SET = new Set(["resolved", "rejected", "closed"]);
const RECORD_CANCELABLE_STATUS_SET = new Set(["pending", "processing"]);

const RECORD_EXTRA_FIELD_LABEL_MAP = Object.freeze({
  certificatekey: "证明类型",
  certificatetitle: "证明类型",
  name: "姓名",
  realname: "姓名",
  applicantname: "姓名",
  gender: "性别",
  sex: "性别",
  性别: "性别",
  idcard: "身份证号",
  idcardnumber: "身份证号",
  spouse: "配偶姓名",
  spousename: "配偶姓名",
  spouseidcard: "配偶身份证号",
  relatedname: "对方姓名",
  relatedgender: "对方性别",
  relatedidcard: "对方身份证号",
  relationtype: "关系类型",
  phone: "联系方式",
  mobile: "联系方式",
  contactphone: "联系方式",
  contactmobile: "联系方式",
  contactname: "联系人",
  direction: "迁移方向",
  jobdesc: "证明事由",
  reason: "办理事由",
  purpose: "办理用途",
  homeaddress: "住址",
  address: "地址",
  applytype: "申请类型",
  requesttype: "诉求类型",
  trainingoptions: "培训方向",
  jobtitle: "岗位名称",
  jobkey: "岗位名称",
  note: "补充说明",
  remark: "补充说明",
});

const DEFAULT_RECORD_EXTRA_SKIP_KEYS = new Set([
  "certificatekey",
  "certificatetitle",
  "name",
  "realname",
  "applicantname",
  "phone",
  "mobile",
  "contactphone",
  "contactmobile",
  "contact",
  "supportingphotourls",
  "note",
  "remark",
]);

const CERTIFICATE_VALUE_MAP = Object.freeze({
  relationship: "关系证明",
  single_child_loss: "《独生子女父母光荣证》遗失证明",
  no_children: "无子女证明",
  electric_name: "电表更名证明",
  charger_install: "个人充电桩安装同意书",
  kinship_2nd: "亲属关系证明（第二继承人）",
  kinship_1st: "亲属关系证明（第一继承人）",
  marriage_status: "婚育情况证明",
  employment: "从业证明",
  foundling_case: "捡拾弃婴（儿童）情况证明",
  electric_split: "电表分户证明",
  electric_new: "电表上户证明",
  spouse_relation: "夫妻关系证明",
  family_difficulty: "家庭困难证明",
  household: "住所（经营场所）证明",
});

const JOB_VALUE_MAP = Object.freeze({
  kitchen_helper: "后厨帮工",
  warehouse_packer: "打包工",
});

const APPLY_TYPE_VALUE_MAP = Object.freeze({
  job: "就业报名",
  training: "培训申请",
});

const REQUEST_TYPE_VALUE_MAP = Object.freeze({
  complaint: "问题投诉",
  service: "服务需求",
});

function formatDateText(value, maxLength = 10) {
  const text = String(value || "").trim();
  if (!text) {
    return "";
  }
  const limit = Number(maxLength || 0);
  if (limit > 0 && text.length >= limit) {
    return text.slice(0, limit);
  }
  return text;
}

function buildHandledMeta(handledBy, handledAt) {
  const byText = String(handledBy || "").trim();
  if (!byText) {
    return "";
  }
  const dateText = formatDateText(handledAt);
  return `${byText}${dateText ? ` | ${dateText}` : ""}`;
}

function normalizeRecordFieldKey(key) {
  const text = String(key || "").trim();
  if (!text) {
    return "";
  }
  if (text === "性别") {
    return "性别";
  }
  return text.toLowerCase().replace(/[\s_-]/g, "");
}

function normalizeRecordFieldValue(value, options = {}) {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item == null ? "" : item).trim())
      .filter(Boolean)
      .join("、");
  }
  if (value && typeof value === "object") {
    return options.objectFallback || "";
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  return String(value == null ? "" : value).trim();
}

function translateRecordFieldValue(normalizedKey, value, options = {}) {
  const text = String(value == null ? "" : value).trim();
  if (!text) {
    return "";
  }
  if (normalizedKey === "certificatekey" || normalizedKey === "certificatetitle") {
    return CERTIFICATE_VALUE_MAP[text] || text;
  }
  if (normalizedKey === "jobkey" || normalizedKey === "jobtitle") {
    return JOB_VALUE_MAP[text] || text;
  }
  if (normalizedKey === "applytype") {
    return APPLY_TYPE_VALUE_MAP[text] || text;
  }
  if (normalizedKey === "requesttype") {
    return REQUEST_TYPE_VALUE_MAP[text] || text;
  }
  if (options.formatPhone !== false) {
    if (
      normalizedKey === "phone" ||
      normalizedKey === "mobile" ||
      normalizedKey === "contactphone" ||
      normalizedKey === "contactmobile"
    ) {
      return formatPhoneDisplay(text);
    }
  }
  return text;
}

function shouldHideAsciiLikeValue(normalizedKey, value) {
  if (RECORD_EXTRA_FIELD_LABEL_MAP[normalizedKey]) {
    return false;
  }
  return /^[A-Za-z0-9_./:-]+$/.test(String(value || "").trim());
}

function buildRecordExtraRows(extraFields, options = {}) {
  if (!extraFields || typeof extraFields !== "object" || Array.isArray(extraFields)) {
    return [];
  }
  const rows = [];
  const skipKeys =
    options.skipKeys instanceof Set
      ? options.skipKeys
      : new Set(Array.isArray(options.skipKeys) ? options.skipKeys : []);
  const objectFallback = options.objectFallback || "";
  const limit = Number(options.limit || 0);

  Object.keys(extraFields).forEach((key) => {
    const normalizedKey = normalizeRecordFieldKey(key);
    if (!normalizedKey || skipKeys.has(normalizedKey)) {
      return;
    }
    const value = translateRecordFieldValue(
      normalizedKey,
      normalizeRecordFieldValue(extraFields[key], { objectFallback }),
      options
    );
    if (!value || shouldHideAsciiLikeValue(normalizedKey, value)) {
      return;
    }
    rows.push({
      key,
      label: RECORD_EXTRA_FIELD_LABEL_MAP[normalizedKey] || "补充信息",
      value,
    });
  });

  return limit > 0 ? rows.slice(0, limit) : rows;
}

function buildRecordHint(status, sourceText) {
  if (status === "pending") {
    return `${sourceText}已提交，等待村委处理。`;
  }
  if (status === "processing") {
    return `${sourceText}已进入办理流程，可持续查看进度。`;
  }
  if (status === "rejected") {
    return `${sourceText}已退回，请查看处理说明。`;
  }
  if (status === "closed") {
    return `${sourceText}已取消，请查看最终说明。`;
  }
  if (status === "resolved") {
    return `${sourceText}已处理，可查看结果回执。`;
  }
  return `${sourceText}处理中，请留意后续通知。`;
}

function buildResultPreview(text) {
  const content = String(text || "").trim();
  if (content) {
    return content;
  }
  return "暂无办理结果，点击查看详细信息。";
}

module.exports = {
  RECORD_STATUS_TEXT_MAP,
  RECORD_PENDING_STATUS_SET,
  RECORD_RESULT_STATUS_SET,
  RECORD_CANCELABLE_STATUS_SET,
  DEFAULT_RECORD_EXTRA_SKIP_KEYS,
  formatDateText,
  buildHandledMeta,
  buildRecordExtraRows,
  buildRecordHint,
  buildResultPreview,
};
