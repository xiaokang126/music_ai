import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getResonance } from '../services/resonanceService';
import type { ResonanceWork } from '../types';
import { Sparkles, Play, Heart } from 'lucide-react';
import { toneEngine } from '../engine/toneEngine';

export default function ResonancePage() {
  const [works, setWorks] = useState<ResonanceWork[]>([]);
  const [baseMood, setBaseMood] = useState('');
  const [playingId, setPlayingId] = useState<number | null>(null);

  useEffect(() => {
    getResonance().then(data => { setWorks(data.works); setBaseMood(data.base_mood); });
  }, []);

  const handlePlay = (work: ResonanceWork) => {
    if (playingId === work.id) { toneEngine.stop(); setPlayingId(null); return; }
    toneEngine.init().then(() => {
      toneEngine.loadParams(JSON.parse(work.params_json));
      toneEngine.play();
      setPlayingId(work.id);
    });
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center mb-4">
        <h1 className="text-2xl font-bold flex items-center justify-center gap-2">
          <Sparkles size={24} className="text-amber-400" /> 情绪共鸣
        </h1>
        <p className="text-text-muted mt-2">AI 找到这些和你同频的音乐...</p>
        {baseMood && <span className="inline-block mt-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">当前情绪：{baseMood}</span>}
      </div>

      <div className="grid gap-4">
        {works.map(w => (
          <div key={w.id} className="glass rounded-2xl p-5 card-hover flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-8 h-8 rounded-full gradient-warm flex items-center justify-center text-white text-xs font-bold">{w.username?.[0]}</div>
                <span className="text-sm text-text-muted">@{w.username}</span>
              </div>
              <Link to={`/work/${w.id}`} className="font-medium text-text-main hover:text-primary">{w.title}</Link>
              <div className="flex items-center gap-3 mt-2">
                <button onClick={() => handlePlay(w)} className={`flex items-center gap-1 text-xs ${playingId === w.id ? 'text-primary' : 'text-text-muted hover:text-primary'}`}>
                  <Play size={14} fill={playingId === w.id ? '#E8916A' : 'none'} /> 播放
                </button>
                <span className="text-xs text-text-muted flex items-center gap-1"><Heart size={12} /> {w.likes_count}</span>
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-lg font-bold text-primary">{w.match_score}%</div>
              <div className="text-xs text-text-muted">匹配度</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
