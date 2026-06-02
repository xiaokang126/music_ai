import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { getWorks, deleteWork } from '../services/workService';
import { getDiaryList } from '../services/diaryService';
import type { MusicWork } from '../types';
import { Music, Heart, BookOpen, Gift, Music as MusicIcon, Trash2 } from 'lucide-react';

export default function ProfilePage() {
  const { user, isLoggedIn } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState('works');
  const [works, setWorks] = useState<MusicWork[]>([]);
  const [diaries, setDiaries] = useState<any[]>([]);

  useEffect(() => {
    if (!isLoggedIn) { navigate('/login'); return; }
    if (tab === 'works') getWorks(1, 'latest', '', '').then(d => setWorks(d.works));
    if (tab === 'diary') getDiaryList().then(d => setDiaries(d.entries));
  }, [tab, isLoggedIn]);

  if (!user) return null;

  const tabs = [
    { key: 'works', label: '我的作品', icon: Music },
    { key: 'diary', label: '情绪日记', icon: BookOpen },
  ];

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="glass rounded-2xl p-6 flex items-center gap-4">
        <div className="w-16 h-16 rounded-full gradient-warm flex items-center justify-center text-white font-bold text-2xl">{user.username[0]}</div>
        <div>
          <h1 className="text-xl font-bold text-text-main">{user.username}</h1>
          <p className="text-sm text-text-muted">加入于 {new Date(user.created_at).toLocaleDateString()}</p>
        </div>
      </div>

      <div className="flex gap-2">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium ${
              tab === t.key ? 'bg-primary text-white' : 'glass text-text-secondary'
            }`}><t.icon size={14} />{t.label}</button>
        ))}
      </div>

      {tab === 'works' && (
        <div className="space-y-3">
          {works.map(w => (
            <div key={w.id} className="glass rounded-xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">🎵</span>
                <div>
                  <Link to={`/work/${w.id}`} className="font-medium text-text-main hover:text-primary">{w.title}</Link>
                  <div className="flex gap-3 text-xs text-text-muted mt-0.5">
                    <span>❤️ {w.likes_count}</span>
                    <span>💬 {w.comment_count}</span>
                    <span>{w.mood_tag}</span>
                  </div>
                </div>
              </div>
              <button onClick={() => deleteWork(w.id).then(() => setWorks(prev => prev.filter(x => x.id !== w.id)))}
                className="p-2 rounded-lg hover:bg-red-50 text-text-muted hover:text-red-400 transition-colors">
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      {tab === 'diary' && (
        <div className="space-y-3">
          {diaries.map((e: any) => (
            <div key={e.id} className="glass rounded-xl p-4">{e.mood_tag} · {e.mood_score}分 · {e.note?.slice(0, 50)}</div>
          ))}
        </div>
      )}
    </div>
  );
}
