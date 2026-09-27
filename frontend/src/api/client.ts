import axios from "axios";

const TOKEN_KEY = "finsight_token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = String(error.config?.url ?? "");
    if (axios.isAxiosError(error) && error.response?.status === 401 && !url.includes("/api/auth/login")) {
      sessionStorage.removeItem(TOKEN_KEY);
      if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/register")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.message;
    if (typeof message === "string" && message.trim()) return message;
    return error.message;
  }
  return "The request could not be completed.";
}
