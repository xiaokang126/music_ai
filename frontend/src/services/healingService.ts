import api from '../lib/api';
import type { HealingPlan, UserHealingPlan } from '../types';

export async function getPlans() {
  const res = await api.get('/healing/plans');
  return res.data as HealingPlan[];
}

export async function startPlan(planId: number) {
  const res = await api.post('/healing/start', null, { params: { plan_id: planId } });
  return res.data;
}

export async function getMyPlan() {
  const res = await api.get('/healing/my');
  return res.data as UserHealingPlan;
}

export async function completeTask(uphId: number, day: number) {
  const res = await api.post(`/healing/tasks/${uphId}/complete`, null, { params: { day } });
  return res.data;
}
