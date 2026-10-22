const { getToken } = require("./auth");
const { request } = require("./request");
const { getErrorMessage } = require("./messages");
const { getApiOrigin, getCloudbaseConfig } = require("./api");

const UPLOAD_SCENE_WHITELIST = new Set([
  "notice",
  "meeting",
  "volunteer",
  "request",
  "request_reply",
  "gov_apply",
  "gov_reply",
  "open",
  "open_item",
  "open_detail",
  "gov",
  "gov_service",
  "gov_detail",
  "ledger",
]);
const INLINE_UPLOAD_MAX_BYTES = 900 * 1024;
const INLINE_UPLOAD_QUALITY_STEPS = [72, 58, 44, 32, 24];
const CLOUD_RELAY_MAX_BYTES = 6 * 1024 * 1024;
const CLOUD_RELAY_QUALITY_STEPS = [82, 72, 60, 48, 36];
const CONTENT_TYPE_BY_EXTENSION = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".heic": "image/heic",
  ".heif": "image/heif",
};

function normalizeScene(scene) {
  const text = String(scene || "").trim().toLowerCase();
  if (!text || !/^[a-z0-9_-]{1,32}$/.test(text)) {
    return "";
  }
  if (!UPLOAD_SCENE_WHITELIST.has(text)) {
    return "";
  }
  return text;
}

function getFileExtension(filePath) {
  const text = String(filePath || "").trim().toLowerCase();
  const index = text.lastIndexOf(".");
  return index >= 0 ? text.slice(index) : "";
}

function resolveContentType(filePath) {
  return CONTENT_TYPE_BY_EXTENSION[getFileExtension(filePath)] || "image/jpeg";
}

function getFsManager() {
  if (typeof wx.getFileSystemManager !== "function") {
    return null;
  }
  return wx.getFileSystemManager();
}

function statFile(filePath) {
  const fs = getFsManager();
  if (!fs) {
    return Promise.reject({ detail: "request_failed" });
  }
  return new Promise((resolve, reject) => {
    fs.stat({
      path: filePath,
      recursive: false,
      success(res) {
        resolve(res || {});
      },
      fail(err) {
        reject(err);
      },
    });
  });
}

function readFileAsBase64(filePath) {
  const fs = getFsManager();
  if (!fs) {
    return Promise.reject({ detail: "request_failed" });
  }
  return new Promise((resolve, reject) => {
    fs.readFile({
      filePath,
      encoding: "base64",
      success(res) {
        const data = String(res?.data || "").trim();
        if (!data) {
          reject({ detail: "empty_image_file" });
          return;
        }
        resolve(data);
      },
      fail(err) {
        reject(err);
      },
    });
  });
}

function compressImage(filePath, quality) {
  return new Promise((resolve, reject) => {
    wx.compressImage({
      src: filePath,
      quality,
      success(res) {
        resolve(String(res?.tempFilePath || "").trim());
      },
      fail(err) {
        reject(err);
      },
    });
  });
}

async function prepareUploadFileByMaxBytes(filePath, maxBytes, qualitySteps = []) {
  let currentPath = String(filePath || "").trim();
  if (!currentPath) {
    throw { detail: "empty_image_file" };
  }

  let stat = await statFile(currentPath);
  let size = Number(stat?.stats?.size || stat?.size || 0);
  if (size > 0 && size <= maxBytes) {
    return currentPath;
  }

  for (const quality of qualitySteps) {
    try {
      const compressedPath = await compressImage(currentPath, quality);
      if (!compressedPath) {
        continue;
      }
      currentPath = compressedPath;
      stat = await statFile(currentPath);
      size = Number(stat?.stats?.size || stat?.size || 0);
      if (size > 0 && size <= maxBytes) {
        return currentPath;
      }
    } catch (err) {
      // Ignore and continue trying lower quality.
    }
  }

  throw { detail: "image_inline_too_large" };
}

async function prepareInlineUploadFile(filePath) {
  return prepareUploadFileByMaxBytes(filePath, INLINE_UPLOAD_MAX_BYTES, INLINE_UPLOAD_QUALITY_STEPS);
}

async function prepareCloudRelayFile(filePath) {
  return prepareUploadFileByMaxBytes(filePath, CLOUD_RELAY_MAX_BYTES, CLOUD_RELAY_QUALITY_STEPS);
}

function shouldUseInlineUpload() {
  const cloudbase = getCloudbaseConfig();
  return !!(
    cloudbase.enabled &&
    cloudbase.envId &&
    cloudbase.service &&
    wx.cloud &&
    typeof wx.cloud.callContainer === "function"
  );
}

function shouldUseCloudRelayUpload() {
  const cloudbase = getCloudbaseConfig();
  return !!(
    cloudbase.enabled &&
    cloudbase.envId &&
    wx.cloud &&
    typeof wx.cloud.uploadFile === "function" &&
    typeof wx.cloud.getTempFileURL === "function"
  );
}

function buildCloudPath(scene, filePath) {
  const safeScene = normalizeScene(scene) || "gov_apply";
  const ext = getFileExtension(filePath) || ".jpg";
  return `deshengcun/${safeScene}/${Date.now()}_${Math.random().toString(16).slice(2, 10)}${ext}`;
}

