export * from "./api";

import { api } from "@/services/api";

// ==================== 商品服务 ====================
export const productService = {
  getList: (params?: Record<string, any>) =>
    api.get("/api/v1/products", { params }),
  getById: (id: number) => api.get(`/api/v1/products/${id}`),
  create: (data: any) => api.post("/api/v1/products", data),
  importByUrl: (url: string, shop_id: number) =>
    api.get("/api/v1/products/import", { params: { url, shop_id } }),
  triggerTranslate: (id: number) =>
    api.post(`/api/v1/products/${id}/translate`),
  triggerList: (id: number) =>
    api.post(`/api/v1/products/${id}/list`),
  checkFinance: (id: number) =>
    api.post(`/api/v1/products/${id}/finance/check`),
  update: (id: number, data: any) =>
    api.put(`/api/v1/products/${id}`, data),
  delete: (id: number) =>
    api.delete(`/api/v1/products/${id}`),
};

// ==================== 审核服务 ====================
export const auditService = {
  getQueue: (params?: Record<string, any>) =>
    api.get("/api/v1/audit/queue", { params }),
  approve: (id: number) =>
    api.post(`/api/v1/audit/${id}/approve`),
  reject: (id: number, comment?: string) =>
    api.post(`/api/v1/audit/${id}/reject`, { comment }),
  batchApprove: (ids: number[]) =>
    api.post("/api/v1/audit/batch/approve", { ids }),
  batchReject: (ids: number[], comment?: string) =>
    api.post("/api/v1/audit/batch/reject", { ids, comment }),
  triggerList: (id: number) =>
    api.post(`/api/v1/audit/${id}/list`),
};

// ==================== 店铺服务 ====================
export const shopService = {
  getList: (params?: Record<string, any>) =>
    api.get("/api/v1/shops", { params }),
  getById: (id: number) => api.get(`/api/v1/shops/${id}`),
  create: (data: any) => api.post("/api/v1/shops", data),
  update: (id: number, data: any) =>
    api.put(`/api/v1/shops/${id}`, data),
  delete: (id: number) => api.delete(`/api/v1/shops/${id}`),
  getToken: (id: number) =>
    api.get(`/api/v1/shops/${id}/token`),
};

// ==================== 上架服务 ====================
export const listingService = {
  getList: (params?: Record<string, any>) =>
    api.get("/api/v1/listings", { params }),
  getById: (id: number) => api.get(`/api/v1/listings/${id}`),
  create: (data: any) => api.post("/api/v1/listings", data),
  retry: (id: number) =>
    api.post(`/api/v1/listings/${id}/retry`),
};

// ==================== 翻译服务 ====================
export const translateService = {
  trigger: (product_id: number) =>
    api.post("/api/v1/translate/trigger", null, {
      params: { product_id },
    }),
  batch: (product_ids: number[]) =>
    api.post("/api/v1/translate/batch", null, {
      params: { product_ids },
    }),
  getHistory: (params?: Record<string, any>) =>
    api.get("/api/v1/translate/history", { params }),
  sync: (product_id: number) =>
    api.post(`/api/v1/translate/sync/${product_id}`),
};

// ==================== 媒体服务 ====================
export const mediaService = {
  upload: (file: File, product_id?: number) => {
    const formData = new FormData();
    formData.append("file", file);
    if (product_id) formData.append("product_id", String(product_id));
    return api.post("/api/v1/media/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  uploadBatch: (files: File[], product_id?: number) => {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    if (product_id) formData.append("product_id", String(product_id));
    return api.post("/api/v1/media/upload/batch", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  getPresignedUrl: (url: string, expires = 3600) =>
    api.get("/api/v1/media/presigned-url", {
      params: { url, expires },
    }),
  delete: (url: string) =>
    api.delete("/api/v1/media", { params: { url } }),
  getStats: () => api.get("/api/v1/media/stats"),
};

// ==================== 报表服务 ====================
export const reportService = {
  getDaily: (date?: string) =>
    api.get("/api/v1/reports/daily", { params: { date } }),
  getFinance: (start_date: string, end_date?: string) =>
    api.get("/api/v1/reports/finance", {
      params: { start_date, end_date },
    }),
  getProfitCalibration: (params?: Record<string, any>) =>
    api.get("/api/v1/reports/profit-calibration", { params }),
  getSummary: () => api.get("/api/v1/reports/summary"),
};

// ==================== 设置服务 ====================
export const settingService = {
  get: () => api.get("/api/v1/settings"),
  update: (data: any) => api.put("/api/v1/settings", data),
  getRiskWords: () => api.get("/api/v1/settings/risk-words"),
  addRiskWord: (word: string, word_type = "brand") =>
    api.post("/api/v1/settings/risk-words/add", null, {
      params: { word, word_type },
    }),
};

// ==================== 认证服务 ====================
export const authService = {
  login: (data: { email: string; password: string }) =>
    axios.post("/auth/login", data),
  register: (data: {
    username: string;
    email: string;
    password: string;
    role?: string;
  }) => axios.post("/auth/register", data),
  refresh: () => api.post("/auth/refresh"),
  logout: () => api.post("/auth/logout"),
  getMe: () => api.get("/auth/me"),
};

// ==================== 健康检查 ====================
export const healthService = {
  check: () => api.get("/api/v1/health"),
};
