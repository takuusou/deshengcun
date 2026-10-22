function confirmAction(title, content, options = {}) {
  return new Promise((resolve) => {
    wx.showModal({
      title: String(title || "").trim(),
      content: String(content || "").trim(),
      confirmText: options.confirmText || "是",
      cancelText: options.cancelText || "否",
      showCancel: options.showCancel !== false,
      success: resolve,
      fail: () => resolve({ confirm: false }),
    });
  });
}

module.exports = {
  confirmAction,
};
