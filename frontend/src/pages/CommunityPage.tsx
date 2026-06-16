import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  Bookmark,
  Clock,
  EyeOff,
  Flame,
  Heart,
  ImagePlus,
  MessageCircle,
  Music2,
  PenLine,
  Send,
  Settings,
  Share2,
  Sparkles,
  Shield,
  Trash2,
  Trophy,
  UserMinus,
  UserRound,
  X,
} from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../hooks/useAuth';
import { formatApiError, recordClientError } from '../lib/errorUtils';

const TAG_LIST = ['校园', '亲情', '告白', '旅行', '毕业', '成长', '告别', '友情', '爱情', '家乡'];

const TOPICS = [
  { title: '给一段想念配声音', tag: '告别', icon: Music2, tone: 'bg-blue-50 text-blue-700' },
  { title: '我的校园告别片', tag: '毕业', icon: Trophy, tone: 'bg-amber-50 text-amber-700' },
  { title: '一封影像家书', tag: '亲情', icon: PenLine, tone: 'bg-rose-50 text-rose-700' },
];

type RuleUser = { user_id: string; username: string; created_at?: string };
type CommunitySettings = { hidden_authors: RuleUser[]; blocked_viewers: RuleUser[] };

function parseTags(value: unknown): string[] {
  if (!value || typeof value !== 'string' || value === '[]') return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === 'string') : [];
  } catch {
    return [];
  }
}

