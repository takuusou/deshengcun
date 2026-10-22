import http, { buildAdminHeaders } from "./http";

export async function fetchAdminNavBadges(token) {
  const { data } = await http.get("/admin/nav-badges", {
    headers: buildAdminHeaders(token),
  });
  return data || {};
}
