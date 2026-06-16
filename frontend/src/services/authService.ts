import api from '../lib/api';
import type { User } from '../types';

interface AuthResponse {
  token: string;
  user: User;
}

export async function registerUser(username: string, password: string): Promise<AuthResponse> {
  const res = await api.post('/auth/register', { username, password });
  return res.data;
}

export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  const res = await api.post('/auth/login', { username, password });
  return res.data;
}

export async function getMe(): Promise<User> {
  const res = await api.get('/auth/me');
  return res.data;
}

export async function updateMe(payload: { username?: string; avatar_url?: string }): Promise<User> {
  const res = await api.patch('/auth/me', payload);
  return res.data;
}
