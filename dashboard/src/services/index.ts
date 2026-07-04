export * from "./api";

import { api } from "@/services/api";

export const productService = {
  getList: (params?: Record<string, any>) =>
    api.get("/products", { params }),
  getById: (id: string) => api.get(`/products/${id}`),
  create: (data: any) => api.post("/products", data),
  importByUrl: (url: string) => api.post("/products/import", { url }),
  triggerTranslate: (id: string) => api.post(`/products/${id}/translate`),
  checkFinance: (id: string) => api.post(`/products/${id}/finance/check`),
};

export const auditService = {
  getQueue: (params?: Record<string, any>) => api.get("/audit", { params }),
  approve: (id: string) => api.post(`/audit/${id}/approve`),
  reject: (id: string, comment: string) =>
    api.post(`/audit/${id}/reject`, { comment }),
  batchApprove: (ids: string[]) =>
    api.post("/audit/batch/approve", { ids }),
  batchReject: (ids: string[], comment: string) =>
    api.post("/audit/batch/reject", { ids, comment }),
};

export const financeService = {
  getDailyReport: (params?: Record<string, any>) =>
    api.get("/reports/daily", { params }),
  getFinanceReport: (params?: Record<string, any>) =>
    api.get("/reports/finance", { params }),
  getProfitCalibration: (params?: Record<string, any>) =>
    api.get("/reports/profit-calibration", { params }),
};

export const riskService = {
  getLogs: (params?: Record<string, any>) => api.get("/risk-logs", { params }),
  getWordFilter: () => api.get("/risk/word-filter"),
  updateWordFilter: (data: any) => api.put("/risk/word-filter", data),
};

export const shopService = {
  getList: () => api.get("/shops"),
  create: (data: any) => api.post("/shops", data),
  update: (id: string, data: any) => api.put(`/shops/${id}`, data),
  testConnection: (id: string) => api.post(`/shops/${id}/test`),
};

export const listingService = {
  getList: (params?: Record<string, any>) =>
    api.get("/listings", { params }),
  create: (data: any) => api.post("/listings", data),
  retry: (id: string) => api.post(`/listings/${id}/retry`),
};

export const settingService = {
  get: () => api.get("/settings"),
  update: (data: any) => api.put("/settings", data),
};
