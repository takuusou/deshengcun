import http, { buildAdminHeaders } from "./http";

export async function loginAdmin(payload) {
  const { data } = await http.post("/admin/auth/login", payload);
  return data;
}

export async function fetchAdminMe(token) {
  const { data } = await http.get("/admin/auth/me", {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function logoutAdmin(token) {
  const { data } = await http.post(
    "/admin/auth/logout",
    {},
    {
      headers: buildAdminHeaders(token),
    }
  );
  return data;
}

export async function changeAdminPassword(token, payload) {
  const { data } = await http.post("/admin/auth/change-password", payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function beginAdminMfaSetup(token) {
  const { data } = await http.post(
    "/admin/auth/mfa/setup",
    {},
    { headers: buildAdminHeaders(token) }
  );
  return data;
}

export async function confirmAdminMfaSetup(token, code) {
  const { data } = await http.post(
    "/admin/auth/mfa/confirm",
    { code },
    { headers: buildAdminHeaders(token) }
  );
  return data;
}
