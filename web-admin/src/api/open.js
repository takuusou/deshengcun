import http, { buildAdminHeaders } from "./http";

export async function listAdminMetrics(token) {
  const { data } = await http.get("/admin/open/metrics", {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminMetrics(token, payload) {
  const { data } = await http.put("/admin/open/metrics", payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function getAdminOpenProfile(token) {
  const { data } = await http.get("/admin/open/profile", {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminOpenProfile(token, payload) {
  const { data } = await http.put("/admin/open/profile", payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function listAdminOpenItems(token, params = {}) {
  const { data } = await http.get("/admin/open/items", {
    headers: buildAdminHeaders(token),
    params,
  });
  return data;
}

export async function fetchAdminOpenItemDetail(token, itemId) {
  const { data } = await http.get(`/admin/open/items/${itemId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function createAdminOpenItem(token, payload) {
  const { data } = await http.post("/admin/open/items", payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminOpenItem(token, itemId, payload) {
  const { data } = await http.put(`/admin/open/items/${itemId}`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function deleteAdminOpenItem(token, itemId) {
  const { data } = await http.delete(`/admin/open/items/${itemId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}
