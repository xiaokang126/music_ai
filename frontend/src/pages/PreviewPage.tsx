import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Play, Pause, Volume2, Download, Loader2, RotateCcw, Sparkles, AlertCircle } from 'lucide-react';
import api from '../lib/api';
import WorkflowGuide from '../components/project/WorkflowGuide';
import { formatApiError, recordClientError } from '../lib/errorUtils';
import { audioEngine } from '../engine/musecutEngine';

export default function PreviewPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const waveformRef = useRef<HTMLCanvasElement>(null);
  const [timelineData, setTimelineData] = useState<any>(null);
  const [playing, setPlaying] = useState(false);
  const [bgmVol, setBgmVol] = useState(80);
  const [beatVol, setBeatVol] = useState(70);
  const [sfxVol, setSfxVol] = useState(70);
  const [masterVol, setMasterVol] = useState(90);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [engineReady, setEngineReady] = useState(false);
  const [generatingBGM, setGeneratingBGM] = useState(false);
  const [bgmStatus, setBgmStatus] = useState('');
  const [hasBGM, setHasBGM] = useState(false);
  const [checkedBGM, setCheckedBGM] = useState(false);
  const [userSFXs, setUserSFXs] = useState<any[]>([]);
  const pollRef = useRef<number>(0);
  const autoBGMRef = useRef(false);

  useEffect(() => {
    if (!projectId) return;
    setError('');
    setCheckedBGM(false);
    api.get(`/timeline/by-project/${projectId}`)
      .then(r => { setTimelineData(JSON.parse(r.data.timeline_json)); setLoading(false); })
      .catch((e) => {
        const message = formatApiError(e, '加载 Timeline 失败，请确认已在编辑页生成配乐方案', { action: 'load_timeline_for_preview', projectId });
        recordClientError('preview.load_timeline', message, e);
        setError(message);
        setLoading(false);
      });
    api.get(`/generate/by-project/${projectId}`)
      .then(r => {
        if (r.data.audio_url) setHasBGM(true);
        if (r.data.status === 'failed') {
          setBgmStatus('失败');
          setError(r.data.error_message || 'BGM 生成失败：当前项目只允许使用 ACE 生成音频，且未得到可用结果。');
        }
      })
      .catch(() => {})
      .finally(() => setCheckedBGM(true));
    api.get('/assets/sfx')
      .then(r => setUserSFXs(r.data || []))
      .catch(() => setUserSFXs([]));
  }, [projectId]);

  // Waveform
  useEffect(() => {
    const ctx = waveformRef.current?.getContext('2d');
    if (!ctx || !timelineData) return;
    const w = waveformRef.current!.width = waveformRef.current!.parentElement?.clientWidth || 600;
    const h = waveformRef.current!.height = 50;
    ctx.clearRect(0, 0, w, h);
    const segs = timelineData.timeline || [];
    const dur = timelineData.duration || 15;
    const padL = 2;
    const scaleX = (t: number) => padL + (t / dur) * (w - padL * 2);
    segs.forEach((seg: any) => {
      const x1 = scaleX(seg.start), x2 = scaleX(seg.end);
      const amp = (seg.energy || 0.5) * (h - 10);
      ctx.fillStyle = seg.emotion === 'intense' || seg.emotion === 'excited' ? '#ef4444' : seg.emotion === 'calm' || seg.emotion === 'sad' ? '#60a5fa' : '#6366F1';
      ctx.fillRect(x1, h - amp, Math.max(x2 - x1, 2), amp);
    });
  }, [timelineData]);

  const handleInitEngine = useCallback(async () => {
    try {
      await audioEngine.init();
      await Promise.all(userSFXs.map((sfx) =>
        audioEngine.loadSFXBuffer(`user:${sfx.id}`, sfx.url).catch(() => undefined)
      ));
      setEngineReady(true);
      if (timelineData) audioEngine.scheduleTimeline(timelineData);
      if (hasBGM && projectId) {
        audioEngine.loadBGM(`/api/generate/public/audio/latest/${projectId}`).catch(() => {});
      }
    } catch (e: any) {
      const message = formatApiError(e, '音频引擎初始化失败，请刷新页面重试', { action: 'init_audio_engine', projectId });
      recordClientError('preview.init_engine', message, e);
      setError(message);
    }
  }, [timelineData, hasBGM, projectId, userSFXs]);

  useEffect(() => { if (timelineData && engineReady) audioEngine.scheduleTimeline(timelineData); }, [timelineData, engineReady]);
  useEffect(() => { if (engineReady) audioEngine.bgmVolume.volume.value = (bgmVol / 100) * 2 - 1; }, [bgmVol, engineReady]);
  useEffect(() => { if (engineReady) audioEngine.beatVolume.volume.value = (beatVol / 100) * 2 - 1; }, [beatVol, engineReady]);
  useEffect(() => { if (engineReady) audioEngine.sfxVolume.volume.value = (sfxVol / 100) * 2 - 1; }, [sfxVol, engineReady]);
  useEffect(() => { if (engineReady) audioEngine.masterVolume.volume.value = (masterVol / 100) * 2 - 1; }, [masterVol, engineReady]);

  const togglePlay = async () => {
    if (!engineReady) { await handleInitEngine(); return; }
    const v = videoRef.current; if (!v) return;
    playing ? (audioEngine.stop(), v.pause()) : (v.play(), await audioEngine.play(v.currentTime || 0));
    setPlaying(!playing);
  };

  const handleStop = () => { audioEngine.stop(); videoRef.current?.pause(); setPlaying(false); };

  const handleGenerateBGM = async () => {
    if (!projectId) return;
    setGeneratingBGM(true); setBgmStatus('提交中...'); setError('');
    try {
      await api.post('/generate/bgm', { project_id: projectId });
      setBgmStatus('生成中...');
      pollRef.current = window.setInterval(async () => {
        try {
          const s = await api.get(`/generate/by-project/${projectId}`);
          if (s.data.status === 'completed') { clearInterval(pollRef.current); setGeneratingBGM(false); setBgmStatus('完成！'); setHasBGM(true); if (engineReady) { audioEngine.loadBGM(`/api/generate/public/audio/latest/${projectId}`).catch(() => {}); } }
          else if (s.data.status === 'failed') {
            clearInterval(pollRef.current);
            setGeneratingBGM(false);
            setBgmStatus('失败');
            setError(s.data.error_message || 'BGM 生成失败：当前项目只允许使用 ACE 生成音频，且未得到可用结果。');
          }
        } catch (e: any) {
          clearInterval(pollRef.current); setGeneratingBGM(false); setBgmStatus('查询失败');
          const message = formatApiError(e, 'BGM 状态查询失败，请刷新页面', { action: 'poll_bgm_generation', projectId });
          recordClientError('preview.poll_bgm', message, e);
          setError(message);
        }
      }, 3000);
    } catch (err: any) {
      setGeneratingBGM(false); setBgmStatus('提交失败');
      const message = formatApiError(err, '提交 BGM 生成请求失败', { action: 'submit_bgm_generation', projectId });
      recordClientError('preview.submit_bgm', message, err);
      setError(message);
    }
  };

  useEffect(() => {
    if (!projectId || !timelineData || !checkedBGM || hasBGM || generatingBGM || autoBGMRef.current) return;
    autoBGMRef.current = true;
    handleGenerateBGM();
  }, [projectId, timelineData, checkedBGM, hasBGM, generatingBGM]);

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="animate-spin text-primary" size={32} /></div>;
  if (!timelineData) return <div className="text-center py-20"><p className="text-text-muted text-lg mb-4">请先在编辑页生成 Music Timeline</p><button onClick={() => navigate(`/editor/${projectId}`)} className="px-6 py-3 rounded-xl gradient-primary text-white font-medium">前往编辑页</button></div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <WorkflowGuide active="preview" projectId={projectId} />

      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-text-main">预览试听</h1>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => navigate(`/editor/${projectId}`)} className="px-4 py-2.5 rounded-xl bg-surface-warm text-text-secondary font-medium hover:bg-surface-warm/80">返回编辑</button>
          {!hasBGM && !generatingBGM && checkedBGM && (
            bgmStatus.includes('失败') ? (
              <button onClick={handleGenerateBGM} className="flex items-center gap-2 rounded-xl bg-amber-50 px-5 py-2.5 font-medium text-amber-700 hover:bg-amber-100">
                <Sparkles size={18} /> 重新生成 BGM
              </button>
            ) : (
              <span className="flex items-center gap-2 rounded-xl bg-amber-50 px-4 py-2.5 text-sm text-amber-700"><Sparkles size={16} /> AI 将自动生成 BGM</span>
            )
          )}
          {generatingBGM && (<span className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-50 text-amber-700 text-sm"><Loader2 size={16} className="animate-spin" />{bgmStatus}</span>)}
          <button onClick={() => navigate(`/export/${projectId}`)} className="flex items-center gap-2 px-5 py-2.5 rounded-xl gradient-primary text-white font-medium"><Download size={18} /> 导出</button>
        </div>
      </div>

      {error && <div className="mb-4 flex items-start gap-2 whitespace-pre-wrap rounded-lg bg-red-50 px-4 py-3 font-mono text-xs leading-6 text-red-700"><AlertCircle size={16} /> {error}</div>}

      {projectId && <div className="bg-black rounded-2xl overflow-hidden aspect-video max-h-[350px] mb-6"><video ref={videoRef} src={`/api/video/public/${projectId}/preview`} className="w-full h-full object-contain" /></div>}

      {!engineReady ? (
        <div className="text-center mb-8">
          <button onClick={handleInitEngine} className="px-8 py-4 rounded-2xl gradient-primary text-white font-semibold hover:opacity-90 shadow-lg">初始化音频引擎</button>
          <p className="text-text-muted text-sm mt-2">需要用户手势启动 Web Audio API</p>
        </div>
      ) : (
        <div className="flex justify-center gap-4 mb-8">
          <button onClick={handleStop} className="p-3 rounded-full bg-surface-warm text-text-secondary hover:bg-surface-warm/80"><RotateCcw size={20} /></button>
          <button onClick={togglePlay} className="p-4 rounded-full bg-primary text-white shadow-lg hover:opacity-90">{playing ? <Pause size={28} /> : <Play size={28} />}</button>
          {hasBGM && <span className="flex items-center text-sm text-green-600">✅ BGM 已就绪</span>}
        </div>
      )}

      <div className="glass rounded-2xl p-4 mb-6"><h3 className="text-xs text-text-muted mb-2">波形预览</h3><canvas ref={waveformRef} className="w-full" /></div>

      <div className="glass rounded-2xl p-6">
        <h3 className="font-semibold text-text-main mb-5 flex items-center gap-2"><Volume2 size={18} /> 多轨混音</h3>
        <div className="space-y-4">
          {[{ label: 'BGM 背景音乐', value: bgmVol, set: setBgmVol, color: '#6366F1' },{ label: 'Beat 节奏', value: beatVol, set: setBeatVol, color: '#f97316' },{ label: 'SFX 音效', value: sfxVol, set: setSfxVol, color: '#ef4444' }].map(({ label, value, set, color }) => (
            <div key={label} className="flex items-center gap-4"><span className="w-32 text-sm text-text-secondary">{label}</span><input type="range" min="0" max="100" value={value} onChange={e => set(Number(e.target.value))} className="flex-1 h-2 rounded-full appearance-none cursor-pointer" style={{ background: `linear-gradient(to right, ${color} ${value}%, #e5e7eb ${value}%)` }} /><span className="w-10 text-sm text-text-main text-right">{value}%</span></div>
          ))}
          <div className="flex items-center gap-4 pt-2 border-t border-surface-warm"><span className="w-32 text-sm font-medium text-text-main">总音量 Master</span><input type="range" min="0" max="100" value={masterVol} onChange={e => setMasterVol(Number(e.target.value))} className="flex-1 h-2 rounded-full appearance-none cursor-pointer" style={{ background: `linear-gradient(to right, #1e293b ${masterVol}%, #e5e7eb ${masterVol}%)` }} /><span className="w-10 text-sm text-text-main text-right">{masterVol}%</span></div>
        </div>
      </div>

      <div className="mt-6 glass rounded-2xl p-4"><p className="text-sm text-text-muted">风格: {timelineData.style} | BPM: {timelineData.bpm} | Key: {timelineData.key} | 段落: {(timelineData.timeline || []).length}</p></div>
    </div>
  );
}
