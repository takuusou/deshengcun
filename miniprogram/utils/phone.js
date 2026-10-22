const MOBILE_PHONE_DIGITS = 11;

function compactPhone(value) {
  return String(value || "")
    .replace(/\D/g, "")
    .slice(0, MOBILE_PHONE_DIGITS);
}

function formatPhoneInput(value) {
  const digits = compactPhone(value);
  if (!digits) {
    return "";
  }
  if (digits.length <= 3) {
    return digits;
  }
  if (digits.length <= 7) {
    return `${digits.slice(0, 3)} ${digits.slice(3)}`;
  }
  return `${digits.slice(0, 3)} ${digits.slice(3, 7)} ${digits.slice(7)}`;
}

function formatPhoneDisplay(value) {
  const text = String(value || "").trim();
  if (!text) {
    return "";
  }
  const compactText = text.replace(/\s/g, "");
  if (/^[\d*]{11}$/.test(compactText)) {
    if (compactText.length <= 3) {
      return compactText;
    }
    if (compactText.length <= 7) {
      return `${compactText.slice(0, 3)} ${compactText.slice(3)}`;
    }
    return `${compactText.slice(0, 3)} ${compactText.slice(3, 7)} ${compactText.slice(7)}`;
  }
  const digits = compactPhone(text);
  if (digits.length === MOBILE_PHONE_DIGITS) {
    return formatPhoneInput(digits);
  }
  return text;
}

function isValidMobilePhone(value) {
  return /^1\d{10}$/.test(compactPhone(value));
}

function dialPhoneNumber(phoneNumber, options = {}) {
  const text = String(phoneNumber || "").trim();
  if (!text) {
    wx.showToast({ title: options.emptyToastTitle || "暂未配置联系电话", icon: "none" });
    return;
  }
  wx.makePhoneCall({
    phoneNumber: text,
    fail() {
      wx.showToast({ title: options.failToastTitle || "拨号失败，请稍后再试", icon: "none" });
    },
  });
}

module.exports = {
  compactPhone,
  dialPhoneNumber,
  formatPhoneDisplay,
  formatPhoneInput,
  isValidMobilePhone,
};
