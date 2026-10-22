import http, { buildAdminHeaders } from "./http";

export async function listAdminAuditLogs(token, params = {}) {
  const { data } = await http.get("/admin/audit-logs", {
    headers: buildAdminHeaders(token),
    params,
  });
  return data;
}

export async function fetchAdminAuditLogDetail(token, logId) {
  const { data } = await http.get(`/admin/audit-logs/${logId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}
