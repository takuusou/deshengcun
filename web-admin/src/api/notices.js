import http, { buildAdminHeaders } from "./http";

export async function listAdminNotices(token, filters = {}) {
  const { data } = await http.get("/admin/notices", {
    headers: buildAdminHeaders(token),
    params: {
      keyword: filters.keyword || "",
      home_top_only: !!filters.home_top_only,
    },
  });
  return data;
}

export async function fetchAdminNoticeDetail(token, noticeId) {
  const { data } = await http.get(`/admin/notices/${noticeId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function createAdminNotice(token, payload) {
  const { data } = await http.post("/admin/notices", payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminNotice(token, noticeId, payload) {
  const { data } = await http.put(`/admin/notices/${noticeId}`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function deleteAdminNotice(token, noticeId) {
  const { data } = await http.delete(`/admin/notices/${noticeId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}
