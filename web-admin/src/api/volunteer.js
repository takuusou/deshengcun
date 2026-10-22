import axios from "axios";

import http, { buildAdminHeaders, buildApiUrl, downloadBlobFile } from "./http";

// 志愿活动（招募报名型，与就业培训同构；独立接口 /admin/volunteer-activities）

export async function listAdminVolunteerActivities(token, params = {}) {
  const { data } = await http.get("/admin/volunteer-activities", {
    headers: buildAdminHeaders(token),
    params,
  });
  return data;
}

export async function createAdminVolunteerActivity(token, payload) {
  const { data } = await http.post("/admin/volunteer-activities", payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminVolunteerActivity(token, activityId, payload) {
  const { data } = await http.put(`/admin/volunteer-activities/${activityId}`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function endAdminVolunteerActivity(token, activityId) {
  const { data } = await http.post(`/admin/volunteer-activities/${activityId}/end`, {}, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function deleteAdminVolunteerActivity(token, activityId) {
  const { data } = await http.delete(`/admin/volunteer-activities/${activityId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function listAdminVolunteerActivitySignups(token, activityId) {
  const { data } = await http.get(`/admin/volunteer-activities/${activityId}/signups`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function exportAdminVolunteerActivitySignups(token, activityId, filename = "志愿活动报名名单.csv") {
  const response = await axios.get(buildApiUrl(`/admin/volunteer-activities/${activityId}/signups/export`), {
    headers: buildAdminHeaders(token),
    responseType: "blob",
    timeout: 30000,
  });
  downloadBlobFile(response.data, filename, "text/csv;charset=utf-8");
}
