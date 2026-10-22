import axios from "axios";

import http, { buildAdminHeaders, buildApiUrl, downloadBlobFile } from "./http";

export async function listAdminVillagerIdentities(token, params = {}) {
  const { data } = await http.get("/admin/villager-identities", {
    headers: buildAdminHeaders(token),
    params: {
      keyword: params.keyword || "",
      limit: params.limit || 200,
    },
  });
  return data;
}

export async function unbindAdminVillagerIdentity(token, userId, payload = {}) {
  const { data } = await http.post(`/admin/villager-identities/${userId}/unbind`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function rebindAdminVillagerIdentity(token, userId, payload) {
  const { data } = await http.post(`/admin/villager-identities/${userId}/rebind`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function fetchAdminVillagerIdentitySummary(token, params = {}) {
  const { data } = await http.get("/admin/villager-identities/summary", {
    headers: buildAdminHeaders(token),
    params: {
      keyword: params.keyword || "",
    },
  });
  return data;
}

export async function exportAdminVillagerIdentities(token, params = {}, filename = "村民脱敏名册.xlsx") {
  const response = await axios.get(buildApiUrl("/admin/villager-identities/export"), {
    headers: buildAdminHeaders(token),
    params: {
      keyword: params.keyword || "",
    },
    responseType: "blob",
    timeout: 30000,
  });
  downloadBlobFile(
    response.data,
    filename,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  );
}
