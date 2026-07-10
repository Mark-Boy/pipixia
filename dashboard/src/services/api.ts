import axios from "axios";
import { toast } from "sonner";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Request interceptor — 自动附加 JWT (Header Bearer Token)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — 统一错误处理
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status;
    const message = error.response?.data?.detail || error.message;

    if (status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    } else if (status === 403) {
      toast.error("权限不足: " + message);
    } else if (status >= 500) {
      toast.error("服务器错误，请稍后重试");
    } else if (status === 404) {
      toast.error("请求的资源不存在");
    } else if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
      toast.error("请求超时，请检查网络连接");
    } else if (error.code === "ERR_NETWORK") {
      toast.error("无法连接后端服务，请确认 API 地址正确");
    } else {
      toast.error(message || "请求失败");
    }

    return Promise.reject(error);
  }
);

export default api;
