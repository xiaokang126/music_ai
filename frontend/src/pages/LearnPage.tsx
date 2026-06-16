import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Music, Video, Wand2, Volume2, Mic, Palette, Lightbulb, Heart, Plus, X, AlertCircle } from 'lucide-react';
import { VIDEO_TYPE_LABELS, type VideoType } from '../types';
import api from '../lib/api';

const lessons = [
  { id: 'what-is', icon: Wand2, title: '什么是音乐配乐导演？', desc: '了解 MuseCut 的 Music Timeline 概念' },
  { id: 'choose-style', icon: Video, title: '如何为你的 vlog 选择配乐风格？', desc: '6 种风格模板详解' },
  { id: 'bpm-emotion', icon: Music, title: 'BPM 与情绪的关系', desc: '节奏速度如何影响观感' },
  { id: 'sfx-guide', icon: Volume2, title: '音效的力量——转场和卡点怎么用', desc: 'SFX 使用技巧' },
  { id: 'voice-ducking', icon: Mic, title: '人声避让——让你的旁白更清晰', desc: 'Ducking 原理和使用' },
  { id: 'chord-basics', icon: BookOpen, title: '和弦进行入门', desc: '基础乐理知识' },
];

const TEMPLATES: { style: VideoType; icon: string; desc: string; instruments: string; bpm: string; emotion: string }[] = [
  { style: 'healing_vlog', icon: '🌿', desc: '温暖治愈风——日常记录、旅行日志', instruments: '钢琴/吉他/Pad', bpm: '70-90', emotion: '平静→温暖→治愈' },
  { style: 'product_promo', icon: '🛍️', desc: '活力现代风——产品展示、带货视频', instruments: '电子/合成器/强鼓', bpm: '100-120', emotion: '兴奋→活力→催促' },
  { style: 'hype_edit', icon: '🔥', desc: '高能量卡点风——运动、混剪', instruments: '全乐队/电子/摇滚', bpm: '120-150', emotion: '激烈→高能量→爆发' },
  { style: 'campus_memory', icon: '🎓', desc: '青春温暖风——毕业视频、校园活动', instruments: '吉他/钢琴/轻鼓', bpm: '80-100', emotion: '温暖→怀旧→幸福' },
  { style: 'emotional_story', icon: '💫', desc: '情感深沉风——情感表达、故事叙述', instruments: '钢琴/弦乐/环境音', bpm: '60-85', emotion: '忧伤→深沉→克制' },
  { style: 'knowledge_edu', icon: '📚', desc: '理性专业风——知识讲解、科普内容', instruments: 'Lo-fi/合成器/Pad', bpm: '90-110', emotion: '冷静→专注→理性' },
];

const THEMES = ['校园','爱情','旅行','毕业','成长','告别','亲情','友情','故乡','梦想'];
const EMOTIONS = ['calm','warm','happy','intense','sad','excited','nostalgic','energetic'];

