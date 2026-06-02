import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { generateParams } from '../services/llmService';
import { createWork } from '../services/workService';
import { addDiary } from '../services/diaryService';
import { toneEngine } from '../engine/toneEngine';
import { MOOD_OPTIONS, INSTRUMENTS, type MusicParams } from '../types';
import { useAuth } from '../hooks/useAuth';
import { Sparkles, Play, Square, Upload, ArrowLeft } from 'lucide-react';

const DEFAULT_PARAMS: MusicParams = {
  scale: 'C_major', tempo: 72, chord_progression: ['Cmaj7', 'Am7', 'Fmaj7', 'G7'],
  rhythm_style: 'flowing_arpeggio', melody_contour: 'wavelike_calm', instrument: 'piano',
  mood: 'calm', description: ''
};

export default function CreatePage() {
  const [search] = useSearchParams();
  const replyTo = search.get('reply_to');
  const replyTitle = search.get('reply_title') || '';
  const replyUser = search.get('reply_user') || '';

  const [emotion, setEmotion] = useState('');
  const [params, setParams] = useState<MusicParams>(DEFAULT_PARAMS);
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [title, setTitle] = useState('');
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();
  const { isLoggedIn } = useAuth();

  const handleGenerate = async () => {
    if (!emotion.trim()) return;
    setLoading(true);
    generateParams(emotion).then(p => {
      setParams(p);
      toneEngine.init().then(() => toneEngine.loadParams(p));
    }).finally(() => setLoading(false));
  };

  const handlePlay = async () => {
    await toneEngine.init();
    toneEngine.loadParams(params);
    if (playing) { toneEngine.stop(); setPlaying(false); }
    else { toneEngine.play(); setPlaying(true); }
  };

  const handlePublish = async () => {
    if (!isLoggedIn) { navigate('/login'); return; }
    if (!title.trim()) return;
    setSaving(true);
    createWork({
      title, mood_tag: params.mood, params_json: JSON.stringify(params),
      reply_to_work_id: replyTo ? Number(replyTo) : undefined, description: emotion.slice(0, 100)
    }).then(work => {
      addDiary({ mood_tag: params.mood, mood_score: 5, note: emotion, work_id: work.id }).catch(() => {});
      toneEngine.stop();
      navigate('/square');
    }).finally(() => setSaving(false));
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {replyTo && (
        <div className="glass rounded-xl p-3 flex items-center gap-3 text-sm">
          <ArrowLeft size={16} className="text-primary" />
          <span className="text-text-secondary">回应</span>
          <span className="font-medium text-text-main">@{replyUser}</span>
          <span className="text-text-muted">的《{replyTitle}》</span>
        </div>
      )}

      <div className="glass rounded-2xl p-6 space-y-4">
        <label className="block text-sm font-medium text-text-main">写下你的心情</label>
        <textarea
          value={emotion} onChange={e => setEmotion(e.target.value)}
          placeholder="写下你的心情，AI 帮你谱成曲...&#10;例：雨天的思念，淡淡的忧伤但又有一丝希望"
          className="w-full h-28 px-4 py-3 rounded-xl bg-surface-warm border-0 outline-none focus:ring-2 focus:ring-primary/30 resize-none text-text-main"
        />
        <button onClick={handleGenerate} disabled={loading || !emotion.trim()}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl gradient-warm text-white font-medium hover:opacity-90 disabled:opacity-50 transition-all">
          {loading ? (
            <span className="flex items-center gap-2"><span className="animate-spin">🎵</span> AI 解析中...</span>
          ) : (
            <><Sparkles size={16} /> AI 解析</>
          )}
        </button>
      </div>

      <div className="glass rounded-2xl p-6 space-y-5">
        <h3 className="font-semibold text-text-main">音乐参数</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-text-muted mb-1 block">调式</label>
            <select value={params.scale} onChange={e => setParams({ ...params, scale: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-surface-warm text-sm outline-none">
              {['C_major','D_minor','A_minor','F_major','G_major','E_minor'].map(s => (
                <option key={s} value={s}>{s.replace('_',' ')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-text-muted mb-1 block">速度</label>
            <input type="range" min={40} max={180} value={params.tempo}
              onChange={e => { setParams({ ...params, tempo: Number(e.target.value) }); toneEngine.setTempo(Number(e.target.value)); }}
              className="w-full accent-primary" />
            <span className="text-xs text-text-secondary">{params.tempo} BPM</span>
          </div>
          <div>
            <label className="text-xs text-text-muted mb-1 block">乐器</label>
            <select value={params.instrument} onChange={e => setParams({ ...params, instrument: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-surface-warm text-sm outline-none">
              {INSTRUMENTS.map(i => <option key={i.value} value={i.value}>{i.icon} {i.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-text-muted mb-1 block">情绪</label>
            <select value={params.mood} onChange={e => setParams({ ...params, mood: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-surface-warm text-sm outline-none">
              {MOOD_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="text-xs text-text-muted mb-2 block">和弦进行</label>
          <div className="flex gap-2 flex-wrap">
            {params.chord_progression.map((chord, i) => (
              <input key={i} value={chord}
                onChange={e => {
                  const newChords = [...params.chord_progression];
                  newChords[i] = e.target.value;
                  setParams({ ...params, chord_progression: newChords });
                }}
                className="w-20 px-3 py-2 rounded-lg bg-surface-warm text-sm text-center outline-none focus:ring-2 focus:ring-primary/20"
              />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          <button onClick={handlePlay}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium transition-all ${
              playing ? 'bg-red-100 text-red-500' : 'glass text-primary hover:bg-primary/10'
            }`}>
            {playing ? <><Square size={16} /> 停止</> : <><Play size={16} /> 试听</>}
          </button>

          <div className="flex items-center gap-3">
            <input value={title} onChange={e => setTitle(e.target.value)}
              placeholder="给作品起个名字..." className="px-4 py-2 rounded-xl bg-surface-warm text-sm outline-none w-48" />
            <button onClick={handlePublish} disabled={saving || !title.trim()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl gradient-warm text-white font-medium hover:opacity-90 disabled:opacity-50 transition-all">
              <Upload size={16} /> {saving ? '发布中...' : '发布'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
