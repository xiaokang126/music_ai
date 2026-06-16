import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, Camera, Clock, Film, Play, Save, Trash2, Upload, UserRound, X } from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../hooks/useAuth';
import { updateMe } from '../services/authService';
import { VIDEO_TYPE_LABELS, type VideoType } from '../types';
import { formatApiError, recordClientError } from '../lib/errorUtils';

function formatDuration(seconds?: number) {
  const total = Math.max(0, Math.round(seconds || 0));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

function statusText(status: string) {
  if (status === 'uploaded') return '待编排';
  if (status === 'profiled') return '已分析';
  if (status === 'completed') return '已完成';
  if (status === 'failed') return '需要重试';
  return status || '进行中';
}

function continuePath(project: any) {
  if (project.status === 'completed') return `/preview/${project.id}`;
  return `/editor/${project.id}`;
}

export default function ProfilePage() {
  const { user, isLoggedIn, loading: authLoading, updateUser } = useAuth();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [username, setUsername] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const loadProjects = useCallback(async () => {
    setError('');
    setLoading(true);
    try {
      const r = await api.get('/video/projects');
      setProjects(r.data.projects || []);
    } catch (e: any) {
      const message = formatApiError(e, '加载创作任务失败', { action: 'load_profile_projects' });
      recordClientError('profile.load_projects', message, e);
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }
    loadProjects();
  }, [authLoading, isLoggedIn, loadProjects, navigate]);

  useEffect(() => {
    setUsername(user?.username || '');
    setAvatarUrl(user?.avatar_url || '');
  }, [user]);

  const unfinished = useMemo(
    () => projects.filter(project => project.status !== 'completed'),
    [projects]
  );

  const handleAvatarFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setNotice('');
    if (!file.type.startsWith('image/')) {
      setError('头像文件需要是图片格式');
      return;
    }
    if (file.size > 1024 * 1024) {
      setError('头像图片请控制在 1MB 以内');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setAvatarUrl(String(reader.result || ''));
      setError('');
    };
    reader.onerror = () => setError('读取头像文件失败，请换一张图片重试');
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = async (event: FormEvent) => {
    event.preventDefault();
    if (!username.trim()) {
      setError('用户名不能为空');
      return;
    }
    setSavingProfile(true);
    setError('');
    setNotice('');
    try {
      const nextUser = await updateMe({ username: username.trim(), avatar_url: avatarUrl.trim() });
      updateUser(nextUser);
      setNotice('个人资料已保存');
    } catch (e: any) {
      const message = formatApiError(e, '保存个人资料失败', { action: 'update_profile' });
      recordClientError('profile.update_profile', message, e);
      setError(message);
    } finally {
      setSavingProfile(false);
    }
  };

  const handleDelete = async (projectId: string) => {
    if (!window.confirm('确定删除这个创作任务吗？上传素材和相关编排会一起移除。')) return;
    setError('');
    try {
      await api.delete(`/video/${projectId}`);
      setProjects(prev => prev.filter(project => project.id !== projectId));
    } catch (e: any) {
      const message = formatApiError(e, '删除任务失败', { action: 'delete_project', projectId });
      recordClientError('profile.delete_project', message, e);
      setError(message);
    }
  };

  if (authLoading) {
    return <div className="py-20 text-center text-text-muted">正在进入个人中心...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <section className="mb-6 rounded-lg border border-black/10 bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="" className="h-16 w-16 rounded-lg object-cover" />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-lg gradient-primary text-2xl font-bold text-white">
                {user?.username?.slice(0, 1).toUpperCase() || <UserRound size={26} />}
              </div>
            )}
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">Profile Center</p>
              <h1 className="mt-1 text-2xl font-bold text-text-main">个人中心</h1>
              <p className="mt-1 text-sm text-text-muted">{user?.username || 'MuseCut 用户'}，你的资料和创作任务都在这里。</p>
            </div>
          </div>
          <Link to="/upload" className="inline-flex items-center gap-2 rounded-lg gradient-primary px-4 py-2.5 text-sm font-semibold text-white">
            <Upload size={17} /> 新建创作
          </Link>
        </div>
      </section>

      {error && (
        <div className="mb-5 flex items-start gap-2 whitespace-pre-wrap rounded-lg bg-red-50 px-4 py-3 font-mono text-xs leading-6 text-red-700">
          <AlertCircle size={16} /> {error}
        </div>
      )}
      {notice && (
        <div className="mb-5 rounded-lg bg-primary/10 px-4 py-3 text-sm font-semibold text-primary">{notice}</div>
      )}

      <section id="settings" className="mb-8 rounded-lg border border-black/10 bg-white p-5">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-text-main">资料设置</h2>
          <p className="mt-1 text-sm text-text-muted">改名和头像会同步到社区展示与个人入口。</p>
        </div>
        <form onSubmit={handleSaveProfile} className="grid gap-5 lg:grid-cols-[220px_1fr]">
          <div className="flex flex-col items-start gap-3">
            {avatarUrl ? (
              <img src={avatarUrl} alt="" className="h-28 w-28 rounded-lg object-cover" />
            ) : (
              <div className="flex h-28 w-28 items-center justify-center rounded-lg bg-surface-warm text-text-muted">
                <UserRound size={34} />
              </div>
            )}
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-surface-warm px-3 py-2 text-sm font-semibold text-text-secondary hover:text-primary">
              <Camera size={16} /> 上传头像
              <input type="file" accept="image/*" className="hidden" onChange={handleAvatarFile} />
            </label>
            {avatarUrl && (
              <button type="button" onClick={() => setAvatarUrl('')} className="inline-flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-100">
                <X size={16} /> 清除头像
              </button>
            )}
          </div>
          <div className="space-y-4">
            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-text-secondary">用户名</span>
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                maxLength={50}
                className="w-full rounded-lg border border-black/10 bg-surface-bg px-4 py-3 text-text-main outline-none focus:border-primary"
                placeholder="输入新的用户名"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-text-secondary">头像链接</span>
              <input
                value={avatarUrl.startsWith('data:image/') ? '已上传本地头像' : avatarUrl}
                onChange={(event) => setAvatarUrl(event.target.value)}
                disabled={avatarUrl.startsWith('data:image/')}
                className="w-full rounded-lg border border-black/10 bg-surface-bg px-4 py-3 text-text-main outline-none focus:border-primary disabled:text-text-muted"
                placeholder="也可以粘贴 https 图片链接"
              />
            </label>
            <button
              type="submit"
              disabled={savingProfile}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
            >
              <Save size={17} /> {savingProfile ? '保存中...' : '保存资料'}
            </button>
          </div>
        </form>
      </section>

      <section className="mb-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-bold text-text-main">创作任务</h2>
          <span className="text-sm text-text-muted">未完成 {unfinished.length} 个，全部 {projects.length} 个</span>
        </div>
        {loading ? (
          <div className="rounded-lg border border-black/10 bg-white py-14 text-center text-text-muted">加载中...</div>
        ) : unfinished.length === 0 ? (
          <div className="rounded-lg border border-black/10 bg-white py-14 text-center text-text-muted">暂无未完成任务</div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {unfinished.map(project => (
              <article key={project.id} className="rounded-lg border border-black/10 bg-white p-4 shadow-sm">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate text-base font-bold text-text-main">{project.title || project.video_filename}</h3>
                    <p className="mt-1 text-sm text-text-muted">{VIDEO_TYPE_LABELS[project.video_type as VideoType] || project.video_type}</p>
                  </div>
                  <span className="rounded-lg bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">{statusText(project.status)}</span>
                </div>
                <div className="mb-4 flex flex-wrap gap-3 text-xs text-text-muted">
                  <span className="inline-flex items-center gap-1"><Clock size={13} /> {formatDuration(project.duration)}</span>
                  <span className="inline-flex items-center gap-1"><Film size={13} /> {project.video_filename}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button onClick={() => navigate(continuePath(project))} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90">
                    <Play size={16} /> 继续执行
                  </button>
                  <button onClick={() => handleDelete(project.id)} className="inline-flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-100">
                    <Trash2 size={16} /> 删除
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-bold text-text-main">全部创作</h2>
        <div className="rounded-lg border border-black/10 bg-white">
          {projects.length === 0 && !loading ? (
            <div className="py-12 text-center text-sm text-text-muted">还没有创作任务</div>
          ) : projects.map(project => (
            <div key={project.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-black/5 px-4 py-3 last:border-0">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-text-main">{project.title || project.video_filename}</p>
                <p className="mt-1 text-xs text-text-muted">{statusText(project.status)} · {formatDuration(project.duration)}</p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => navigate(continuePath(project))} className="rounded-lg bg-surface-warm px-3 py-1.5 text-xs font-semibold text-text-secondary hover:text-primary">
                  继续
                </button>
                <button onClick={() => handleDelete(project.id)} className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-100">
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
