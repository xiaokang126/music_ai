import api from '../lib/api';
import type { MusicWork } from '../types';

export async function getWorks(page = 1, sort = 'latest', mood = '', search = '') {
  const res = await api.get('/works', { params: { page, page_size: 20, sort, mood, search } });
  return res.data as { works: MusicWork[]; total: number; page: number; page_size: number };
}

export async function createWork(data: {
  title: string; mood_tag: string; params_json: string;
  reply_to_work_id?: number; description?: string;
}) {
  const res = await api.post('/works', data);
  return res.data as MusicWork;
}

export async function getWorkDetail(workId: number) {
  const res = await api.get(`/works/${workId}`);
  return res.data as MusicWork & { replies: MusicWork[] };
}

export async function likeWork(workId: number) {
  const res = await api.post(`/works/${workId}/like`);
  return res.data;
}

export async function deleteWork(workId: number) {
  return api.delete(`/works/${workId}`);
}