function uploadFileToCloudStaging(filePath, scene) {
  return new Promise((resolve, reject) => {
    wx.cloud.uploadFile({
      cloudPath: buildCloudPath(scene, filePath),
      filePath,
      success(res) {
        const fileID = String(res?.fileID || "").trim();
        if (!fileID) {
          reject({ detail: "cloud_file_upload_failed" });
          return;
        }
        resolve(fileID);
      },
      fail(err) {
        reject(err || { detail: "cloud_file_upload_failed" });
      },
    });
  });
}

function getCloudTempFileUrl(fileID) {
  return new Promise((resolve, reject) => {
    wx.cloud.getTempFileURL({
      fileList: [fileID],
      success(res) {
        const row = Array.isArray(res?.fileList) ? res.fileList[0] : null;
        const tempUrl = String(row?.tempFileURL || "").trim();
        if (!tempUrl) {
          reject({ detail: "cloud_file_temp_url_failed" });
          return;
        }
        resolve(tempUrl);
      },
      fail(err) {
        reject(err || { detail: "cloud_file_temp_url_failed" });
      },
    });
  });
}

function deleteCloudStagingFile(fileID) {
  if (!fileID || !wx.cloud || typeof wx.cloud.deleteFile !== "function") {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    wx.cloud.deleteFile({
      fileList: [fileID],
      complete() {
        resolve();
      },
    });
  });
}

function normalizeContainerResponse(res) {
  if (res && typeof res.statusCode === "number") {
    return res;
  }
  return {
    statusCode: Number(res?.statusCode || 500) || 500,
    data: res?.data || res || {},
  };
}

async function uploadSingleImageInline(filePath, role = "villager", scene = "") {
  const token = getToken();
  const cloudbase = getCloudbaseConfig();
  const normalizedScene = normalizeScene(scene);
  if (!normalizedScene) {
    return Promise.reject({ detail: "invalid_upload_scene" });
  }

  const preparedPath = await prepareInlineUploadFile(filePath);
  const dataBase64 = await readFileAsBase64(preparedPath);
  const contentType = resolveContentType(preparedPath || filePath);

  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: { env: cloudbase.envId },
      path: "/api/v1/uploads/images-inline",
      method: "POST",
      header: {
        "content-type": "application/json",
        "X-WX-SERVICE": cloudbase.service,
        "X-Role": role || "villager",
        "X-Token": token,
      },
      data: {
        scene: normalizedScene,
        content_type: contentType,
        data_base64: dataBase64,
      },
      timeout: 60000,
      success(res) {
        const normalized = normalizeContainerResponse(res);
        if (normalized.statusCode >= 200 && normalized.statusCode < 300 && normalized.data?.url) {
          resolve(normalized.data);
          return;
        }
        reject(normalized.data || { detail: "request_failed" });
      },
      fail(err) {
        reject(err);
      },
    });
  });
}

async function uploadSingleImageCloudRelay(filePath, role = "villager", scene = "") {
  const normalizedScene = normalizeScene(scene);
  if (!normalizedScene) {
    return Promise.reject({ detail: "invalid_upload_scene" });
  }
  const preparedPath = await prepareCloudRelayFile(filePath);
  const contentType = resolveContentType(preparedPath || filePath);
  const fileID = await uploadFileToCloudStaging(preparedPath, normalizedScene);
  try {
    const tempUrl = await getCloudTempFileUrl(fileID);
    const result = await request({
      path: "/uploads/images-from-cloud",
      method: "POST",
      role,
      timeout: 60000,
      data: {
        scene: normalizedScene,
        source_url: tempUrl,
        content_type: contentType,
      },
    });
    if (result && result.url) {
      return result;
    }
    throw { detail: "upload_store_failed" };
  } finally {
    await deleteCloudStagingFile(fileID);
  }
}

async function uploadSingleImage(filePath, role = "villager", scene = "") {
  if (shouldUseCloudRelayUpload()) {
    try {
      return await uploadSingleImageCloudRelay(filePath, role, scene);
    } catch (err) {
      if (!shouldUseInlineUpload()) {
        throw err;
      }
    }
  }
  if (shouldUseInlineUpload()) {
    return uploadSingleImageInline(filePath, role, scene);
  }
  const token = getToken();
  const origin = getApiOrigin();
  const normalizedScene = normalizeScene(scene);
  if (!normalizedScene) {
    return Promise.reject({ detail: "invalid_upload_scene" });
  }
  const url = `${origin}/api/v1/uploads/images?scene=${encodeURIComponent(normalizedScene)}`;
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url,
      filePath,
      name: "file",
      header: {
        "X-Role": role || "villager",
        "X-Token": token,
      },
      success(res) {
        let payload = {};
        try {
          payload = JSON.parse(res.data || "{}");
        } catch (e) {
          payload = { detail: "request_failed" };
        }
        if (res.statusCode >= 200 && res.statusCode < 300 && payload.url) {
          resolve(payload);
          return;
        }
        reject(payload);
      },
      fail(err) {
        reject(err);
      },
    });
  });
}

async function uploadImages(filePaths, role = "villager", scene = "") {
  const urls = [];
  for (const filePath of filePaths || []) {
    try {
      const result = await uploadSingleImage(filePath, role, scene);
      if (result && result.url) {
        urls.push(result.url);
      }
    } catch (err) {
      throw new Error(getErrorMessage(err));
    }
  }
  return urls;
}

module.exports = {
  uploadImages,
};
