const { getApiOrigin } = require("./api");

function isLocalHostname(hostname) {
  const text = String(hostname || "").trim().toLowerCase();
  return (
    text === "localhost" ||
    text === "127.0.0.1" ||
    /^10\.\d+\.\d+\.\d+$/.test(text) ||
    /^192\.168\.\d+\.\d+$/.test(text) ||
    /^172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+$/.test(text)
  );
}

function parseHttpUrl(value) {
  const text = String(value || "").trim();
  const match = /^(https?:\/\/)([^/?#]+)(\/[^?#]*)(\?[^#]*)?(#.*)?$/i.exec(text);
  if (!match) {
    return null;
  }
  const host = match[2] || "";
  const hostname = host.replace(/^[^@]*@/, "").replace(/:\d+$/, "");
  return {
    origin: `${match[1]}${host}`,
    hostname,
    path: match[3] || "/",
    search: match[4] || "",
    hash: match[5] || "",
  };
}

function parseHttpOrigin(value) {
  const text = String(value || "").trim().replace(/\/+$/, "");
  const match = /^(https?:\/\/)([^/?#]+)/i.exec(text);
  if (!match) {
    return null;
  }
  const host = match[2] || "";
  const hostname = host.replace(/^[^@]*@/, "").replace(/:\d+$/, "");
  return {
    origin: `${match[1]}${host}`,
    hostname,
  };
}

function normalizePhotoUrl(url) {
  const text = String(url || "").trim();
  if (!text) {
    return "";
  }
  if (/^\/api\/v1\/uploads\/access\//i.test(text)) {
    const apiParsed = parseHttpOrigin(getApiOrigin());
    return apiParsed ? `${apiParsed.origin}${text}` : text;
  }
  const parsed = parseHttpUrl(text);
  if (!parsed || !/\/api\/v1\/uploads\/access\//i.test(parsed.path || "")) {
    return text;
  }
  const apiParsed = parseHttpOrigin(getApiOrigin());
  if (!apiParsed) {
    return text;
  }
  if (!isLocalHostname(parsed.hostname) && !isLocalHostname(apiParsed.hostname)) {
    return text;
  }
  return `${apiParsed.origin}${parsed.path}${parsed.search}${parsed.hash}`;
}

function normalizePhotoUrls(urls) {
  if (!Array.isArray(urls)) {
    return [];
  }
  return urls.map(normalizePhotoUrl).filter(Boolean);
}

module.exports = {
  normalizePhotoUrl,
  normalizePhotoUrls,
};
