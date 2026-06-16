import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Heart, MessageCircle, Send, Share2, Trash2, UserRound } from 'lucide-react';
import api from '../lib/api';
import { formatApiError, recordClientError } from '../lib/errorUtils';

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
  return post?.is_anonymous ? '匿名创作者' : (post?.username || 'MuseCut 用户');
}

export default function PostDetailPage() {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();
  const [post, setPost] = useState<any>(null);
  const [comments, setComments] = useState<any[]>([]);
  const [commentText, setCommentText] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const loadPost = async () => {
    if (!postId) return;
    setError('');
    try {
      const [postRes, commentRes] = await Promise.all([
        api.get(`/community/posts/${postId}`),
        api.get(`/community/posts/${postId}/comments`),
      ]);
      setPost(postRes.data);
      setComments(Array.isArray(commentRes.data) ? commentRes.data : []);
    } catch (e: any) {
      const message = formatApiError(e, '加载动态详情失败', { action: 'load_post_detail', postId });
      recordClientError('community.post_detail', message, e);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadPost(); }, [postId]);

  const handleLike = async () => {
    try {
      const r = await api.post(`/community/posts/${postId}/like`);
      setPost((prev: any) => ({ ...prev, likes_count: r.data.likes_count, is_liked: r.data.liked }));
    } catch (e: any) {
      const message = formatApiError(e, '点赞失败', { action: 'like_post_detail', postId });
      recordClientError('community.post_like', message, e);
      setError(message);
    }
  };

  const handleComment = async () => {
    if (!commentText.trim()) return;
    const savedText = commentText;
    try {
      await api.post(`/community/posts/${postId}/comments`, { content: commentText });
      setCommentText('');
      const r = await api.get(`/community/posts/${postId}/comments`);
      setComments(Array.isArray(r.data) ? r.data : []);
      setPost((prev: any) => ({ ...prev, comments_count: (prev?.comments_count || 0) + 1 }));
    } catch (e: any) {
      setCommentText(savedText);
      const message = formatApiError(e, '评论发送失败', { action: 'create_comment', postId });
      recordClientError('community.comment', message, e);
      setError(message);
    }
  };

  const handleShare = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  const handleDelete = async () => {
    if (!postId || !window.confirm('确定删除这条作品吗？删除后社区里将不再显示。')) return;
    try {
      await api.delete(`/community/posts/${postId}`);
      navigate('/community');
    } catch (e: any) {
      const message = formatApiError(e, '删除作品失败', { action: 'delete_post_detail', postId });
      recordClientError('community.post_delete', message, e);
      setError(message);
    }
  };

  if (loading) return <div className="py-20 text-center text-text-muted">加载中...</div>;
  if (!post && !error) return <div className="py-20 text-center text-text-muted">动态不存在</div>;

  const tags = parseTags(post?.story_tags);

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <Link to="/community" className="mb-4 inline-flex items-center gap-2 rounded-lg bg-surface-warm px-3 py-2 text-sm font-semibold text-text-secondary hover:text-primary">
        <ArrowLeft size={16} /> 返回社区
      </Link>

      {error && (
        <div className="mb-4 flex items-start gap-2 whitespace-pre-wrap rounded-lg bg-red-50 px-4 py-3 font-mono text-xs leading-6 text-red-700">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {post && (
        <article className="rounded-lg border border-black/10 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-start gap-3">
            <div className={`flex h-12 w-12 items-center justify-center rounded-lg text-lg font-bold ${post.is_anonymous ? 'bg-text-main text-white' : 'bg-primary text-white'}`}>
              {post.is_anonymous ? '匿' : <UserRound size={22} />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-bold text-text-main">{displayName(post)}</span>
                {post.is_anonymous && <span className="rounded bg-text-main/10 px-2 py-0.5 text-[10px] font-semibold text-text-main">匿名</span>}
                <span className="text-xs text-text-muted">{relativeTime(post.created_at)}</span>
              </div>
              <h1 className="mt-2 text-2xl font-bold text-text-main">{post.title || '未命名动态'}</h1>
            </div>
          </div>

          <p className="mb-4 whitespace-pre-wrap text-sm leading-7 text-text-secondary">{post.content || post.description || ''}</p>

          {tags.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-2">
              {tags.map(tag => <span key={tag} className="rounded-lg bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">#{tag}</span>)}
            </div>
          )}

          {post.project_id && (
            <div className="mb-4 overflow-hidden rounded-lg bg-black">
              <video src={`/api/video/public/${post.project_id}/preview`} controls className="aspect-video w-full object-contain" />
            </div>
          )}

          <div className="grid grid-cols-3 gap-2 border-t border-black/5 pt-3 text-sm text-text-muted">
            <button onClick={handleLike} className={`inline-flex items-center justify-center gap-2 rounded-lg py-2 hover:bg-surface-warm ${post.is_liked ? 'text-red-500' : ''}`}>
              <Heart size={17} fill={post.is_liked ? 'currentColor' : 'none'} /> {post.likes_count || 0}
            </button>
            <span className="inline-flex items-center justify-center gap-2 rounded-lg py-2">
              <MessageCircle size={17} /> {comments.length}
            </span>
            <button onClick={handleShare} className="inline-flex items-center justify-center gap-2 rounded-lg py-2 hover:bg-surface-warm">
              <Share2 size={17} /> {copied ? '已复制' : '分享'}
            </button>
          </div>
          {post.can_delete && (
            <div className="mt-3 border-t border-black/5 pt-3">
              <button onClick={handleDelete} className="inline-flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-100">
                <Trash2 size={16} /> 删除作品
              </button>
            </div>
          )}
        </article>
      )}

      <section className="mt-5 rounded-lg border border-black/10 bg-white p-4 shadow-sm">
        <h2 className="mb-4 font-bold text-text-main">评论 ({comments.length})</h2>
        <div className="mb-5 space-y-3">
          {comments.map((comment: any) => (
            <div key={comment.id} className="rounded-lg bg-surface-warm p-3">
              <span className="text-sm font-bold text-text-main">{comment.username || '匿名'}</span>
              <p className="mt-1 text-sm leading-6 text-text-secondary">{comment.content}</p>
            </div>
          ))}
          {comments.length === 0 && <p className="text-sm text-text-muted">暂无评论</p>}
        </div>

        <div className="flex gap-3">
          <input
            value={commentText}
            onChange={e => setCommentText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleComment()}
            placeholder="写下你的评论..."
            className="min-w-0 flex-1 rounded-lg bg-surface-warm px-4 py-3 text-sm text-text-main placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button onClick={handleComment} className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-3 text-white hover:opacity-90">
            <Send size={18} />
          </button>
        </div>
      </section>
    </div>
  );
}
