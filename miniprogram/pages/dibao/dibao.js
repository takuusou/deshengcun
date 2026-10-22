const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");

const MATERIALS = [
  { key: "application", name: "申请书", shortName: "申请书", desc: "本人手写" },
  { key: "diagnosis", name: "病历诊断书", shortName: "病历", desc: "医院开具的诊断证明" },
  { key: "hospitalization", name: "出入院记录", shortName: "出入院", desc: "住院相关记录" },
  { key: "expense", name: "费用清单", shortName: "费用", desc: "医疗费用明细" },
  { key: "hukou", name: "户口簿", shortName: "户口簿", desc: "整户户口簿页（残疾证如有）" },
  { key: "bank_card", name: "银行卡", shortName: "银行卡", desc: "本人名下" },
];

const FLOW_CONFIG = {
  requestType: "dibao",
  title: "低保申请",
  subtitle: "民政救助 · 材料上传",
  introText: "办理低保需要以下材料。请先备齐，再点下一步逐项拍照上传。",
  doneTitle: "材料已提交",
  doneMessage: "村委会已收到你的材料，会尽快为你办理。办理进度会通过微信通知你。",
};

Page({
  data: {
    flowConfig: FLOW_CONFIG,
    materialItems: MATERIALS,
  },
  onLoad() {
    showDefaultShareMenu();
  },
  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜服务通 - 低保申请", path: "/pages/dibao/dibao" });
  },
  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通 - 低保申请" });
  },
});
