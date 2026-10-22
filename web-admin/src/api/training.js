import axios from "axios";

import http, { buildAdminHeaders, buildApiUrl, downloadBlobFile } from "./http";

export async function listAdminTrainingPrograms(token, params = {}) {
  const { data } = await http.get("/admin/training-programs", {
    headers: buildAdminHeaders(token),
    params,
  });
  return data;
}

export async function createAdminTrainingProgram(token, payload) {
  const { data } = await http.post("/admin/training-programs", payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminTrainingProgram(token, programId, payload) {
  const { data } = await http.put(`/admin/training-programs/${programId}`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function endAdminTrainingProgram(token, programId) {
  const { data } = await http.post(`/admin/training-programs/${programId}/end`, {}, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function deleteAdminTrainingProgram(token, programId) {
  const { data } = await http.delete(`/admin/training-programs/${programId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function listAdminTrainingSignups(token, programId) {
  const { data } = await http.get(`/admin/training-programs/${programId}/signups`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function exportAdminTrainingSignups(token, programId, filename = "就业培训报名名单.csv") {
  const response = await axios.get(buildApiUrl(`/admin/training-programs/${programId}/signups/export`), {
    headers: buildAdminHeaders(token),
    responseType: "blob",
    timeout: 30000,
  });
  downloadBlobFile(response.data, filename, "text/csv;charset=utf-8");
}
