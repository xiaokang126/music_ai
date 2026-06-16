import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  Film,
  Heart,
  Library,
  Mic,
  Music2,
  PenLine,
  Play,
  Sparkles,
  Trophy,
  Users,
  Wand2,
} from 'lucide-react';
import type { VideoType } from '../types';

const expressionModes: {
  label: string;
  type: VideoType;
  prompt: string;
  icon: typeof Heart;
}[] = [
  { label: '想念与告别', type: 'emotional_story', prompt: '我想把一段想念、告别或和解做成一支有留白的短片。', icon: Heart },
  { label: '校园与成长', type: 'campus_memory', prompt: '我想记录一次校园活动、毕业回忆或成长片段。', icon: Film },
  { label: '日常与旅行', type: 'healing_vlog', prompt: '我想把普通日常、旅行碎片或生活记录做得更温柔。', icon: Music2 },
  { label: '旁白与知识', type: 'knowledge_edu', prompt: '我想让讲述内容更清楚，同时保留轻微的情绪氛围。', icon: Mic },
];

const platformPaths = [
  {
    icon: Wand2,
    title: 'AI 配乐导演',
    body: '把镜头、字幕、人声和关键事件整理成可编辑的声音时间轴。',
  },
  {
    icon: PenLine,
    title: '情感音乐表达',
    body: '从一段心情出发，获得歌词方向、和弦情绪、配器和旋律动机。',
  },
  {
    icon: Users,
    title: '故事社区',
    body: '发布音乐、影像故事和创作过程，参与主题征集与每周精选。',
  },
  {
    icon: Library,
    title: '导演灵感库',
    body: '沉淀真实故事、人物关系、地方记忆和可改编的创作素材。',
  },
  {
    icon: BookOpen,
    title: 'AI 创作教学',
    body: '学习作词、声音设计、短片叙事和剧本结构，让创作更可控。',
  },
];

const showcases = [
  {
    title: '记忆影像',
    image: '/showcase/timeline-studio.png',
    caption: '家庭、校园、旅行片段被整理成情绪清晰的声音叙事。',
  },
  {
    title: '社区故事',
    image: '/showcase/community-stories.png',
    caption: '真实表达可以被看见、收藏、讨论，也能成为新的创作灵感。',
  },
  {
    title: '创作教学',
    image: '/showcase/creative-lab.png',
    caption: '把情绪、文字、旁白和镜头转化为可执行的创作方案。',
  },
];

const demoCases = [
  { title: '校园 vlog', body: '平静开场，温暖高潮，柔和收束。', tone: 'bg-primary/10 text-primary' },
  { title: '商品种草', body: '产品、价格、引导节点分别触发声音强调。', tone: 'bg-amber-100 text-amber-800' },
  { title: '高燃剪辑', body: '密集转场、鼓点和 whoosh 形成卡点推进。', tone: 'bg-accent/10 text-accent' },
  { title: '情绪短片', body: '保留原声和留白，让独白与音乐自然呼吸。', tone: 'bg-mood-sad/10 text-mood-sad' },
];

