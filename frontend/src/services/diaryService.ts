import api from '../lib/api';
import type { EmotionDiary, ChartDataPoint } from '../types';

export async function getDiaryList(page = 1) {
  const res = await api.get('/diary', { params: { page } });
  return res.data as { entries: EmotionDiary[]; total: number };
}

export async function addDiary(data: { mood_tag: string; mood_score: number; note?: string; work_id?: number }) {
  const res = await api.post('/diary', data);
  return res.data as EmotionDiary;
}

export async function getMoodChart(days = 30) {
  const res = await api.get('/diary/chart', { params: { days } });
  return res.data as { points: ChartDataPoint[] };
}
