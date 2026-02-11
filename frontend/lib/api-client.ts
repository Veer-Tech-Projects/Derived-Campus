import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

// Environment-aware Base URL
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let accessToken: string | null = null;

// --- REFRESH QUEUE LOGIC ---
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
};

export const setAccessToken = (token: string | null) => {
  accessToken = token;
};

// --- AXIOS INSTANCE ---
export const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// 1. Request Interceptor
apiClient.interceptors.request.use(
  (config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 2. Response Interceptor
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // [CRITICAL FIX] 
    // If the failed request was LOGIN, do NOT attempt refresh. 
    // Pass the original 401 error (Incorrect Password/Locked) directly to the UI.
    if (originalRequest.url?.includes("/auth/login")) {
      return Promise.reject(error);
    }

    // Ignore if no response or not 401 or already retried
    if (!error.response || error.response.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // If already refreshing, queue this request
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(originalRequest));
          },
          reject: (err: any) => {
            reject(err);
          },
        });
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // CSRF Hardening
      const refreshResponse = await axios.post(
        `${BASE_URL}/auth/refresh`,
        {},
        { 
          withCredentials: true,
          headers: { "X-Requested-With": "XMLHttpRequest" } 
        }
      );

      const newAccessToken = refreshResponse.data.access_token;
      setAccessToken(newAccessToken);
      
      processQueue(null, newAccessToken);
      
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return apiClient(originalRequest);

    } catch (refreshError) {
      processQueue(refreshError, null);
      setAccessToken(null);
      // Optional: Force redirect if not on login page
      if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
         window.location.href = "/admin/login";
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);