const ERROR_MESSAGE_MAP = {
  invalid_admin_credentials: "账号或密码不正确。",
  admin_account_locked: "连续失败次数过多，后台账号已暂时锁定。",
  admin_account_disabled: "当前后台账号已停用。",
  admin_account_not_found: "该干部还没有创建后台账号，请先创建后台账号。",
  admin_authorization_disabled: "当前干部授权已停用，请联系管理员。",
  admin_mfa_already_configured: "双因素认证已经启用；如需重置，请联系超级管理员重置账号安全设置。",
  admin_write_forbidden: "当前账号只有查看权限，不能新建或修改内容。",
  admin_super_required: "只有超级管理员可以管理干部账号和重置密码。",
  weak_admin_password: "后台密码至少 12 位，并包含至少两类字符。",
  admin_login_name_exists: "这个后台登录名已被占用，请换一个登录名。",
  invalid_admin_role_key: "所选后台角色不符合该干部授权级别。",
  login_required: "登录状态已失效，请重新登录。",
  invalid_metric_payload: "请把数字概览里的指标名称和值填写完整。",
  invalid_open_item_payload: "请先填写公开条目标题。",
  invalid_open_section: "请选择正确的公开栏目。",
  notice_not_found: "这条通知已不存在或已被删除。",
  meeting_not_found: "这条会议记录已不存在或已被删除。",
  training_program_not_found: "这条就业培训已不存在或已被删除。",
  invalid_training_program_title: "请先填写培训标题。",
  invalid_training_date: "培训日期格式不正确，请使用日期选择器重新选择。",
  invalid_training_date_range: "培训结束日不能早于报名截止日。",
  training_signup_closed: "该培训已停止报名。",
  open_item_not_found: "这条公开条目已不存在或已被删除。",
  audit_log_not_found: "这条审计日志已不存在或已被删除。",
  villager_identity_not_found: "这条村民身份登记记录不存在。",
  roster_not_ready: "当前未导入有效户籍白名单，请先导入名单后再继续。",
  identity_not_in_roster: "身份信息校验失败。",
  id_card_already_verified: "身份证号已被验证，请联系管理员处理。",
  certificate_duplicate_submission: "同一份证明已提交，请勿重复创建。",
  gov_application_duplicate_submission: "相同申请刚刚已经提交，请勿重复创建。",
  certificate_daily_limit_reached: "当天最多只能提交 5 份不同证明，请明天再试。",
  invalid_request_status_transition: "当前事项已经进入后续状态，不能退回到之前的状态。",
  invalid_gov_status_transition: "当前申请已经进入后续状态，不能退回到之前的状态。",
  unsupported_image_type: "只支持 JPG、PNG、WEBP、HEIC 图片。",
  image_content_mismatch: "图片内容与文件格式不一致，请重新选择原始图片。",
  empty_image_file: "所选图片为空，请重新选择。",
  image_file_too_large: "单张图片不能超过 8MB。",
  upload_store_failed: "图片上传失败，请联系管理员检查对象存储配置。",
};

const FIELD_LABEL_MAP = {
  title: "标题",
  content: "正文",
  publisher: "发布人",
  topic: "会议主题",
  summary: "内容",
  owner: "主持/记录人",
  meeting_time: "会议时间",
  section_key: "公开栏目",
  metric_label: "指标名称",
  metric_value: "指标值",
  login_name: "登录名",
  display_name: "显示名",
  password: "密码",
  new_password: "新密码",
  role_key: "后台角色",
};

function formatValidationItem(item) {
  const loc = Array.isArray(item?.loc) ? item.loc : [];
  const fieldKey = String(loc[loc.length - 1] || "").trim();
  const fieldLabel = FIELD_LABEL_MAP[fieldKey] || fieldKey;
  const message = String(item?.msg || "").trim();
  if (!fieldLabel) {
    return message || "输入内容不合法。";
  }
  if (!message) {
    return `${fieldLabel}填写不合法。`;
  }
  return `${fieldLabel}：${message}`;
}

export function extractApiError(error, fallback = "操作失败，请稍后重试。") {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map(formatValidationItem).join("；");
  }
  if (typeof detail === "string" && detail.trim()) {
    return ERROR_MESSAGE_MAP[detail.trim()] || detail.trim();
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  const message = String(error?.message || "").trim();
  return ERROR_MESSAGE_MAP[message] || message || fallback;
}

export function hasText(value) {
  return !!String(value || "").trim();
}

export function parseLocalDateTimeText(value) {
  const text = String(value || "").trim();
  if (!text) {
    return null;
  }
  const nativeTimestamp = Date.parse(text);
  if (!Number.isNaN(nativeTimestamp)) {
    return new Date(nativeTimestamp);
  }

  const normalized = text.replace(/\s+/g, " ");
  const chineseMatch = normalized.match(
    /^(\d{4})-(\d{2})-(\d{2})\s*(上午|下午)?\s*(\d{1,2}):(\d{2})$/,
  );
  if (chineseMatch) {
    const [, year, month, day, meridiem, rawHour, minute] = chineseMatch;
    let hour = Number(rawHour);
    if (meridiem === "下午" && hour < 12) {
      hour += 12;
    }
    if (meridiem === "上午" && hour === 12) {
      hour = 0;
    }
    return new Date(Number(year), Number(month) - 1, Number(day), hour, Number(minute), 0, 0);
  }

  const basicMatch = normalized.match(/^(\d{4})-(\d{2})-(\d{2})\s*(\d{1,2}):(\d{2})$/);
  if (basicMatch) {
    const [, year, month, day, hour, minute] = basicMatch;
    return new Date(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), 0, 0);
  }

  return null;
}
