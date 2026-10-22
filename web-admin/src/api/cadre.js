import http, { buildAdminHeaders } from "./http";

export async function listAdminCadreAuthorizations(token, params = {}) {
  const { data } = await http.get("/admin/cadre-authorizations", {
    headers: buildAdminHeaders(token),
    params,
  });
  return data;
}

export async function createAdminCadreAuthorization(token, payload) {
  const { data } = await http.post("/admin/cadre-authorizations", payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function deleteAdminCadreAuthorization(token, authorizationId) {
  const { data } = await http.delete(`/admin/cadre-authorizations/${authorizationId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminCadreAuthorization(token, authorizationId, payload) {
  const { data } = await http.put(`/admin/cadre-authorizations/${authorizationId}`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function createAdminCadreAccount(token, authorizationId, payload) {
  const { data } = await http.post(`/admin/cadre-authorizations/${authorizationId}/create-account`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function resetAdminCadreAccountPassword(token, authorizationId, payload) {
  const { data } = await http.post(`/admin/cadre-authorizations/${authorizationId}/reset-password`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}
