import { useEffect, useState } from 'react';
import { getPlans, startPlan, getMyPlan, completeTask } from '../services/healingService';
import type { HealingPlan, UserHealingPlan } from '../types';
import { Heart, Check, Star, Trophy, Sparkles } from 'lucide-react';

export default function HealingPage() {
  const [plans, setPlans] = useState<HealingPlan[]>([]);
  const [myPlan, setMyPlan] = useState<UserHealingPlan | null>(null);
  const [showBadge, setShowBadge] = useState(false);

  useEffect(() => {
    getPlans().then(setPlans);
    getMyPlan().then(setMyPlan).catch(() => {});
  }, []);

  const handleStart = async (planId: number) => {
    const r = await startPlan(planId);
    setMyPlan({ ...r, plan_name: plans.find(p => p.id === planId)?.name || '' });
  };

  const handleComplete = async (day: number) => {
    if (!myPlan) return;
    await completeTask(myPlan.id, day);
    const updated = await getMyPlan();
    setMyPlan(updated);
    if (updated.is_completed === 1) setShowBadge(true);
  };

  const completedDays = myPlan ? JSON.parse(myPlan.completed_tasks_json || '[]') as number[] : [];
  const tasks = myPlan ? JSON.parse(myPlan.tasks_json || '[]') as Array<{ day: number; task: string; tip: string }> : [];

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <Heart size={24} className="text-red-400" /> 治愈计划
      </h1>

      {myPlan ? (
        <div className="glass rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-text-main">{myPlan.plan_name}</h2>
              <p className="text-sm text-text-muted">第 {myPlan.current_day} 天 / 共 {myPlan.duration_days} 天</p>
            </div>
            <div className="text-3xl">{myPlan.is_completed === 1 ? '🏆' : '🌱'}</div>
          </div>

          <div className="w-full bg-surface-warm rounded-full h-3 overflow-hidden">
            <div className="h-full rounded-full gradient-warm transition-all duration-500"
              style={{ width: `${(completedDays.length / myPlan.duration_days) * 100}%` }} />
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {tasks.map((t: { day: number; task: string; tip: string }) => (
              <div key={t.day}
                className={`rounded-xl p-3 flex items-start gap-3 transition-all ${
                  completedDays.includes(t.day) ? 'bg-green-50' : 'bg-surface-warm'
                }`}>
                <button onClick={() => !completedDays.includes(t.day) && handleComplete(t.day)}
                  disabled={completedDays.includes(t.day)}
                  className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 transition-all ${
                    completedDays.includes(t.day) ? 'bg-green-400 text-white' : 'border-2 border-text-muted text-transparent hover:border-primary'
                  }`}>
                  {completedDays.includes(t.day) && <Check size={12} />}
                </button>
                <div className="flex-1">
                  <p className={`text-sm ${completedDays.includes(t.day) ? 'text-green-700 line-through' : 'text-text-main'}`}>
                    第{t.day}天：{t.task}
                  </p>
                  {!completedDays.includes(t.day) && <p className="text-xs text-text-muted mt-0.5">💡 {t.tip}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-5">
          {plans.map(p => (
            <div key={p.id} className="glass rounded-2xl p-6 card-hover text-center space-y-4">
              <span className="text-4xl">{p.cover_icon === '🌅' ? '🌅' : p.cover_icon === '🌻' ? '🌻' : '🌟'}</span>
              <h3 className="text-lg font-semibold text-text-main">{p.name}</h3>
              <p className="text-sm text-text-secondary">{p.description}</p>
              <span className="text-xs px-3 py-1 rounded-full bg-primary/10 text-primary">{p.duration_days}天</span>
              <button onClick={() => handleStart(p.id)}
                className="w-full py-2.5 rounded-xl gradient-warm text-white text-sm font-medium hover:opacity-90">
                开始旅程
              </button>
            </div>
          ))}
        </div>
      )}

      {showBadge && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setShowBadge(false)}>
          <div className="glass rounded-3xl p-8 text-center max-w-sm mx-4 animate-float">
            <div className="text-6xl mb-4">🏆</div>
            <h3 className="text-xl font-bold text-text-main mb-2">恭喜完成！</h3>
            <p className="text-text-secondary mb-4">你走完了这段治愈之旅，音乐见证了你的成长</p>
            <Star size={40} className="mx-auto text-amber-400" />
          </div>
        </div>
      )}
    </div>
  );
}
