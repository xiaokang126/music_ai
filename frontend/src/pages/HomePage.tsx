import { Link } from 'react-router-dom';
import { BookOpen, Music, Sparkles, Heart, ArrowRight } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getWorks } from '../services/workService';
import type { MusicWork } from '../types';

export default function HomePage() {
  const [hotWorks, setHotWorks] = useState<MusicWork[]>([]);

  useEffect(() => {
    getWorks(1, 'hot').then(data => setHotWorks(data.works.slice(0, 3))).catch(() => {});
  }, []);

  const cards = [
    { to: '/theory', icon: BookOpen, title: '学乐理', desc: '从零基础开始，了解音阶、和弦与节奏', color: 'from-rose-300 to-rose-400' },
    { to: '/create', icon: Music, title: '去创作', desc: '写下你的心情，AI 帮你谱成旋律', color: 'from-primary to-orange-400' },
    { to: '/square', icon: Sparkles, title: '逛广场', desc: '聆听他人的音乐，用旋律彼此温暖', color: 'from-amber-300 to-amber-400' },
  ];

  return (
    <div className="space-y-10">
      <section className="text-center pt-8 pb-4">
        <div className="inline-flex items-center gap-3 mb-6 animate-float">
          <span className="text-5xl">💔</span>
          <span className="text-5xl">🎵</span>
          <span className="text-5xl">✨</span>
        </div>
        <h1 className="text-4xl font-bold mb-4">
          <span className="bg-gradient-to-r from-primary via-primary-light to-amber-400 bg-clip-text text-transparent">
            失恋广场
          </span>
        </h1>
        <p className="text-lg text-text-secondary max-w-md mx-auto leading-relaxed">
          在这里，每一种情绪都值得被听见<br />
          用音乐书写心情，让旋律治愈彼此
        </p>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-5 max-w-3xl mx-auto">
        {cards.map(({ to, icon: Icon, title, desc, color }) => (
          <Link key={to} to={to} className="group">
            <div className="glass rounded-2xl p-6 card-hover cursor-pointer h-full flex flex-col items-center text-center gap-3">
              <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${color} flex items-center justify-center text-white shadow-lg`}>
                <Icon size={26} />
              </div>
              <h3 className="text-lg font-semibold text-text-main group-hover:text-primary transition-colors">{title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">{desc}</p>
            </div>
          </Link>
        ))}
      </section>

      {hotWorks.length > 0 && (
        <section className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Heart size={18} className="text-red-400" /> 热门旋律
            </h2>
            <Link to="/square" className="text-sm text-primary hover:underline flex items-center gap-1">
              逛广场 <ArrowRight size={14} />
            </Link>
          </div>
          <div className="grid gap-4">
            {hotWorks.map(w => (
              <Link key={w.id} to={`/work/${w.id}`}>
                <div className="glass rounded-xl p-4 card-hover flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg gradient-warm flex items-center justify-center text-white font-bold text-sm">
                    {w.username?.[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-text-main truncate">{w.title}</p>
                    <p className="text-xs text-text-muted">@{w.username} · {w.likes_count} ❤️</p>
                  </div>
                  <div className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">{w.mood_tag}</div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="text-center pb-8">
        <Link to="/healing" className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl glass card-hover text-primary font-medium">
          <Heart size={18} /> 开启治愈计划
        </Link>
      </section>
    </div>
  );
}
