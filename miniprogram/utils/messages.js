const ERROR_MAP = {
  cadre_role_required: "仅村干部可操作",
  event_not_found: "活动不存在",
  event_quota_reached: "活动名额已满",
  training_program_not_found: "培训不存在",
  training_signup_closed: "该培训已停止报名",
  invalid_training_program_title: "请填写培训标题",
  invalid_training_date: "培训日期格式不正确",
  invalid_training_date_range: "结束日期不能早于报名截止日期",
  invalid_training_signup_name: "请填写报名姓名",
  signup_conflict: "请勿重复报名",
  request_failed: "请求失败",
  login_required: "请先登录",
  invalid_token: "登录状态无效，请重新登录",
  token_expired: "登录已过期，请重新登录",
  invalid_wechat_code: "微信登录失败，请重试",
  wechat_login_unconfigured: "微信登录尚未完成正式配置，请联系村委会",
  wechat_service_unavailable: "微信登录服务暂时不可用，请稍后再试",
  invalid_wechat_phone_code: "手机号授权已失效，请重新点击“微信验证手机号”",
  wechat_phone_unconfigured: "微信手机号验证尚未完成正式配置，请联系村委会",
  wechat_phone_unavailable: "微信手机号验证服务暂时不可用，请稍后再试",
  wechat_notice_template_unconfigured: "村委正在配置服务通知模板，请稍后再试",
  wechat_notice_send_unavailable: "微信服务通知暂时不可用，请稍后再试",
  phone_bind_requires_wechat_verify: "请使用微信官方手机号验证按钮完成绑定",
  cadre_web_admin_only: "村干部管理已迁移到电脑端 Web 后台，请改用后台账号在浏览器登录",
  cadre_password_login_disabled: "原干部账号密码登录已停用，请先完成微信身份信息登记后进入干部工作台验证",
  cadre_authorization_required: "当前微信身份未在干部授权名单中",
  cadre_stepup_required: "进入干部工作台前，请先完成一次操作密码验证",
  cadre_operation_password_not_set: "首次进入干部工作台，请先设置独立操作密码",
  invalid_cadre_operation_password: "干部操作密码不正确，请重新输入",
  weak_cadre_operation_password: "操作密码至少 8 位，且不要使用纯数字",
  cadre_access_locked: "连续输错次数过多，干部工作台已暂时锁定，请稍后再试",
  invalid_phone: "手机号格式不正确",
  invalid_real_name: "请输入真实姓名",
  invalid_id_card: "身份证号格式不正确",
  realname_required: "请先完成基础实名登记",
  invalid_manager_credentials: "村委账号或密码错误",
  privacy_consent_required: "请先同意隐私政策",
  sensitive_consent_required: "请先同意实名信息处理授权",
  roster_not_ready: "户籍白名单尚未导入，请稍后再试或联系村委",
  identity_not_in_roster: "身份信息校验失败",
  id_card_already_verified: "身份证号已被验证，请联系村委会处理",
  villager_role_required: "仅村民可提交该信息",
  verified_villager_required: "请先登录并完成基础实名登记",
  invalid_policy_version: "隐私政策版本已更新，请重新确认",
  invalid_consent_type: "同意项参数错误",
  unsupported_file_type: "仅支持逗号分隔文件或表格文件",
  invalid_roster_file: "名单文件格式错误，请检查后重试",
  empty_roster_file: "名单文件为空或无有效数据",
  xlsx_not_supported: "后端缺少 XLSX 解析依赖，请安装后重试",
  unsupported_image_type: "仅支持 JPG、PNG、WEBP、HEIC 图片",
  empty_image_file: "图片为空，请重新选择",
  image_file_too_large: "单张图片超过8MB，请压缩后上传",
  image_content_mismatch: "图片内容与文件格式不一致，请重新选择原始图片",
  image_inline_too_large: "图片较大，已超出当前可直传大小，请重新选择或压缩后上传",
  cloud_file_upload_failed: "图片暂存失败，请稍后重试",
  cloud_file_temp_url_failed: "图片链接生成失败，请稍后重试",
  invalid_upload_scene: "图片上传场景不正确，请重试",
  invalid_upload_source_url: "图片上传来源不正确，请重新选择",
  invalid_photo_scene: "图片与当前业务场景不匹配，请重新上传",
  invalid_metric_payload: "公开数字信息格式不正确",
  invalid_request_type: "诉求类型不正确",
  invalid_request_payload: "请填写完整诉求内容",
  request_duplicate_submission: "相同内容刚刚已经提交，可到办理记录查看当前进度",
  gov_application_duplicate_submission: "相同申请刚刚已经提交，可到办理记录查看当前进度",
  request_phone_required: "请填写本人联系电话",
  invalid_request_status: "诉求状态不正确",
  request_not_found: "未找到该诉求记录",
  notice_not_found: "未找到通知内容",
  meeting_not_found: "未找到该会议记录",
  invalid_open_section: "公开分类参数不正确",
  open_item_not_found: "未找到该公开详情",
  gov_service_not_found: "未找到该政务服务",
  invalid_gov_service_payload: "政务服务配置内容不正确",
  invalid_gov_application_payload: "请完整填写政务服务申请信息",
  invalid_gov_application_status: "政务服务申请状态不正确",
  gov_application_not_found: "未找到该政务申请",
  gov_application_cancel_not_allowed: "该申请当前不能取消",
  certificate_duplicate_submission: "同一份证明请勿重复提交，可到办理记录查看当前进度",
  certificate_daily_limit_reached: "当天最多只能提交5份不同的证明，请明天再试",
  gov_handle_requires_feedback: "请填写处理说明或上传回执图片后再提交",
  certificate_reply_photo_required: "开证明办结时必须上传盖章回执图片",
  request_handle_requires_feedback: "诉求处理请至少填写回复或上传回执图片",
  request_cancel_not_allowed: "该诉求当前不能取消",
  rate_limit_exceeded: "操作过于频繁，请稍后再试",
  invalid_upload_signature: "图片访问签名无效，请刷新页面后重试",
  upload_url_expired: "图片链接已过期，请刷新页面后重试",
  upload_store_failed: "图片上传暂时不可用，请稍后再试；如持续失败请联系村委会核查",
  source_image_fetch_failed: "图片接收失败，请稍后重试；如持续失败请联系村委会核查",
};

function getRoleText(role) {
  return role === "cadre" ? "村干部" : "村民";
}

function getErrorMessage(err) {
  const detail =
    (err && err.detail) ||
    (err && err.message) ||
    (err && err.errMsg) ||
    "";
  if (typeof detail === "string" && ERROR_MAP[detail]) {
    return ERROR_MAP[detail];
  }
  if (typeof detail === "string" && /timeout|fail|network|request/i.test(detail)) {
    return "网络异常，请检查后端";
  }
  if (typeof detail === "string" && /[\u4e00-\u9fa5]/.test(detail)) {
    return detail;
  }
  return "操作失败，请稍后重试";
}

module.exports = {
  getRoleText,
  getErrorMessage,
};
