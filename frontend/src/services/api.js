import axios from "axios";

function toApiV1Base(rawBase = "") {
  const cleaned = String(rawBase || "").trim().replace(/\/+$/, "");
  if (!cleaned) return "";
  return cleaned.endsWith("/api/v1") ? cleaned : `${cleaned}/api/v1`;
}

const API_V1_URL = toApiV1Base(process.env.REACT_APP_API_URL);

const api = axios.create({
  baseURL: API_V1_URL,
  timeout: 15000,
});

let isRefreshing = false;
let refreshQueue = [];
let isRedirectingToLogin = false;

const AUTH_ENDPOINTS = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];

function isAuthEndpoint(url = "") {
  return AUTH_ENDPOINTS.some((path) => url.includes(path));
}

function clearAuthStorageAndRedirectToLogin() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("auth_user");
  delete api.defaults.headers.common.Authorization;

  const isAuthPage = window.location.pathname.startsWith("/login") || window.location.pathname.startsWith("/register");
  if (isAuthPage) {
    isRedirectingToLogin = false;
    return;
  }

  if (isRedirectingToLogin) {
    return;
  }

  isRedirectingToLogin = true;
  window.location.replace("/login");
}

function resolveQueue(error, token = null) {
  refreshQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else {
      promise.resolve(token);
    }
  });
  refreshQueue = [];
}

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && isAuthEndpoint(originalRequest?.url)) {
      clearAuthStorageAndRedirectToLogin();
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest?._retry) {
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        clearAuthStorageAndRedirectToLogin();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post(`${api.defaults.baseURL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        localStorage.setItem("access_token", data.access_token);
        if (data.refresh_token) {
          localStorage.setItem("refresh_token", data.refresh_token);
        }
        if (data.user) {
          localStorage.setItem("auth_user", JSON.stringify(data.user));
        }
        api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
        resolveQueue(null, data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        resolveQueue(refreshError, null);
        clearAuthStorageAndRedirectToLogin();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (error.response?.status === 401) {
      clearAuthStorageAndRedirectToLogin();
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  register: (payload) => api.post("/auth/register", payload),
  login: (payload) => axios.post(`${API_V1_URL}/auth/login`, payload),
  refresh: (payload) => api.post("/auth/refresh", payload),
  logout: (refreshToken) => api.post("/auth/logout", null, { headers: refreshToken ? { "X-Refresh-Token": refreshToken } : {} }),
  me: () => api.get("/auth/me"),
};

export const claimsApi = {
  list: (params) => api.get("/claims", { params }),
  get: (claimId) => api.get(`/claims/${claimId}`),
  create: (payload) => api.post("/claims", payload),
  createWithForm: (formData) => api.post("/claims", formData),
  update: (claimId, payload) => api.put(`/claims/${claimId}`, payload),
  remove: (claimId) => api.delete(`/claims/${claimId}`),
  uploadImage: (claimId, formData) => api.post(`/claims/${claimId}/images`, formData),
  listImages: (claimId) => api.get(`/claims/${claimId}/images`),
};

export const fraudApi = {
  predict: (claimId) => api.post("/fraud/predict", { claim_id: claimId }),
  status: (claimId) => api.get(`/fraud/status/${claimId}`),
  results: (claimId) => api.get(`/fraud/results/${claimId}`),
  batch: (claimIds) => api.post("/fraud/batch", { claim_ids: claimIds }),
};

export const imageApi = {
  upload: (formData) => api.post("/images/upload", formData),
  batchUpload: (formData) => api.post("/images/batch-upload", formData),
  damage: (imageId) => api.get(`/images/${imageId}/damage`),
  visualization: (imageId) => `${api.defaults.baseURL}/images/${imageId}/visualization`,
};

export const reportApi = {
  generate: (claimId) => api.post(`/reports/generate/${claimId}`),
  list: (params) => api.get("/reports", { params }),
  get: (reportId) => api.get(`/reports/${reportId}`, { responseType: "blob" }),
  latestForClaim: (claimId) => api.get(`/reports/claim/${claimId}`),
};

export const adminApi = {
  stats: () => api.get("/admin/dashboard/stats"),
  logs: (params) => api.get("/admin/logs", { params }),
  models: () => api.get("/admin/ml-models"),
  surveyors: () => api.get("/admin/surveyors"),
  claims: (params) => api.get("/admin/claims", { params }),
  reports: (params) => api.get("/admin/reports", { params }),
};

export const dashboardApi = {
  stats: () => api.get("/dashboard/stats"),
  trends: () => api.get("/dashboard/trends"),
  highRisk: () => api.get("/dashboard/high-risk"),
  recentActivity: () => api.get("/dashboard/recent-activity"),
};

export default api;
