import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getWorks, likeWork } from '../services/workService';
import { MOOD_OPTIONS, type MusicWork } from '../types';
import { Play, Heart, MessageCircle, Gift, PlusCircle, Music as MusicIcon } from 'lucide-react';
import { toneEngine } from '../engine/toneEngine';

export default function SquarePage() {
  const [works, setWorks] = useState<MusicWork[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState('latest');
  const [mood, setMood] = useState('');
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    getWorks(page, sort, mood, search).then(data => {
      setWorks(data.works);
      setTotal(data.total);
    });
  }, [page, sort, mood, search]);

  const handlePlay = (work: MusicWork) => {
    if (playingId === work.id) {
      toneEngine.stop();
      setPlayingId(null);
      return;
    }
    toneEngine.init().then(() => {
      const params = JSON.parse(work.params_json);
      toneEngine.loadParams(params);
      toneEngine.play();
      setPlayingId(work.id);
    });
  };

  const handleLike = async (id: number) => {
    await likeWork(id);
    setWorks(prev => prev.map(w => w.id === id ? { ...w, likes_count: w.likes_count + 1 } : w));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <MusicIcon size={24} className="text-primary" /> 音乐广场
        </h1>
        <Link to="/create" className="flex items-center gap-2 px-4 py-2 rounded-xl gradient-warm text-white text-sm font-medium hover:opacity-90">
          <PlusCircle size={16} /> 发布我的音乐
        </Link>
      </div>

      <div className="flex gap-2 flex-wrap">
        <input
          type="text" value={search} onChange={e => setSearch(e.target.value)}
          placeholder="搜索作品..." className="px-4 py-2 rounded-xl bg-white/60 border-0 text-sm outline-none focus:ring-2 focus:ring-primary/20 w-44"
        />
        {['最新', '热门'].map(s => (
          <button key={s} onClick={() => setSort(s === '最新' ? 'latest' : 'hot')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              (s === '最新' && sort === 'latest') || (s === '热门' && sort === 'hot')
                ? 'bg-primary text-white' : 'glass text-text-secondary hover:text-primary'
            }`}>{s}</button>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setMood('')}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${!mood ? 'bg-primary text-white' : 'glass text-text-secondary'}`}>全部</button>
        {MOOD_OPTIONS.map(m => (
          <button key={m.value} onClick={() => setMood(mood === m.value ? '' : m.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
              mood === m.value ? 'text-white' : 'glass text-text-secondary hover:text-primary'
            }`}
            style={mood === m.value ? { backgroundColor: m.color } : {}}
          >{m.label}</button>
        ))}
      </div>

      <div className="grid gap-4">
        {works.map(work => (
          <div key={work.id} className="glass rounded-2xl overflow-hidden card-hover">
            <div className="flex">
              <div className="w-1.5 flex-shrink-0" style={{ backgroundColor: MOOD_OPTIONS.find(m => m.value === work.mood_tag)?.color || '#E8916A' }} />
              <div className="flex-1 p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full gradient-warm flex items-center justify-center text-white text-sm font-bold">{work.username?.[0]}</div>
                    <div>
                      <Link to={`/work/${work.id}`} className="font-medium text-text-main hover:text-primary transition-colors">{work.title}</Link>
                      <p className="text-xs text-text-muted">@{work.username}</p>
                    </div>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">{work.mood_tag}</span>
                </div>
                <p className="text-sm text-text-secondary mb-3">{work.description}</p>
                <div className="flex items-center gap-5">
                  <button onClick={() => handlePlay(work)}
                    className={`flex items-center gap-1.5 text-sm font-medium transition-colors ${playingId === work.id ? 'text-primary' : 'text-text-secondary hover:text-primary'}`}>
                    <Play size={16} fill={playingId === work.id ? '#E8916A' : 'none'} /> 播放
                  </button>
                  <button onClick={() => handleLike(work.id)}
                    className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-red-400 transition-colors">
                    <Heart size={16} /> {work.likes_count}
                  </button>
                  <Link to={`/work/${work.id}`} className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-primary transition-colors">
                    <MessageCircle size={16} /> {work.comment_count}
                  </Link>
                  <span className="flex items-center gap-1.5 text-sm text-text-muted">
                    <Gift size={16} /> {work.gift_count}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {total > 20 && (
        <div className="flex justify-center gap-3">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
            className="px-4 py-2 rounded-xl glass text-sm disabled:opacity-40">上一页</button>
          <span className="px-4 py-2 text-sm text-text-muted">{page} / {Math.ceil(total / 20)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 20)}
            className="px-4 py-2 rounded-xl glass text-sm disabled:opacity-40">下一页</button>
        </div>
      )}
    </div>
  );
}
