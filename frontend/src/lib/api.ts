import axios from 'axios';
import { formatApiError, recordClientError } from './errorUtils';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const detail = err.response?.data?.detail;
    const authMissing = status === 401 || (status === 403 && detail === 'Not authenticated');
    if (authMissing) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
    const message = formatApiError(err, '接口请求失败', {
      url: err.config?.url,
      method: err.config?.method,
    });
    recordClientError('api.response', message, err);
    return Promise.reject(err);
  }
);

export { api };
export default api;
