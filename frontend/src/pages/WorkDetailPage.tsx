import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getWorkDetail, likeWork } from '../services/workService';
import { getWorkGifts, getGifts, sendGift } from '../services/giftService';
import { toneEngine } from '../engine/toneEngine';
import api from '../lib/api';
import type { MusicWork, Gift, Comment, WorkGift } from '../types';
import { Play, Square, Heart, MessageCircle, Gift as GiftIcon, Reply, ArrowLeft } from 'lucide-react';

export default function WorkDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [work, setWork] = useState<(MusicWork & { replies: MusicWork[] }) | null>(null);
  const [playing, setPlaying] = useState(false);
  const [replies, setReplies] = useState<MusicWork[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentText, setCommentText] = useState('');
  const [gifts, setGifts] = useState<Gift[]>([]);
  const [workGifts, setWorkGifts] = useState<WorkGift[]>([]);
  const [showGiftPanel, setShowGiftPanel] = useState(false);

  useEffect(() => {
    if (!id) return;
    getWorkDetail(Number(id)).then(w => { setWork(w); setReplies(w.replies || []); });
    api.get(`/works/${id}/comments`).then(r => setComments(r.data));
    getGifts().then(setGifts);
    getWorkGifts(Number(id)).then(setWorkGifts);
  }, [id]);

  const handlePlay = async () => {
    if (!work) return;
    await toneEngine.init();
    if (playing) { toneEngine.stop(); setPlaying(false); return; }
    const params = JSON.parse(work.params_json);
    toneEngine.loadParams(params);
    toneEngine.play();
    setPlaying(true);
  };

  const handleLike = async () => {
    if (!work) return;
    await likeWork(work.id);
    setWork({ ...work, likes_count: work.likes_count + 1 });
  };

  const handleComment = async () => {
    if (!commentText.trim() || !id) return;
    const res = await api.post(`/works/${id}/comments`, { content: commentText });
    setComments([...comments, res.data]);
    setCommentText('');
  };

  const handleSendGift = async (giftId: number) => {
    if (!id) return;
    await sendGift(Number(id), giftId);
    const updated = await getWorkGifts(Number(id));
    setWorkGifts(updated);
    setShowGiftPanel(false);
  };

  const handleReply = () => {
    navigate(`/create?reply_to=${work?.id}&reply_title=${work?.title}&reply_user=${work?.username}`);
  };

  if (!work) return <div className="text-center py-20 text-text-muted">加载中...</div>;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link to="/square" className="flex items-center gap-2 text-sm text-text-muted hover:text-primary"><ArrowLeft size={14} /> 返回广场</Link>

      <div className="glass rounded-2xl p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full gradient-warm flex items-center justify-center text-white font-bold text-lg">{work.username?.[0]}</div>
            <div>
              <h1 className="text-xl font-bold text-text-main">{work.title}</h1>
              <p className="text-sm text-text-muted">@{work.username}</p>
            </div>
          </div>
          <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">{work.mood_tag}</span>
        </div>
        <p className="text-text-secondary">{work.description}</p>

        <div className="flex items-center gap-4">
          <button onClick={handlePlay} className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium ${playing ? 'bg-red-100 text-red-500' : 'glass text-primary'}`}>
            {playing ? <><Square size={16} /> 停止</> : <><Play size={16} /> 播放</>}
          </button>
          <button onClick={handleLike} className="flex items-center gap-1 text-text-secondary hover:text-red-400"><Heart size={18} /> {work.likes_count}</button>
          <button onClick={() => setShowGiftPanel(!showGiftPanel)} className="flex items-center gap-1 text-text-secondary hover:text-amber-500"><GiftIcon size={18} /> {workGifts.length}</button>
          <button onClick={handleReply} className="flex items-center gap-1 text-text-secondary hover:text-primary"><Reply size={18} /> 用音乐回应</button>
        </div>

        {showGiftPanel && (
          <div className="flex gap-2 flex-wrap p-3 rounded-xl bg-surface-warm">
            {gifts.map(g => (
              <button key={g.id} onClick={() => handleSendGift(g.id)}
                className="px-3 py-1.5 rounded-lg bg-white hover:bg-primary/5 text-lg transition-all">{g.icon} {g.name}</button>
            ))}
          </div>
        )}

        {workGifts.length > 0 && (
          <div className="flex gap-1 flex-wrap">
            {workGifts.slice(0, 10).map(wg => (
              <span key={wg.id} className="text-sm" title={`${wg.sender_name} 送了${wg.gift_name}`}>{wg.gift_icon}</span>
            ))}
          </div>
        )}
      </div>

      {replies.length > 0 && (
        <div className="glass rounded-2xl p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2"><Reply size={16} /> 音乐对话链 ({replies.length})</h3>
          <div className="space-y-3 ml-4 border-l-2 border-primary/20 pl-4">
            {replies.map(reply => (
              <Link key={reply.id} to={`/work/${reply.id}`} className="block glass rounded-xl p-3 card-hover">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-text-main">@{reply.username}</span>
                  <span className="text-xs text-text-muted">用音乐回应了</span>
                </div>
                <p className="text-sm text-text-secondary">{reply.title}</p>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="glass rounded-2xl p-6 space-y-4">
        <h3 className="font-semibold">评论 ({comments.length})</h3>
        <div className="flex gap-2">
          <input value={commentText} onChange={e => setCommentText(e.target.value)}
            placeholder="写下你的感受..." className="flex-1 px-4 py-2 rounded-xl bg-surface-warm text-sm outline-none" />
          <button onClick={handleComment} className="px-4 py-2 rounded-xl gradient-warm text-white text-sm">发送</button>
        </div>
        <div className="space-y-3">
          {comments.map(c => (
            <div key={c.id} className="flex gap-3">
              <div className="w-8 h-8 rounded-full gradient-warm flex items-center justify-center text-white text-xs font-bold flex-shrink-0">{c.username?.[0]}</div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-text-main">{c.username}</span>
                  <span className="text-xs text-text-muted">{new Date(c.created_at).toLocaleDateString()}</span>
                </div>
                <p className="text-sm text-text-secondary">{c.content}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
