import { api } from "./api";

// ==================== 拼多多采集账号服务 ====================

export interface PddAccount {
  id: number;
  user_id: number;
  account_name: string;
  phone?: string;
  notes?: string;
  login_status: "not_logged_in" | "logged_in" | "expired" | "error";
  storage_state?: string;
  last_login_at?: string;
  expires_at?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PddAccountListResponse {
  total: number;
  page: number;
  size: number;
  accounts: PddAccount[];
}

export interface PddQrcodeGenerateRequest {
  account_id: number;
}

export interface PddQrcodeGenerateResponse {
  account_id: number;
  qrcode_url: string;
  qrcode_token: string;
  expires_at: string;
  message: string;
}

export interface PddQrcodeStatusRequest {
  qrcode_token: string;
}

export interface PddQrcodeStatusResponse {
  qrcode_token: string;
  status: "generating" | "waiting" | "scanned" | "confirmed" | "success" | "failed" | "expired" | "error";
  qrcode_image?: string | null;
  message: string;
  account_id?: number | null;
  account?: PddAccount | null;
}

export const pddAccountService = {
  // 获取账号列表
  getList: (params?: { page?: number; size?: number; active_only?: boolean }) =>
    api.get("/api/v1/pdd-accounts", { params }),

  // 获取单个账号
  getById: (id: number) =>
    api.get(`/api/v1/pdd-accounts/${id}`),

  // 创建账号
  create: (data: { account_name: string; phone?: string; notes?: string }) =>
    api.post("/api/v1/pdd-accounts", data),

  // 更新账号
  update: (id: number, data: Partial<{ account_name: string; phone: string; notes: string; is_active: boolean }>) =>
    api.put(`/api/v1/pdd-accounts/${id}`, data),

  // 删除账号
  delete: (id: number) =>
    api.delete(`/api/v1/pdd-accounts/${id}`),

  // 生成二维码
  generateQrcode: (accountId: number) =>
    api.post("/api/v1/pdd-accounts/qrcode/generate", { account_id: accountId }),

  // 查询二维码状态
  checkQrcodeStatus: (qrcodeToken: string) =>
    api.post("/api/v1/pdd-accounts/qrcode/status", { qrcode_token: qrcodeToken }),

  // 登出账号
  logout: (id: number) =>
    api.post(`/api/v1/pdd-accounts/${id}/logout`),

  // 采集商品
  collectProducts: (data: { account_id: number; urls: string[]; target_shop_id: number; max_pages?: number }) =>
    api.post("/api/v1/pdd-accounts/collect", data),

  // 获取账号关联的店铺列表
  getShops: (accountId: number) =>
    api.get(`/api/v1/pdd-accounts/${accountId}/shops`),
};