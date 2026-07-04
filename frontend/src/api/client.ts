import axios from "axios";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;

function normalizeApiBaseUrl(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  if (!trimmed) return undefined;
  if (!import.meta.env.DEV && /^(https?:\/\/)?0\.0\.0\.0(?::\d+)?(\/.*)?$/.test(trimmed)) {
    return "";
  }
  return trimmed;
}

export const API_BASE_URL =
  normalizeApiBaseUrl(configuredApiBaseUrl) || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("[API Error]", error);
    return Promise.reject(error);
  }
);
