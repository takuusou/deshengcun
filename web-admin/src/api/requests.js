import http, { buildAdminHeaders, downloadBlobFile } from "./http";

export async function listAdminRequests(token, filters = {}) {
  const { data } = await http.get("/admin/requests", {
    headers: buildAdminHeaders(token),
    params: {
      status: filters.status || "",
      request_type: filters.request_type || "",
      keyword: filters.keyword || "",
    },
  });
  return data;
}

export async function fetchAdminRequestDetail(token, requestId) {
  const { data } = await http.get(`/admin/requests/${requestId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminRequest(token, requestId, payload) {
  const { data } = await http.patch(`/admin/requests/${requestId}`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function exportAdminRequestMaterials(token, requestId, filename) {
  const response = await http.get(`/admin/requests/${requestId}/materials/export`, {
    headers: buildAdminHeaders(token),
    responseType: "blob",
    timeout: 120000,
  });
  downloadBlobFile(response.data, filename, "application/zip");
}

export async function listAdminProposals(token) {
  const { data } = await http.get("/admin/proposals", {
    headers: buildAdminHeaders(token),
  });
  return data;
}
