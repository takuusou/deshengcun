const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");

Page({
  data: {
    sections: [
      {
        title: "登录与实名",
        items: [
          "可先浏览首页、公开和好物内容，提交办理事项前再登录。",
          "实名认证使用真实姓名和身份证号核验户籍名单，手机号仅作为联系号码。",
          "手机号通过微信官方能力绑定，不需要额外验证流程。",
        ],
      },
      {
        title: "办理服务",
        items: [
          "政务办理可提交开具证明、低保申请、特困认证。",
          "便民协同可发起随手拍、就业培训报名、志愿服务、建议反馈。",
          "提交后可在\"我的-办理记录\"查看进度和结果，共支持申请、进度、结果三种状态查看。",
        ],
      },
      {
        title: "便民服务",
        items: [
          "首页便民服务提供湘税社保、智慧人社、土地承包、湘易办、奖扶年审等第三方服务快捷入口。",
          "部分服务需先完成实名认证或跳转至对应官方平台办理。",
        ],
      },
      {
        title: "通知与公开",
        items: [
          "首页展示置顶通知、村委会服务电话和历史通知列表。",
          "公开页展示得胜村村情总览（村组、家庭、人口、党员数量）和村情简介。",
          "服务通知提醒需您主动点击查看，不会自动弹出。",
        ],
      },
      {
        title: "得胜好物",
        items: [
          "好物页展示得胜村本地特色产品，如平江烟茶、农家腊肉、得胜黄鳝面等。",
          "点击\"点击了解\"可查看产品详情介绍。",
        ],
      },
    ],
  },
  onLoad() {
    showDefaultShareMenu();
  },
  goBack() {
    wx.navigateBack({
      fail() {
        wx.switchTab({ url: "/pages/me/me" });
      },
    });
  },
  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜服务通 - 使用帮助", path: "/pages/help/help" });
  },
  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通 - 使用帮助" });
  },
});
