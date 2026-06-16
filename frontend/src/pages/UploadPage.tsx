import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Film, Loader2, Mic, Plus, Trash2, Type, Upload, X } from 'lucide-react';
import { VIDEO_TYPE_LABELS, type VideoType } from '../types';
import api from '../lib/api';
import WorkflowGuide from '../components/project/WorkflowGuide';
import { formatApiError, recordClientError } from '../lib/errorUtils';

const MAX_FILE_SIZE = 100 * 1024 * 1024;
type Step = 'upload' | 'keypoints' | 'done';

const TYPE_HINTS: Record<VideoType, string> = {
  healing_vlog: '日常、旅行、生活切片',
  product_promo: '商品展示、活动宣传',
  hype_edit: '运动、混剪、节奏片',
  campus_memory: '毕业、社团、校园回忆',
  emotional_story: '想念、告白、亲情、告别',
  knowledge_edu: '旁白讲解、课程、科普',
};

interface KeyPoint { time: number; type: string; label: string; importance: string; description: string; }
interface VoiceRegion { start: number; end: number; type: string; content: string; speaker: string; }
interface CaptionEvent { time: number; text: string; style: string; }
interface SceneChange { time: number; confidence: number; type: string; }

export default function UploadPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const [step, setStep] = useState<Step>('upload');
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [videoType, setVideoType] = useState<VideoType>('campus_memory');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [projectId, setProjectId] = useState('');
  const [duration, setDuration] = useState(0);
  const [sceneChanges, setSceneChanges] = useState<SceneChange[]>([]);
  const [keyPoints, setKeyPoints] = useState<KeyPoint[]>([]);
  const [voiceRegions, setVoiceRegions] = useState<VoiceRegion[]>([]);
  const [captionEvents, setCaptionEvents] = useState<CaptionEvent[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [error, setError] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [tab, setTab] = useState<'keypoints' | 'voice' | 'caption'>('keypoints');

  useEffect(() => {
    const savedStory = localStorage.getItem('musecut_story_seed');
    const savedMode = localStorage.getItem('musecut_expression_mode') as VideoType | null;
    if (savedStory) setDescription(savedStory);
    if (savedMode && VIDEO_TYPE_LABELS[savedMode]) setVideoType(savedMode);
  }, []);

  const handleFile = (f: File) => {
    if (!f.type.startsWith('video/')) { setError('请上传视频文件'); return; }
    if (f.size > MAX_FILE_SIZE) { setError('文件不能超过100MB'); return; }
    setFile(f); setVideoUrl(URL.createObjectURL(f)); setError('');
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFile(dropped);
  };

  const handleUpload = async (mode: 'auto' | 'manual' = 'auto') => {
    if (!file) return; setUploading(true);
    try {
      const fd = new FormData();
      fd.append('video', file);
      fd.append('video_type', videoType);
      fd.append('user_description', description);
      const r = await api.post('/video/upload', fd);
      setProjectId(r.data.id);
      localStorage.setItem('musecut_current_project_id', r.data.id);
      localStorage.setItem('musecut_current_video_type', videoType);
      localStorage.setItem('musecut_story_seed', description.trim());
      if (r.data.metadata_json) {
        setDuration(JSON.parse(r.data.metadata_json).duration || 0);
      }
      if (mode === 'manual') {
        try { const sc = await api.get(`/video/${r.data.id}/scene-changes`); setSceneChanges(sc.data || []); } catch {}
        setStep('keypoints');
      } else {
        navigate(`/editor/${r.data.id}`);
      }
    } catch (err: any) {
      const message = formatApiError(err, '上传失败', { action: 'upload_video', file: file.name, videoType, mode });
      recordClientError('upload.video', message, err);
      setError(message);
    }
    finally { setUploading(false); }
  };

  // Canvas timeline
  const drawTimeline = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || duration === 0) return;
    const ctx = canvas.getContext('2d'); if (!ctx) return;
    const w = canvas.width = canvas.parentElement?.clientWidth || 700;
    const h = canvas.height = 80;
    const padL = 5;
    const scaleX = (t: number) => padL + (t / duration) * (w - padL * 2);
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#f5f5f5'; ctx.fillRect(padL, 10, w - padL * 2, h - 20);
    ctx.fillStyle = '#999'; ctx.font = '10px sans-serif';
    for (let t = 0; t <= duration; t += Math.max(1, Math.floor(duration / 10))) {
      ctx.fillText(`${t}s`, scaleX(t) - 8, 8);
    }
    // Scene changes
    sceneChanges.forEach(sc => {
      const x = scaleX(sc.time);
      ctx.fillStyle = sc.type === 'hard_cut' ? 'rgba(239,68,68,0.3)' : 'rgba(251,146,60,0.3)';
      ctx.fillRect(x - 1, 10, 3, h - 20);
    });
    // Voice regions (green overlay)
    voiceRegions.forEach(vr => {
      const x1 = scaleX(vr.start), x2 = scaleX(vr.end);
      ctx.fillStyle = 'rgba(34,197,94,0.25)';
      ctx.fillRect(x1, 10, Math.max(x2 - x1, 4), h - 20);
      ctx.fillStyle = '#166534'; ctx.font = '9px sans-serif';
      ctx.fillText('VOICE', x1 + 2, h / 2 + 4);
    });
    // Caption events (orange diamonds)
    captionEvents.forEach(ce => {
      const x = scaleX(ce.time);
      ctx.fillStyle = '#f97316';
      ctx.beginPath(); ctx.moveTo(x, 18); ctx.lineTo(x + 6, h / 2); ctx.lineTo(x, h - 18); ctx.closePath(); ctx.fill();
    });
    // Key points
    keyPoints.forEach(kp => {
      const x = scaleX(kp.time);
      ctx.fillStyle = kp.importance === 'critical' ? '#ef4444' : kp.importance === 'high' ? '#f97316' : '#3b82f6';
      ctx.beginPath(); ctx.moveTo(x, 25); ctx.lineTo(x + 8, h / 2); ctx.lineTo(x, h - 25); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#333'; ctx.font = '9px sans-serif';
      ctx.fillText(kp.label || kp.type, x + 12, h / 2 + 3);
    });
    const cx = scaleX(currentTime);
    ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, h); ctx.stroke();
  }, [duration, sceneChanges, keyPoints, voiceRegions, captionEvents, currentTime]);

  useEffect(() => { drawTimeline(); }, [drawTimeline]);

  const seekAndPlay = (time: number) => {
    const target = Math.max(0, Math.min(time, duration || time));
    setCurrentTime(target);
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = target;
    video.play().catch(() => {});
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!duration) return;
    const rect = canvasRef.current?.getBoundingClientRect(); if (!rect) return;
    const padL = 5, w = rect.width;
    const x = e.clientX - rect.left;
    const t = Math.round((((x - padL) / (w - padL * 2)) * duration) * 10) / 10;
    if (t < 0 || t > duration) return;
    seekAndPlay(t);
    if (tab === 'keypoints') {
      setKeyPoints([...keyPoints, { time: t, type: 'custom', label: `节点${keyPoints.length + 1}`, importance: 'normal', description: '' }]);
    } else if (tab === 'caption') {
      setCaptionEvents([...captionEvents, { time: t, text: '', style: 'subtitle' }]);
    }
  };

  // Video sync
  useEffect(() => {
    const v = videoRef.current; if (!v) return;
    const onTime = () => setCurrentTime(v.currentTime);
    v.addEventListener('timeupdate', onTime);
    return () => v.removeEventListener('timeupdate', onTime);
  }, [videoUrl]);

  const addVoiceRegion = () => {
    setVoiceRegions([...voiceRegions, { start: Math.round(currentTime * 10) / 10, end: Math.min(Math.round((currentTime + 2) * 10) / 10, duration), type: 'dialogue', content: '', speaker: '' }]);
  };

  const submitKeypoints = async () => {
    try {
      await api.post(`/video/${projectId}/keypoints`, {
        keypoints: keyPoints,
        voice_regions: voiceRegions,
        caption_events: captionEvents,
      });
      await api.get(`/video/${projectId}/profile`);
      navigate(`/editor/${projectId}`);
    } catch (err: any) {
      const message = formatApiError(err, '保存标注失败', { action: 'submit_keypoints', projectId, keyPoints: keyPoints.length, voiceRegions: voiceRegions.length, captions: captionEvents.length });
      recordClientError('upload.submit_keypoints', message, err);
      setError(message);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <WorkflowGuide active="upload" projectId={projectId || undefined} />

      <div className="mb-8 grid gap-5 md:grid-cols-[1fr_0.78fr] md:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-primary">Create</p>
          <h1 className="mt-2 text-3xl font-bold text-text-main">创建一段有情绪走向的影像故事</h1>
          <p className="mt-3 max-w-2xl text-text-secondary">
            上传视频只是第一步。MuseCut 会把你的描述、关键画面、人声和字幕整理成声音叙事线索。
          </p>
        </div>
        <div className="rounded-lg bg-surface-dark p-4 text-sm leading-6 text-white/80">
          适合恋爱日常、家庭影像、校园回忆、旅行片段、知识旁白和产品故事。你可以先手动标注，AI 再生成可编辑的 Music Timeline。
        </div>
      </div>

      {step === 'upload' && (
        <div className="space-y-6">
          {!file ? (
            <div onDragOver={e => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition-all md:p-16 ${dragOver ? 'scale-[1.01] border-primary bg-primary/5' : 'border-text-muted/30 bg-white hover:border-primary/50'}`}>
              <input ref={fileInputRef} type="file" accept="video/*" className="hidden"
                onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
              <Upload size={40} className="mx-auto mb-4 text-primary" />
              <p className="mb-1 text-lg font-semibold text-text-main">拖拽影像素材到此处</p>
              <p className="text-sm text-text-muted">支持 MP4 / MOV / WebM，最大 100MB</p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4 md:flex-row md:items-start">
                <div className="glass flex flex-1 items-center gap-4 rounded-lg p-4">
                  <Film size={24} className="text-primary shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-text-main truncate">{file.name}</p>
                    <p className="text-sm text-text-muted">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                  </div>
                  <button onClick={() => { setFile(null); setVideoUrl(''); }} className="rounded-lg p-2 hover:bg-surface-warm"><X size={18} className="text-text-muted" /></button>
                </div>
                {videoUrl && <div className="overflow-hidden rounded-lg bg-black md:w-72"><video ref={videoRef} src={videoUrl} className="w-full" controls /></div>}
              </div>
              <div className="glass rounded-lg p-5">
                <label className="mb-3 block text-sm font-semibold text-text-main">表达方向</label>
                <div className="grid gap-3 md:grid-cols-3">
                  {(Object.entries(VIDEO_TYPE_LABELS) as [VideoType, string][]).map(([k, label]) => (
                    <button key={k} onClick={() => setVideoType(k)} className={`rounded-lg border px-3 py-3 text-left text-sm transition-all ${videoType === k ? 'border-primary bg-primary text-white shadow-lg shadow-primary/20' : 'border-black/10 bg-surface-warm text-text-secondary hover:border-primary/30'}`}>
                      <span className="block font-semibold">{label}</span>
                      <span className={`mt-1 block text-xs ${videoType === k ? 'text-white/75' : 'text-text-muted'}`}>{TYPE_HINTS[k]}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="glass rounded-lg p-5">
                <label className="mb-2 block text-sm font-semibold text-text-main">故事描述</label>
                <textarea value={description} onChange={e => setDescription(e.target.value)} maxLength={500} rows={3}
                  placeholder="例如：这是一段毕业前最后一次社团排练，我想保留大家说话的声音，在结尾做一点温暖的收束。"
                  className="w-full resize-none rounded-lg bg-surface-warm px-4 py-3 text-sm text-text-main placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/30" />
              </div>
              {error && <div className="whitespace-pre-wrap rounded-lg bg-red-50 px-4 py-3 font-mono text-xs leading-6 text-red-600">{error}</div>}
              <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                <button onClick={() => handleUpload('auto')} disabled={uploading}
                  className="flex w-full items-center justify-center gap-2 rounded-lg gradient-primary py-4 font-semibold text-white hover:opacity-90 disabled:opacity-50">
                  {uploading ? <><Loader2 size={20} className="animate-spin" />正在上传并交给 AI 编排...</> : <><ArrowRight size={20} />交给 AI 生成声音方案</>}
                </button>
                <button onClick={() => handleUpload('manual')} disabled={uploading}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-black/10 bg-white px-5 py-4 text-sm font-semibold text-text-secondary hover:border-primary hover:text-primary disabled:opacity-50">
                  先手动补充节点
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {step === 'keypoints' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <button onClick={() => setStep('upload')} className="flex items-center gap-1 text-text-muted hover:text-text-main"><ArrowRight size={16} className="rotate-180" />返回</button>
            <h2 className="text-lg font-bold text-text-main">标记声音叙事节点</h2>
            <div className="w-20" />
          </div>

          {videoUrl && (
            <div className="aspect-video max-h-[300px] overflow-hidden rounded-lg bg-black">
              <video ref={videoRef} src={videoUrl} className="w-full h-full" controls />
            </div>
          )}

          {/* Tab switcher */}
          <div className="flex rounded-lg bg-surface-warm p-1">
            {[
              { id: 'keypoints' as const, label: '关键节点', Icon: Film },
              { id: 'voice' as const, label: '人声区间', Icon: Mic },
              { id: 'caption' as const, label: '字幕事件', Icon: Type },
            ].map(({ id, label, Icon }) => (
              <button key={id} onClick={() => setTab(id)}
                className={`flex flex-1 items-center justify-center gap-2 rounded-md py-2.5 text-sm font-medium transition-all ${tab === id ? 'bg-white text-primary shadow-sm' : 'text-text-muted'}`}>
                <Icon size={16} /> {label}
              </button>
            ))}
          </div>

          {/* Scene changes auto-detect */}
          {sceneChanges.length > 0 && (
            <div className="glass rounded-lg p-4">
              <h3 className="text-sm font-semibold text-text-main mb-2">AI 检测到的转场点</h3>
              <div className="flex flex-wrap gap-2">
                {sceneChanges.map((sc, i) => (
                  <button key={i} onClick={() => {
                    seekAndPlay(sc.time);
                    setKeyPoints([...keyPoints, { time: sc.time, type: sc.type === 'hard_cut' ? 'scene_cut' : 'transition', label: sc.type === 'hard_cut' ? '画面切换' : '渐变转场', importance: 'high', description: `自动检测置信度${Math.round(sc.confidence * 100)}%` }]);
                  }}
                    className="px-3 py-1.5 rounded-lg bg-surface-warm text-xs text-text-secondary hover:bg-primary/10 hover:text-primary transition-all">
                    {sc.type === 'hard_cut' ? '切换' : '转场'} {sc.time}s ({Math.round(sc.confidence * 100)}%)
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Canvas timeline */}
          <div className="glass rounded-lg p-4">
            <p className="text-xs text-text-muted mb-2">总时长: {duration}s | 关键点: {keyPoints.length} | 人声区: {voiceRegions.length} | 字幕: {captionEvents.length} | 当前: {currentTime.toFixed(1)}s</p>
            <canvas ref={canvasRef} onClick={handleCanvasClick} className="w-full cursor-crosshair rounded-lg border border-surface-warm" />
          </div>

          {/* Tab content: Key Points */}
          {tab === 'keypoints' && (
            <div className="glass rounded-lg p-4">
              <h3 className="text-sm font-semibold text-text-main mb-3">关键节点 ({keyPoints.length})</h3>
              {keyPoints.length === 0 && <p className="text-sm text-text-muted">在时间轴上点击添加节点</p>}
              <div className="space-y-2 max-h-[200px] overflow-y-auto">
                {keyPoints.map((kp, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-lg bg-surface-warm p-3 text-sm">
                    <button type="button" onClick={() => seekAndPlay(kp.time)} className="w-12 text-left font-mono text-primary hover:underline">{kp.time}s</button>
                    <select value={kp.type} onChange={e => { const n = [...keyPoints]; n[i].type = e.target.value; setKeyPoints(n); }} className="bg-white rounded-lg px-2 py-1 text-xs border-0">
                      <option value="scene_start">场景开始</option><option value="emotion_peak">情绪高点</option><option value="ending">结尾</option><option value="transition">转场</option><option value="highlight">高亮</option><option value="scene_cut">画面切换</option><option value="custom">自定义</option>
                    </select>
                    <input value={kp.label} onChange={e => { const n = [...keyPoints]; n[i].label = e.target.value; setKeyPoints(n); }} placeholder="标签" className="flex-1 bg-white rounded-lg px-2 py-1 text-xs border-0 min-w-[80px]" />
                    <select value={kp.importance} onChange={e => { const n = [...keyPoints]; n[i].importance = e.target.value; setKeyPoints(n); }} className="bg-white rounded-lg px-2 py-1 text-xs border-0">
                      <option value="critical">关键</option><option value="high">重要</option><option value="normal">普通</option>
                    </select>
                    <button onClick={() => setKeyPoints(keyPoints.filter((_, j) => j !== i))} className="p-1 text-red-400 hover:text-red-600"><Trash2 size={14} /></button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab content: Voice Regions */}
          {tab === 'voice' && (
            <div className="glass rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-text-main">人声区间 ({voiceRegions.length})</h3>
                <button onClick={addVoiceRegion} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-medium hover:bg-primary/20">
                  <Plus size={14} /> 标记当前时间点
                </button>
              </div>
              <div className="space-y-2 max-h-[200px] overflow-y-auto">
                {voiceRegions.length === 0 && <p className="text-sm text-text-muted">播放视频到人声开始处，点击按钮标记</p>}
                {voiceRegions.map((vr, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-3 rounded-lg bg-surface-warm p-3 text-sm">
                    <button type="button" onClick={() => seekAndPlay(vr.start)} className="font-mono text-xs text-green-600 hover:underline">{vr.start}s – {vr.end}s</button>
                    <input type="number" value={vr.start} step="0.1" min={0} max={vr.end} onChange={e => { const n = [...voiceRegions]; n[i].start = parseFloat(e.target.value) || 0; setVoiceRegions(n); }} className="w-16 bg-white rounded-lg px-2 py-1 text-xs border-0" />
                    <span className="text-text-muted">→</span>
                    <input type="number" value={vr.end} step="0.1" min={vr.start} max={duration} onChange={e => { const n = [...voiceRegions]; n[i].end = parseFloat(e.target.value) || 0; setVoiceRegions(n); }} className="w-16 bg-white rounded-lg px-2 py-1 text-xs border-0" />
                    <select value={vr.type} onChange={e => { const n = [...voiceRegions]; n[i].type = e.target.value; setVoiceRegions(n); }} className="bg-white rounded-lg px-2 py-1 text-xs border-0">
                      <option value="dialogue">对话</option><option value="voiceover">旁白</option><option value="interview">采访</option>
                    </select>
                    <input value={vr.content} onChange={e => { const n = [...voiceRegions]; n[i].content = e.target.value; setVoiceRegions(n); }} placeholder="说话内容" className="flex-1 bg-white rounded-lg px-2 py-1 text-xs border-0 min-w-[100px]" />
                    <button onClick={() => setVoiceRegions(voiceRegions.filter((_, j) => j !== i))} className="p-1 text-red-400"><Trash2 size={14} /></button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab content: Caption Events */}
          {tab === 'caption' && (
            <div className="glass rounded-lg p-4">
              <h3 className="text-sm font-semibold text-text-main mb-3">字幕事件 ({captionEvents.length})</h3>
              <div className="space-y-2 max-h-[200px] overflow-y-auto">
                {captionEvents.length === 0 && <p className="text-sm text-text-muted">在时间轴上点击添加字幕事件</p>}
                {captionEvents.map((ce, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-lg bg-surface-warm p-3 text-sm">
                    <button type="button" onClick={() => seekAndPlay(ce.time)} className="w-12 text-left font-mono text-amber-600 hover:underline">{ce.time}s</button>
                    <input value={ce.text} onChange={e => { const n = [...captionEvents]; n[i].text = e.target.value; setCaptionEvents(n); }} placeholder="字幕文字" className="flex-1 bg-white rounded-lg px-2 py-1 text-xs border-0" />
                    <select value={ce.style} onChange={e => { const n = [...captionEvents]; n[i].style = e.target.value; setCaptionEvents(n); }} className="bg-white rounded-lg px-2 py-1 text-xs border-0">
                      <option value="big_title">大标题</option><option value="subtitle">副标题</option><option value="normal">普通字幕</option>
                    </select>
                    <button onClick={() => setCaptionEvents(captionEvents.filter((_, j) => j !== i))} className="p-1 text-red-400"><Trash2 size={14} /></button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && <div className="whitespace-pre-wrap rounded-lg bg-red-50 px-4 py-3 font-mono text-xs leading-6 text-red-600">{error}</div>}

          <button onClick={submitKeypoints} className="flex w-full items-center justify-center gap-2 rounded-lg gradient-primary py-4 font-semibold text-white hover:opacity-90">
            <ArrowRight size={20} />完成标记，开始配乐
          </button>
        </div>
      )}
    </div>
  );
}
