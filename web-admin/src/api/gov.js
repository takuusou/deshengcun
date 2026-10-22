import http, { buildAdminHeaders } from "./http";

export async function listAdminGovApplications(token, filters = {}) {
  const { data } = await http.get("/admin/gov/applications", {
    headers: buildAdminHeaders(token),
    params: {
      status: filters.status || "",
      service_key: filters.service_key || "",
      keyword: filters.keyword || "",
      village_group: filters.village_group || "",
    },
  });
  return data;
}

export async function listAdminGovServices(token) {
  const { data } = await http.get("/admin/gov/services", {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function fetchAdminGovServiceDetail(token, serviceId) {
  const { data } = await http.get(`/admin/gov/services/${serviceId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminGovService(token, serviceId, payload) {
  const { data } = await http.put(`/admin/gov/services/${serviceId}`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function fetchAdminGovApplicationDetail(token, applicationId) {
  const { data } = await http.get(`/admin/gov/applications/${applicationId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminGovApplication(token, applicationId, payload) {
  const { data } = await http.patch(`/admin/gov/applications/${applicationId}`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}
