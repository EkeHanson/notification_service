import axios from "axios";

const config = {
  WEB_PAGE__URL: import.meta.env.VITE_WEB_PAGE_URL,
  API_Documentation_URL: import.meta.env.VITE_API_DOCUMENTATION_URL,
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  WEBSOCKET_URL: import.meta.env.VITE_WEBSOCKET_URL,
};

export const API_BASE_URL = `${config.API_BASE_URL}`;
export const WEBSOCKET_URL = `${config.WEBSOCKET_URL}`;

// Create an axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add request interceptor to include auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired, clear local storage
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      localStorage.removeItem("user");
      // Redirect to login
      window.location.href = "/";
    }
    return Promise.reject(error);
  }
);

export default config;