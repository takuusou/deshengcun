import http, { buildAdminHeaders } from "./http";

// 本地好物（纯展示，无价格/库存/购买）

export async function listAdminProducts(token) {
  const { data } = await http.get("/admin/products", {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function createAdminProduct(token, payload) {
  const { data } = await http.post("/admin/products", payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function updateAdminProduct(token, productId, payload) {
  const { data } = await http.put(`/admin/products/${productId}`, payload, {
    headers: buildAdminHeaders(token),
  });
  return data;
}

export async function deleteAdminProduct(token, productId) {
  const { data } = await http.delete(`/admin/products/${productId}`, {
    headers: buildAdminHeaders(token),
  });
  return data;
}
