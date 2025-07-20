// api.js or services.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000,
});

// Add request interceptor to inject token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default apiClient;
