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
    if (err.response?.status === 401) {
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