function relativeTime(value?: string) {
  if (!value) return '刚刚';
  const diff = Date.now() - new Date(value).getTime();
  if (Number.isNaN(diff)) return '刚刚';
  const mins = Math.max(0, Math.floor(diff / 60000));
  if (mins < 1) return '刚刚';
  if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天前`;
  return new Date(value).toLocaleDateString();
}

function displayName(post: any) {
  return post.is_anonymous ? '匿名创作者' : (post.username || 'MuseCut 用户');
}

function avatarText(post: any) {
  if (post.is_anonymous) return '匿';
  return String(post.username || 'M').slice(0, 1).toUpperCase();
}

export default function CommunityPage() {
  const { user } = useAuth();
  const [posts, setPosts] = useState<any[]>([]);
  const [featured, setFeatured] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTag, setActiveTag] = useState('');
  const [error, setError] = useState('');
  const [composerText, setComposerText] = useState('');
  const [composerTitle, setComposerTitle] = useState('');
  const [composerTags, setComposerTags] = useState<string[]>(['校园']);
  const [anonymous, setAnonymous] = useState(false);
  const [posting, setPosting] = useState(false);
  const [copiedId, setCopiedId] = useState('');
  const [recentDays, setRecentDays] = useState(() => localStorage.getItem('musecut_community_recent_days') || 'all');
  const [showSettings, setShowSettings] = useState(true);
  const [settings, setSettings] = useState<CommunitySettings>({ hidden_authors: [], blocked_viewers: [] });
  const [hideUsername, setHideUsername] = useState('');
  const [blockUsername, setBlockUsername] = useState('');
  const [settingsBusy, setSettingsBusy] = useState(false);

  const loadFeed = async () => {
    setError('');
    setLoading(true);
    const params = new URLSearchParams({ page_size: '30' });
    if (activeTag) params.set('tag', activeTag);
    if (recentDays !== 'all') params.set('recent_days', recentDays);
    try {
      const [feedRes, featuredRes] = await Promise.all([
        api.get(`/community/posts?${params.toString()}`),
        api.get('/community/featured').catch(() => ({ data: [] })),
      ]);
      setPosts(feedRes.data.posts || []);
      setFeatured(Array.isArray(featuredRes.data) ? featuredRes.data : []);
    } catch (e: any) {
      const message = formatApiError(e, '加载故事社区失败', { action: 'load_community_feed', activeTag, recentDays });
      recordClientError('community.load_feed', message, e);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const loadSettings = async () => {
    if (!user) return;
    try {
      const r = await api.get('/community/settings');
      setSettings(r.data || { hidden_authors: [], blocked_viewers: [] });
    } catch (e: any) {
      const message = formatApiError(e, '加载社区设置失败', { action: 'load_community_settings' });
      recordClientError('community.load_settings', message, e);
      setError(message);
    }
  };

  useEffect(() => {
    localStorage.setItem('musecut_community_recent_days', recentDays);
    loadFeed();
  }, [activeTag, recentDays]);

  useEffect(() => { loadSettings(); }, [user?.id]);

  const totals = useMemo(() => ({
    posts: posts.length,
    likes: posts.reduce((sum, post) => sum + (post.likes_count || 0), 0),
    comments: posts.reduce((sum, post) => sum + (post.comments_count || 0), 0),
  }), [posts]);

  const toggleComposerTag = (tag: string) => {
    setComposerTags(prev => prev.includes(tag) ? prev.filter(item => item !== tag) : [...prev, tag].slice(0, 4));
  };

  const handleCreatePost = async () => {
    const text = composerText.trim();
    if (!text) return;
    setPosting(true);
    setError('');
    try {
      await api.post('/community/posts', {
        title: composerTitle.trim() || text.slice(0, 24) || '一条 MuseCut 动态',
        description: text,
        content: text,
        story_tags: composerTags,
        is_anonymous: anonymous,
      });
      setComposerText('');
      setComposerTitle('');
      await loadFeed();
    } catch (e: any) {
      const message = formatApiError(e, '发布动态失败', { action: 'create_community_post', anonymous, tags: composerTags });
      recordClientError('community.create_post', message, e);
      setError(message);
    } finally {
      setPosting(false);
    }
  };

  const handleLike = async (postId: string) => {
    try {
      const r = await api.post(`/community/posts/${postId}/like`);
      setPosts(prev => prev.map(post => post.id === postId ? { ...post, is_liked: r.data.liked, likes_count: r.data.likes_count } : post));
    } catch (e: any) {
      const message = formatApiError(e, '点赞失败', { action: 'like_post', postId });
      recordClientError('community.like_post', message, e);
      setError(message);
    }
  };

  const handleCollect = async (postId: string) => {
    try {
      const r = await api.post(`/community/posts/${postId}/collect`);
      setPosts(prev => prev.map(post => post.id === postId ? { ...post, collects_count: r.data.collects_count } : post));
    } catch (e: any) {
      const message = formatApiError(e, '收藏失败', { action: 'collect_post', postId });
      recordClientError('community.collect_post', message, e);
      setError(message);
    }
  };

  const updateSettingsFromResponse = (data: CommunitySettings) => {
    setSettings({
      hidden_authors: data.hidden_authors || [],
      blocked_viewers: data.blocked_viewers || [],
    });
  };

  const handleAddHiddenAuthor = async (username = hideUsername) => {
    const target = username.trim();
    if (!target) return;
    setSettingsBusy(true);
    setError('');
    try {
      const r = await api.post('/community/settings/hidden-authors', { username: target });
      updateSettingsFromResponse(r.data);
      setHideUsername('');
      await loadFeed();
    } catch (e: any) {
      const message = formatApiError(e, '设置“不看谁”失败', { action: 'hide_author', username: target });
      recordClientError('community.hide_author', message, e);
      setError(message);
    } finally {
      setSettingsBusy(false);
    }
  };

  const handleAddBlockedViewer = async () => {
    const target = blockUsername.trim();
    if (!target) return;
    setSettingsBusy(true);
    setError('');
    try {
      const r = await api.post('/community/settings/blocked-viewers', { username: target });
      updateSettingsFromResponse(r.data);
      setBlockUsername('');
    } catch (e: any) {
      const message = formatApiError(e, '设置“不给谁看”失败', { action: 'block_viewer', username: target });
      recordClientError('community.block_viewer', message, e);
      setError(message);
    } finally {
      setSettingsBusy(false);
    }
  };

  const handleRemoveRule = async (mode: 'hidden-authors' | 'blocked-viewers', userId: string) => {
    setSettingsBusy(true);
    setError('');
    try {
      const r = await api.delete(`/community/settings/${mode}/${userId}`);
      updateSettingsFromResponse(r.data);
      if (mode === 'hidden-authors') await loadFeed();
    } catch (e: any) {
      const message = formatApiError(e, '移除社区设置失败', { action: 'remove_community_rule', mode, userId });
      recordClientError('community.remove_rule', message, e);
      setError(message);
    } finally {
      setSettingsBusy(false);
    }
  };

  const handleDeletePost = async (postId: string) => {
    if (!window.confirm('确定删除这条作品吗？删除后社区里将不再显示。')) return;
    setError('');
    try {
      await api.delete(`/community/posts/${postId}`);
      setPosts(prev => prev.filter(post => post.id !== postId));
      await loadFeed();
    } catch (e: any) {
      const message = formatApiError(e, '删除作品失败', { action: 'delete_post', postId });
      recordClientError('community.delete_post', message, e);
      setError(message);
    }
  };

  const handleShare = async (postId: string) => {
    const url = `${window.location.origin}/community/${postId}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopiedId(postId);
      window.setTimeout(() => setCopiedId(''), 1600);
    } catch {
      setCopiedId('');
    }
  };

  return (
    <div className="mx-auto grid max-w-7xl gap-5 px-4 py-6 lg:grid-cols-[220px_minmax(0,1fr)_300px]">
      <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
        <section className="rounded-lg border border-black/10 bg-white p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary text-lg font-bold text-white">
              {user?.username?.slice(0, 1).toUpperCase() || 'M'}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-text-main">{user?.username || 'MuseCut 用户'}</p>
              <p className="text-xs text-text-muted">声音故事创作者</p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-lg bg-surface-warm px-2 py-2"><b className="block text-text-main">{totals.posts}</b><span className="text-text-muted">动态</span></div>
            <div className="rounded-lg bg-surface-warm px-2 py-2"><b className="block text-text-main">{totals.likes}</b><span className="text-text-muted">共鸣</span></div>
            <div className="rounded-lg bg-surface-warm px-2 py-2"><b className="block text-text-main">{totals.comments}</b><span className="text-text-muted">讨论</span></div>
          </div>
        </section>

        <section className="rounded-lg border border-black/10 bg-white p-4">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-text-main"><Flame size={16} /> 话题</h2>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setActiveTag('')} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${!activeTag ? 'bg-primary text-white' : 'bg-surface-warm text-text-secondary hover:text-primary'}`}>全部</button>
            {TAG_LIST.map(tag => (
              <button key={tag} onClick={() => setActiveTag(activeTag === tag ? '' : tag)} className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${activeTag === tag ? 'bg-primary text-white' : 'bg-surface-warm text-text-secondary hover:text-primary'}`}>
                #{tag}
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-black/10 bg-white p-4">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="mb-3 flex w-full items-center justify-between text-left text-sm font-bold text-text-main"
          >
            <span className="inline-flex items-center gap-2"><Settings size={16} /> 社区设置</span>
            <span className="text-xs text-text-muted">{showSettings ? '收起' : '展开'}</span>
          </button>
          {showSettings && (
            <div className="space-y-4">
              <div>
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-text-secondary"><Clock size={14} /> 时间范围</p>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    ['all', '全部'],
                    ['3', '近三天'],
                    ['7', '近七天'],
                    ['30', '近一月'],
                  ].map(([value, label]) => (
                    <button
                      key={value}
                      onClick={() => setRecentDays(value)}
                      className={`rounded-lg px-2 py-1.5 text-xs font-semibold ${
                        recentDays === value ? 'bg-primary text-white' : 'bg-surface-warm text-text-muted hover:text-primary'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-text-secondary"><UserMinus size={14} /> 不看谁</p>
                <div className="flex gap-2">
                  <input
                    value={hideUsername}
                    onChange={e => setHideUsername(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleAddHiddenAuthor()}
                    placeholder="输入用户名"
                    className="min-w-0 flex-1 rounded-lg bg-surface-warm px-2 py-2 text-xs outline-none focus:ring-2 focus:ring-primary/25"
                  />
                  <button
                    onClick={() => handleAddHiddenAuthor()}
                    disabled={settingsBusy || !hideUsername.trim()}
                    className="rounded-lg bg-primary px-2 py-2 text-xs font-semibold text-white disabled:opacity-40"
                  >
                    添加
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {settings.hidden_authors.map(item => (
                    <button
                      key={item.user_id}
                      onClick={() => handleRemoveRule('hidden-authors', item.user_id)}
                      className="inline-flex items-center gap-1 rounded-md bg-surface-warm px-2 py-1 text-[11px] text-text-secondary hover:text-red-600"
                    >
                      {item.username}<X size={11} />
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-text-secondary"><Shield size={14} /> 不给谁看</p>
                <div className="flex gap-2">
                  <input
                    value={blockUsername}
                    onChange={e => setBlockUsername(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleAddBlockedViewer()}
                    placeholder="输入用户名"
                    className="min-w-0 flex-1 rounded-lg bg-surface-warm px-2 py-2 text-xs outline-none focus:ring-2 focus:ring-primary/25"
                  />
                  <button
                    onClick={handleAddBlockedViewer}
                    disabled={settingsBusy || !blockUsername.trim()}
                    className="rounded-lg bg-primary px-2 py-2 text-xs font-semibold text-white disabled:opacity-40"
                  >
                    添加
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {settings.blocked_viewers.map(item => (
                    <button
                      key={item.user_id}
                      onClick={() => handleRemoveRule('blocked-viewers', item.user_id)}
                      className="inline-flex items-center gap-1 rounded-md bg-surface-warm px-2 py-1 text-[11px] text-text-secondary hover:text-red-600"
                    >
                      {item.username}<X size={11} />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      </aside>

      <main className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-primary">Community</p>
            <h1 className="mt-1 text-3xl font-bold text-text-main">故事社区</h1>
          </div>
          <Link to="/upload" className="inline-flex items-center gap-2 rounded-lg gradient-primary px-4 py-2.5 text-sm font-semibold text-white">
            <ImagePlus size={17} /> 创作作品
          </Link>
        </div>

        {error && (
          <div className="flex items-start gap-2 whitespace-pre-wrap rounded-lg bg-red-50 px-4 py-3 font-mono text-xs leading-6 text-red-700">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        <section className="rounded-lg border border-black/10 bg-white p-4 shadow-sm">
          <div className="flex gap-3">
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg font-bold ${anonymous ? 'bg-text-main text-white' : 'bg-primary text-white'}`}>
              {anonymous ? <EyeOff size={18} /> : (user?.username?.slice(0, 1).toUpperCase() || 'M')}
            </div>
            <div className="min-w-0 flex-1">
              <input
                value={composerTitle}
                onChange={e => setComposerTitle(e.target.value)}
                maxLength={80}
                placeholder="给这条动态起个标题"
                className="mb-2 w-full rounded-lg bg-surface-warm px-3 py-2 text-sm font-semibold text-text-main placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/25"
              />
              <textarea
                value={composerText}
                onChange={e => setComposerText(e.target.value)}
                maxLength={500}
                rows={4}
                placeholder="分享你的作品、故事片段或配乐灵感..."
                className="w-full resize-none rounded-lg bg-surface-warm px-3 py-3 text-sm leading-6 text-text-main placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/25"
              />
              <div className="mt-3 flex flex-wrap gap-2">
                {TAG_LIST.slice(0, 10).map(tag => (
                  <button key={tag} onClick={() => toggleComposerTag(tag)} className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${composerTags.includes(tag) ? 'bg-primary text-white' : 'bg-surface-warm text-text-muted hover:text-primary'}`}>
                    #{tag}
                  </button>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <div className="inline-flex rounded-lg bg-surface-warm p-1">
                  <button onClick={() => setAnonymous(false)} className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold ${!anonymous ? 'bg-white text-primary shadow-sm' : 'text-text-muted'}`}>
                    <UserRound size={14} /> 实名
                  </button>
                  <button onClick={() => setAnonymous(true)} className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold ${anonymous ? 'bg-white text-primary shadow-sm' : 'text-text-muted'}`}>
                    <EyeOff size={14} /> 匿名
                  </button>
                </div>
                <button onClick={handleCreatePost} disabled={!composerText.trim() || posting} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-45">
                  {posting ? <Sparkles size={16} className="animate-pulse" /> : <Send size={16} />} 发布动态
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-4">
          {loading ? (
            <div className="rounded-lg border border-black/10 bg-white py-16 text-center text-text-muted">加载中...</div>
          ) : posts.length === 0 && !error ? (
            <div className="rounded-lg border border-black/10 bg-white py-16 text-center text-text-muted">
              {activeTag ? `还没有 #${activeTag} 动态` : '还没有动态'}
            </div>
          ) : posts.map(post => {
            const tags = parseTags(post.story_tags);
            return (
              <article key={post.id} className="rounded-lg border border-black/10 bg-white p-4 shadow-sm transition hover:border-primary/30">
                <div className="flex gap-3">
                  <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-base font-bold ${post.is_anonymous ? 'bg-text-main text-white' : 'bg-primary text-white'}`}>
                    {avatarText(post)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <Link to={`/community/${post.id}`} className="font-bold text-text-main hover:text-primary">{displayName(post)}</Link>
                      {post.is_anonymous && <span className="rounded bg-text-main/10 px-2 py-0.5 text-[10px] font-semibold text-text-main">匿名</span>}
                      <span className="text-xs text-text-muted">{relativeTime(post.created_at)}</span>
                    </div>
                    <Link to={`/community/${post.id}`} className="mt-2 block text-lg font-bold text-text-main hover:text-primary">{post.title || '未命名动态'}</Link>
                    {(post.content || post.description) && (
                      <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-text-secondary">{post.content || post.description}</p>
                    )}
                    {post.project_id && (
                      <Link to={`/community/${post.id}`} className="mt-3 block overflow-hidden rounded-lg bg-black">
                        <video src={`/api/video/public/${post.project_id}/preview`} className="aspect-video w-full object-contain" preload="metadata" />
                      </Link>
                    )}
                    {tags.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {tags.map(tag => (
                          <button key={tag} onClick={() => setActiveTag(tag)} className="rounded-lg bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary hover:bg-primary hover:text-white">
                            #{tag}
                          </button>
                        ))}
                      </div>
                    )}
                    <div className="mt-4 flex flex-wrap gap-2 border-t border-black/5 pt-3 text-sm text-text-muted">
                      <button onClick={() => handleLike(post.id)} className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 hover:bg-surface-warm ${post.is_liked ? 'text-red-500' : ''}`}>
                        <Heart size={16} fill={post.is_liked ? 'currentColor' : 'none'} /> {post.likes_count || 0}
                      </button>
                      <Link to={`/community/${post.id}`} className="inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 hover:bg-surface-warm">
                        <MessageCircle size={16} /> {post.comments_count || 0}
                      </Link>
                      <button onClick={() => handleCollect(post.id)} className="inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 hover:bg-surface-warm">
                        <Bookmark size={16} /> {post.collects_count || 0}
                      </button>
                      <button onClick={() => handleShare(post.id)} className="inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 hover:bg-surface-warm">
                        <Share2 size={16} /> {copiedId === post.id ? '已复制' : '分享'}
                      </button>
                      {!post.can_delete && !post.is_anonymous && post.username && (
                        <button
                          onClick={() => handleAddHiddenAuthor(post.username)}
                          className="inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 hover:bg-surface-warm"
                        >
                          <UserMinus size={16} /> 不看TA
                        </button>
                      )}
                      {post.can_delete && (
                        <button
                          onClick={() => handleDeletePost(post.id)}
                          className="ml-auto inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-red-500 hover:bg-red-50"
                        >
                          <Trash2 size={16} /> 删除
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      </main>

      <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
        <section className="rounded-lg border border-black/10 bg-white p-4">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-text-main"><Sparkles size={16} /> 正在发生</h2>
          <div className="space-y-3">
            {TOPICS.map(({ title, tag, icon: Icon, tone }) => (
              <button key={title} onClick={() => setActiveTag(tag)} className="flex w-full items-center gap-3 rounded-lg bg-surface-warm p-3 text-left hover:bg-primary/10">
                <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${tone}`}><Icon size={17} /></span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-text-main">{title}</span>
                  <span className="text-xs text-text-muted">#{tag}</span>
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-black/10 bg-white p-4">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-text-main"><Trophy size={16} /> 精选动态</h2>
          {featured.length === 0 ? (
            <p className="text-sm leading-6 text-text-muted">精选会从社区作品中沉淀出来。</p>
          ) : (
            <div className="space-y-3">
              {featured.slice(0, 5).map(post => (
                <Link key={post.id} to={`/community/${post.id}`} className="block rounded-lg bg-surface-warm p-3 hover:bg-primary/10">
                  <p className="line-clamp-2 text-sm font-semibold text-text-main">{post.title}</p>
                  <p className="mt-1 text-xs text-text-muted">{displayName(post)} · {post.likes_count || 0} 共鸣</p>
                </Link>
              ))}
            </div>
          )}
        </section>
      </aside>
    </div>
  );
}
