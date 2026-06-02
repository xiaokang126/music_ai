import api from '../lib/api';
import type { MusicParams } from '../types';

export async function generateParams(emotionText: string): Promise<MusicParams> {
  const res = await api.post('/llm/generate-params', { emotion_text: emotionText });
  return res.data;
}
