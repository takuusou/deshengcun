const { DEFAULT_API_BASE, normalizeApiBase } = require("./utils/api");
const cloudbaseConfig = require("./config/cloudbase");

App({
  globalData: {
    apiBase: DEFAULT_API_BASE,
    cloudbaseEnabled: !!cloudbaseConfig.enabled,
    guestBrowsePromptShown: false,
    userProfile: null,
    cadreRedirecting: false,
  },
  onLaunch() {
    this.globalData.apiBase = normalizeApiBase(this.globalData.apiBase);
    this.globalData.cloudbaseEnabled = !!cloudbaseConfig.enabled;

    if (
      cloudbaseConfig.enabled &&
      cloudbaseConfig.envId &&
      wx.cloud &&
      typeof wx.cloud.init === "function"
    ) {
      wx.cloud.init({
        env: cloudbaseConfig.envId,
        traceUser: true,
      });
    }

    if (wx.canIUse("getUpdateManager")) {
      const updateManager = wx.getUpdateManager();
      updateManager.onUpdateReady(() => {
        wx.showModal({
          title: "版本更新",
          content: "发现新版本，是否立即重启应用？",
          success(res) {
            if (res.confirm) {
              updateManager.applyUpdate();
            }
          },
        });
      });
    }
  },
});
