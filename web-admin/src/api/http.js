import axios from "axios";

const DEFAULT_DEV_API_BASE = "http://127.0.0.1:8000/api/v1";

function normalizeApiBase(value) {
  const text = String(value || "").trim();
  if (!text) {
    return "";
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

const configuredApiBase = normalizeApiBase(import.meta.env.VITE_API_BASE_URL || "");
const API_BASE = configuredApiBase || (import.meta.env.DEV ? DEFAULT_DEV_API_BASE : "/api/v1");

if (import.meta.env.PROD && !configuredApiBase) {
  console.warn("VITE_API_BASE_URL 未配置，Web 后台已回退到同源 /api/v1。");
}

const http = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

export function buildAdminHeaders(token = "") {
  return token ? { "X-Admin-Token": token } : {};
}

export function buildApiUrl(path = "") {
  const normalizedPath = String(path || "").trim();
  if (!normalizedPath) {
    return API_BASE;
  }
  return `${API_BASE}${normalizedPath.startsWith("/") ? normalizedPath : `/${normalizedPath}`}`;
}

export function downloadBlobFile(blobData, filename, mimeType = "application/octet-stream") {
  const blob = blobData instanceof Blob ? blobData : new Blob([blobData], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default http;
