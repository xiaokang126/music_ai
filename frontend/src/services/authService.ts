import api from '../lib/api';
import type { User } from '../types';

export async function registerUser(username: string, password: string): Promise<{ access_token: string; user: User }> {
  const res = await api.post('/auth/register', { username, password });
  return res.data;
}

export async function loginUser(username: string, password: string): Promise<{ access_token: string; user: User }> {
  const res = await api.post('/auth/login', { username, password });
  return res.data;
}
