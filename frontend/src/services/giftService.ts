import api from '../lib/api';
import type { Gift, WorkGift } from '../types';

export async function getGifts() {
  const res = await api.get('/gifts');
  return res.data as Gift[];
}

export async function getWorkGifts(workId: number) {
  const res = await api.get(`/works/${workId}/gifts`);
  return res.data as WorkGift[];
}

export async function sendGift(workId: number, giftId: number) {
  const res = await api.post(`/works/${workId}/gifts`, { gift_id: giftId });
  return res.data;
}