export default function HomePage() {
  const navigate = useNavigate();
  const [storySeed, setStorySeed] = useState('');
  const [selectedMode, setSelectedMode] = useState(expressionModes[0]);

  const startCreation = () => {
    localStorage.setItem('musecut_expression_mode', selectedMode.type);
    localStorage.setItem('musecut_story_seed', storySeed.trim() || selectedMode.prompt);
    navigate('/upload');
  };

  return (
    <div className="bg-surface-bg text-text-main">
      <section className="relative min-h-[74vh] overflow-hidden">
        <img
          src="/showcase/musecut-hero.png"
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
          aria-hidden="true"
        />
        <div className="absolute inset-0 bg-[#17212b]/75" />
        <div className="relative mx-auto flex min-h-[74vh] max-w-6xl flex-col justify-center px-4 py-16">
          <div className="max-w-3xl">
            <p className="mb-5 inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm font-medium text-white/90">
              <Sparkles size={16} />
              面向情感表达创作者的 AI 声音叙事平台
            </p>
            <h1 className="mb-6 text-5xl font-bold leading-none text-white md:text-7xl">
              MuseCut
            </h1>
            <p className="mb-8 max-w-2xl text-lg leading-8 text-white/80 md:text-xl">
              用音乐、影像、文字和声音讲述爱情、亲情、友情、成长与告别。AI 负责整理素材与编排声音，故事始终属于你自己。
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={startCreation}
                className="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 font-semibold text-surface-dark transition hover:bg-white/90"
              >
                开始表达 <ArrowRight size={18} />
              </button>
              <button
                onClick={() => navigate('/community')}
                className="inline-flex items-center gap-2 rounded-lg border border-white/40 px-6 py-3 font-semibold text-white transition hover:bg-white/10"
              >
                进入故事社区 <Users size={18} />
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto -mt-10 grid max-w-6xl gap-4 px-4 pb-14 md:grid-cols-[1.15fr_0.85fr]">
        <div className="relative z-10 rounded-lg border border-black/10 bg-white p-5 shadow-xl shadow-black/10">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Expression Desk</p>
              <h2 className="mt-1 text-2xl font-bold">今天想表达什么？</h2>
            </div>
            <Heart className="text-accent" size={28} />
          </div>
          <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4">
            {expressionModes.map((mode) => {
              const Icon = mode.icon;
              const active = selectedMode.label === mode.label;
              return (
                <button
                  key={mode.label}
                  onClick={() => setSelectedMode(mode)}
                  className={`flex min-h-20 flex-col items-start justify-between rounded-lg border px-3 py-3 text-left transition ${
                    active
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-black/10 bg-surface-bg text-text-secondary hover:border-primary/30'
                  }`}
                >
                  <Icon size={18} />
                  <span className="text-sm font-semibold">{mode.label}</span>
                </button>
              );
            })}
          </div>
          <textarea
            value={storySeed}
            onChange={(event) => setStorySeed(event.target.value)}
            rows={4}
            className="w-full resize-none rounded-lg border border-black/10 bg-surface-bg px-4 py-3 text-sm leading-6 text-text-main outline-none transition placeholder:text-text-muted focus:border-primary"
            placeholder={selectedMode.prompt}
          />
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-text-muted">这段文字会带到创作页，作为视频、旁白和声音时间轴的情感线索。</p>
            <button
              onClick={startCreation}
              className="inline-flex items-center gap-2 rounded-lg gradient-primary px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-primary/20"
            >
              去创作 <ArrowRight size={16} />
            </button>
          </div>
        </div>

        <div className="relative z-10 rounded-lg bg-surface-dark p-5 text-white shadow-xl shadow-black/10">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">MVP 演示主线</h2>
            <Play size={22} className="text-accent-light" />
          </div>
          <div className="mt-5 space-y-3">
            {demoCases.map((item) => (
              <div key={item.title} className="rounded-lg bg-white/10 p-4">
                <span className={`mb-2 inline-flex rounded-md px-2 py-1 text-xs font-semibold ${item.tone}`}>
                  {item.title}
                </span>
                <p className="text-sm leading-6 text-white/80">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-black/10 bg-white py-14">
        <div className="mx-auto max-w-6xl px-4">
          <div className="mb-8 flex flex-col justify-between gap-3 md:flex-row md:items-end">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-accent">Platform</p>
              <h2 className="mt-2 text-3xl font-bold">从声音工具走向情感表达平台</h2>
            </div>
            <p className="max-w-2xl text-sm leading-6 text-text-secondary">
              计划书中的核心不是单次生成，而是让用户完成作品、获得交流、继续学习，并沉淀真实故事。
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-5">
            {platformPaths.map(({ icon: Icon, title, body }) => (
              <div key={title} className="rounded-lg border border-black/10 bg-surface-bg p-4">
                <Icon className="mb-4 text-primary" size={24} />
                <h3 className="mb-2 font-bold">{title}</h3>
                <p className="text-sm leading-6 text-text-secondary">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14">
        <div className="mb-8 flex flex-col justify-between gap-3 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary">Showcase</p>
            <h2 className="mt-2 text-3xl font-bold">表达可以有很多入口</h2>
          </div>
          <button
            onClick={() => navigate('/learn')}
            className="inline-flex items-center gap-2 self-start rounded-lg border border-black/10 px-4 py-2 text-sm font-semibold text-text-main transition hover:border-primary hover:text-primary md:self-auto"
          >
            查看创作教学 <BookOpen size={16} />
          </button>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {showcases.map((item) => (
            <article key={item.title} className="overflow-hidden rounded-lg border border-black/10 bg-white">
              <img src={item.image} alt="" className="h-48 w-full object-cover" aria-hidden="true" />
              <div className="p-5">
                <h3 className="mb-2 text-lg font-bold">{item.title}</h3>
                <p className="text-sm leading-6 text-text-secondary">{item.caption}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-surface-dark py-14 text-white">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 md:grid-cols-[0.8fr_1.2fr] md:items-center">
          <div>
            <p className="mb-3 inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm font-semibold text-white/90">
              <Trophy size={16} />
              每周主题征集
            </p>
            <h2 className="text-3xl font-bold leading-tight">让真实故事被听见，也能被二次创作。</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {['给一段想念配声音', '我的校园告别片', '家乡与旧照片'].map((topic) => (
              <button
                key={topic}
                onClick={() => navigate('/community')}
                className="rounded-lg border border-white/20 bg-white/10 p-4 text-left text-sm font-semibold text-white transition hover:bg-white/20"
              >
                {topic}
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
