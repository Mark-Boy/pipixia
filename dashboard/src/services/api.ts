import axios from "axios";
import { toast } from "sonner";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Request interceptor — 自动附加 JWT
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
      toast.error("服务器错误: " + message);
    } else {
      toast.error(message);
    }

    return Promise.reject(error);
  }
);

export default api;
