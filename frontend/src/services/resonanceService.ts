import api from '../lib/api';
import type { ResonanceWork } from '../types';

export async function getResonance(mood?: string) {
  const res = await api.get('/resonance/match', { params: { mood: mood || '' } });
  return res.data as { works: ResonanceWork[]; base_mood: string };
}
