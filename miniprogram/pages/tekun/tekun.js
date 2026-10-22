const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");

const MATERIALS = [
  { key: "application", name: "申请书", shortName: "申请书", desc: "本人手写" },
  { key: "hukou", name: "户口簿", shortName: "户口簿", desc: "整户户口簿页" },
  { key: "id_card", name: "身份证", shortName: "身份证", desc: "正反面各一张（同一项里传两张）" },
  { key: "bank_card", name: "银行卡", shortName: "银行卡", desc: "本人名下" },
];

const FLOW_CONFIG = {
  requestType: "tekun",
  title: "特困认证",
  subtitle: "特困供养 · 材料上传",
  introText: "办理特困认证需要以下材料。请先备齐，再点下一步逐项拍照上传。",
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
    return buildShareAppMessage({ title: "得胜服务通 - 特困认证", path: "/pages/tekun/tekun" });
  },
  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通 - 特困认证" });
  },
});