export default function LearnPage() {
  const navigate = useNavigate();
  const [inspirations, setInspirations] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ title: '', description: '', theme: '', emotion: 'warm', reference_url: '', tags: [] as string[] });

  useEffect(() => {
    api.get('/assets/inspiration?page_size=12').then(r => setInspirations(r.data.items || [])).catch(() => {});
  }, []);

  const refreshInspirations = async () => {
    try { const r = await api.get('/assets/inspiration?page_size=12'); setInspirations(r.data.items || []); } catch {}
  };

  const submitInspiration = async () => {
    if (!form.title.trim()) return;
    try {
      await api.post('/assets/inspiration', form);
      setShowForm(false);
      setForm({ title: '', description: '', theme: '', emotion: 'warm', reference_url: '', tags: [] });
      await refreshInspirations();
    } catch {
      setError('提交灵感失败，请重试');
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="relative mb-10 overflow-hidden rounded-lg bg-surface-dark text-white">
        <img
          src="/showcase/creative-lab.png"
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-25"
          aria-hidden="true"
        />
        <div className="relative max-w-3xl p-6 md:p-8">
          <p className="mb-3 text-sm font-semibold uppercase tracking-[0.22em] text-accent-light">Creative Lab</p>
          <h1 className="text-3xl font-bold leading-tight md:text-4xl">创作教学与导演灵感库</h1>
          <p className="mt-4 text-sm leading-6 text-white/80">
            学习作词、编曲、声音设计、短片叙事和剧本结构，也把真实故事、地方记忆和人物关系沉淀为可继续创作的素材。
          </p>
        </div>
      </div>

      {error && <div className="flex items-center gap-2 bg-red-50 text-red-600 rounded-xl px-4 py-3 mb-6 text-sm max-w-3xl mx-auto"><AlertCircle size={16} /> {error}</div>}

      {/* Lessons */}
      <h2 className="text-xl font-bold text-text-main mb-4 flex items-center gap-2"><BookOpen size={22} /> 创作课程</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
        {lessons.map(({ id, icon: Icon, title, desc }) => (
          <div key={id} onClick={() => navigate(`/learn/${id}`)} className="glass flex cursor-pointer gap-4 rounded-lg p-6 card-hover">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Icon size={24} className="text-primary" /></div>
            <div><h3 className="font-semibold text-text-main mb-1">{title}</h3><p className="text-sm text-text-muted">{desc}</p></div>
          </div>
        ))}
      </div>

      {/* Template Showcase */}
      <h2 className="text-xl font-bold text-text-main mb-4 flex items-center gap-2"><Palette size={22} /> 情绪与声音模板</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
        {TEMPLATES.map(({ style, icon, desc, instruments, bpm, emotion }) => (
          <div key={style} className="glass rounded-lg p-5 card-hover">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-2xl">{icon}</span>
              <h3 className="font-semibold text-text-main">{VIDEO_TYPE_LABELS[style]}</h3>
            </div>
            <p className="text-sm text-text-secondary mb-3">{desc}</p>
            <div className="space-y-1 text-xs text-text-muted">
              <p>🎵 乐器: {instruments}</p><p>⏱️ BPM: {bpm}</p><p>🎭 情绪弧: {emotion}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Inspiration Library */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-text-main flex items-center gap-2"><Lightbulb size={22} /> 灵感库</h2>
        <button onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 rounded-lg bg-primary/10 px-4 py-2 text-sm font-medium text-primary hover:bg-primary/20">
          {showForm ? <X size={16} /> : <Plus size={16} />} {showForm ? '取消' : '分享灵感'}
        </button>
      </div>

      {showForm && (
        <div className="glass mb-6 rounded-lg p-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input value={form.title} onChange={e => setForm({...form, title: e.target.value})}
              placeholder="灵感标题 *" className="rounded-lg bg-surface-warm px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
            <select value={form.theme} onChange={e => setForm({...form, theme: e.target.value})}
              className="bg-surface-warm rounded-lg px-3 py-2 text-sm">
              <option value="">选择主题</option>
              {THEMES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select value={form.emotion} onChange={e => setForm({...form, emotion: e.target.value})}
              className="bg-surface-warm rounded-lg px-3 py-2 text-sm">
              {EMOTIONS.map(e => <option key={e} value={e}>{e}</option>)}
            </select>
            <input value={form.reference_url} onChange={e => setForm({...form, reference_url: e.target.value})}
              placeholder="参考链接 (视频/音乐URL)" className="bg-surface-warm rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
            <div className="col-span-2">
              <textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})}
                placeholder="描述你的灵感..." rows={2}
                className="w-full bg-surface-warm rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 resize-none" />
            </div>
          </div>
          <button onClick={submitInspiration}
            className="mt-4 px-6 py-2.5 rounded-xl gradient-primary text-white text-sm font-medium hover:opacity-90">提交灵感</button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {inspirations.map((insp: any) => (
          <div key={insp.id} className="glass rounded-lg p-5 card-hover">
            <h3 className="font-semibold text-text-main mb-2">{insp.title}</h3>
            <p className="text-sm text-text-secondary mb-3 line-clamp-3">{insp.description}</p>
            <div className="flex flex-wrap gap-1 mb-3">
              {insp.theme && <span className="px-2 py-0.5 bg-primary/10 text-primary rounded text-[10px]">{insp.theme}</span>}
              {insp.emotion && <span className="px-2 py-0.5 bg-mood-warm/10 text-mood-warm rounded text-[10px]">{insp.emotion}</span>}
            </div>
            <div className="flex items-center justify-between text-xs text-text-muted">
              <button onClick={async () => {
                try {
                  await api.post(`/assets/inspiration/${insp.id}/like`);
                  await refreshInspirations();
                } catch {}
              }} className="flex items-center gap-1 hover:text-red-500"><Heart size={12} /> {insp.likes_count || 0}</button>
              <span>{insp.tags?.join(', ') || ''}</span>
            </div>
            {insp.reference_url && (
              <a href={insp.reference_url} target="_blank" rel="noreferrer"
                className="block mt-2 text-[10px] text-primary truncate hover:underline">{insp.reference_url}</a>
            )}
          </div>
        ))}
        {inspirations.length === 0 && !showForm && (
          <p className="col-span-full text-center text-text-muted py-8 text-sm">还没有灵感，快来分享第一个创作灵感吧！</p>
        )}
      </div>
    </div>
  );
}
