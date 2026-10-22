const releaseConfig = require("../config/release");
const cloudbaseConfig = require("../config/cloudbase");

function normalizeApiBase(value) {
  const text = String(value || "").trim();
  if (!text) {
    throw new Error("api_base_not_configured");
  }
  const trimmed = text.replace(/\/+$/, "");
  if (/\/api\/v1$/i.test(trimmed)) {
    return trimmed;
  }
  if (/\/api$/i.test(trimmed)) {
    return `${trimmed}/v1`;
  }
  return `${trimmed}/api/v1`;
}

const DEFAULT_API_BASE = normalizeApiBase(releaseConfig.apiBase);
const DEFAULT_PUBLIC_ORIGIN = String(cloudbaseConfig.publicBaseUrl || "").trim().replace(/\/+$/, "");

function getAppSafe() {
  try {
    return getApp();
  } catch (err) {
    return null;
  }
}

function getApiBase() {
  const app = getAppSafe();
  return normalizeApiBase(app?.globalData?.apiBase || DEFAULT_API_BASE);
}

function getApiOrigin() {
  if (cloudbaseConfig.enabled && DEFAULT_PUBLIC_ORIGIN) {
    return DEFAULT_PUBLIC_ORIGIN;
  }
  return getApiBase().replace(/\/api\/v1$/i, "");
}

function isCloudbaseEnabled() {
  return !!cloudbaseConfig.enabled;
}

function getCloudbaseConfig() {
  return {
    enabled: !!cloudbaseConfig.enabled,
    envId: String(cloudbaseConfig.envId || "").trim(),
    service: String(cloudbaseConfig.service || "").trim(),
    publicBaseUrl: DEFAULT_PUBLIC_ORIGIN,
  };
}

module.exports = {
  DEFAULT_API_BASE,
  normalizeApiBase,
  getApiBase,
  getApiOrigin,
  isCloudbaseEnabled,
  getCloudbaseConfig,
};
