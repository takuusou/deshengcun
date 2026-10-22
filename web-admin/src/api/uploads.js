import axios from "axios";

import { buildAdminHeaders, buildApiUrl } from "./http";

export async function uploadAdminImage(token, file, scene = "notice") {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await axios.post(buildApiUrl(`/admin/uploads/images?scene=${encodeURIComponent(scene)}`), formData, {
    headers: {
      ...buildAdminHeaders(token),
    },
    timeout: 30000,
  });
  return data;
}

export async function uploadAdminImages(token, files = [], scene = "notice") {
  const urls = [];
  for (const file of files || []) {
    const result = await uploadAdminImage(token, file, scene);
    if (result?.url) {
      urls.push(result.url);
    }
  }
  return urls;
}
