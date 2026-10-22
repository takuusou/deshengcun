const { showDefaultShareMenu, buildShareAppMessage, buildShareTimeline } = require("../../utils/share");

Page({
  data: {
    status: "success",
    title: "提交成功",
    desc: "您的事项已提交至村委会，请耐心等待审核处理。",
    itemTitle: "",
    submittedAt: "",
    primaryText: "查看进度",
    secondaryText: "返回首页",
  },
  onLoad(options = {}) {
    showDefaultShareMenu();
    const status = String(options.status || "success").trim() === "fail" ? "fail" : "success";
    const itemTitle = decodeURIComponent(String(options.title || ""));
    const desc = decodeURIComponent(
      String(
        options.desc ||
          (status === "success"
            ? "您的事项已提交至村委会，请耐心等待审核处理。"
            : "提交未成功，请检查后重新尝试。")
      )
    );
    this.setData({
      status,
      title: status === "success" ? "提交成功" : "提交失败",
      desc,
      itemTitle,
      submittedAt: this.formatNow(),
    });
  },
  formatNow() {
    const date = new Date();
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const hour = String(date.getHours()).padStart(2, "0");
    const minute = String(date.getMinutes()).padStart(2, "0");
    return `${year} 年 ${month} 月 ${day} 日 ${hour}:${minute}`;
  },
  goHome() {
    wx.switchTab({ url: "/pages/home/home" });
  },
  goRecords() {
    wx.navigateTo({
      url: "/pages/volunteers/volunteers",
      fail() {
        wx.switchTab({ url: "/pages/me/me" });
      },
    });
  },
  onShareAppMessage() {
    return buildShareAppMessage({ title: "得胜服务通", path: "/pages/home/home" });
  },
  onShareTimeline() {
    return buildShareTimeline({ title: "得胜服务通" });
  },
});
