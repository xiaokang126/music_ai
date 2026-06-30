import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, Music, Pause, Play, RotateCcw, Save, Sparkles, Trash2, Upload, Volume2 } from 'lucide-react';
import api from '../lib/api';
import WorkflowGuide from '../components/project/WorkflowGuide';
import { formatApiError, recordClientError } from '../lib/errorUtils';
import { VIDEO_TYPE_LABELS, EMOTION_LABELS, type VideoType, type EmotionType } from '../types';
import { audioEngine } from '../engine/musecutEngine';
import { browserVideoVolume, normalizeMixSettings, sliderToDb, type MixSettingKey } from '../lib/mixSettings';

const EMOTION_COLORS: Record<string, string> = {
  calm: '#60a5fa', warm: '#fb923c', happy: '#facc15', intense: '#ef4444',
  sad: '#a78bfa', excited: '#fbbf24', nostalgic: '#f472b6', mysterious: '#8b5cf6', energetic: '#22c55e',
};
const EMOTIONS = ['calm','warm','happy','intense','sad','excited','nostalgic','mysterious','energetic'];
const INSTRUMENTS = ['soft_piano','acoustic_guitar','pad','orchestral','lofi_beats','synth','full_band','electronic','piano_with_pad','piano_with_strings','electronic_beat'];
const BEATS = ['','simple_kick_snare','energetic_beat','lofi_beat','trap_hats'];
const SFX_TYPES = ['','whoosh','hit','impact','riser'];
const STYLE_LIST: VideoType[] = ['healing_vlog','product_promo','hype_edit','campus_memory','emotional_story','knowledge_edu'];
const userSFXKey = (sfx: any) => `user:${sfx.id}`;

export default function EditorPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bgmPollRef = useRef<number>(0);
  const bgmCacheBustRef = useRef<number>(0);
  const autoBGMRef = useRef(false);
  const autoTimelineRef = useRef(false);
  const autoSaveTimerRef = useRef<number>(0);
  const syncedPlaybackRef = useRef(false);

  const [timelineId, setTimelineId] = useState('');
  const [timelineData, setTimelineData] = useState<any>(null);
  const [projectStyle, setProjectStyle] = useState<VideoType>(() => {
    const saved = localStorage.getItem('musecut_current_video_type') as VideoType | null;
    return saved && VIDEO_TYPE_LABELS[saved] ? saved : 'campus_memory';
  });
  const [projectTitle, setProjectTitle] = useState('');
  const [generating, setGenerating] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedSeg, setSelectedSeg] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [autoSaveDirty, setAutoSaveDirty] = useState(false);
  const [userSFXs, setUserSFXs] = useState<any[]>([]);
  const [showSFXUpload, setShowSFXUpload] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [saveNotice, setSaveNotice] = useState('');
  const [engineReady, setEngineReady] = useState(false);
  const [hasBGM, setHasBGM] = useState(false);
  const [mixStatus, setMixStatus] = useState('');
  const [originalVol, setOriginalVol] = useState(100);
  const [bgmVol, setBgmVol] = useState(90);
  const [beatVol, setBeatVol] = useState(18);
  const [sfxVol, setSfxVol] = useState(15);
  const [masterVol, setMasterVol] = useState(90);
  const [generatingBGM, setGeneratingBGM] = useState(false);
  const [semanticProfile, setSemanticProfile] = useState<any>(null);
  const [semanticDraft, setSemanticDraft] = useState({ story_summary: '', music_director_brief: '' });
  const [semanticLoading, setSemanticLoading] = useState(false);
  const [semanticSaving, setSemanticSaving] = useState(false);

  const loadUserSFXs = async () => {
    try { const r = await api.get('/assets/sfx'); setUserSFXs(r.data || []); } catch {}
  };
  useEffect(() => { loadUserSFXs(); }, []);

  const handleSFXUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append('file', f);
    fd.append('name', f.name.replace(/\.[^.]+$/, ''));
    fd.append('sfx_type', 'custom');
    try {
      await api.post('/assets/sfx/upload', fd);
      await loadUserSFXs();
    } catch (e: any) {
      const message = formatApiError(e, '音效上传失败', { action: 'upload_sfx', file: f.name });
      recordClientError('editor.upload_sfx', message, e);
      setError(message);
    }
  };

  // Drag state for segment resizing
  const [drag, setDrag] = useState<{ segIdx: number; edge: 'start' | 'end' } | null>(null);
  const dragRef = useRef<{ segIdx: number; edge: 'start' | 'end' } | null>(null);
  const timelineDataRef = useRef<any>(null);
  useEffect(() => { timelineDataRef.current = timelineData; }, [timelineData]);

  const loadProject = async () => {
    if (!projectId) return;
    try {
      const r = await api.get(`/video/${projectId}`);
      if (r.data.video_type && VIDEO_TYPE_LABELS[r.data.video_type as VideoType]) {
        setProjectStyle(r.data.video_type as VideoType);
      }
      setProjectTitle(r.data.title || '');
    } catch {}
  };

  const applySemanticProfile = (profile: any) => {
    const semantic = profile?.semantic_understanding || profile || {};
    setSemanticProfile(semantic);
    setSemanticDraft({
      story_summary: semantic.story_summary || profile?.story_summary || '',
      music_director_brief: semantic.music_director_brief || '',
    });
  };

  const loadSemanticProfile = async () => {
    if (!projectId) return;
    setSemanticLoading(true);
    try {
      const r = await api.get(`/video/${projectId}/profile`);
      applySemanticProfile(r.data);
    } catch (e: any) {
      const message = formatApiError(e, '读取视频语义理解失败', { action: 'load_video_semantics', projectId });
      recordClientError('editor.load_semantics', message, e);
      setError(message);
    } finally {
      setSemanticLoading(false);
    }
  };

  const applyMixState = (data: any) => {
    const mix = normalizeMixSettings(data?.mix_settings);
    if (data) data.mix_settings = mix;
    setOriginalVol(mix.original_volume);
    setBgmVol(mix.bgm_volume);
    setBeatVol(mix.beat_volume);
    setSfxVol(mix.sfx_volume);
    setMasterVol(mix.master_volume);
  };

  useEffect(() => {
    if (!projectId) return;
    autoTimelineRef.current = false;
    autoBGMRef.current = false;
    loadProject();
    loadSemanticProfile();
    loadTimeline();
  }, [projectId]);

  const loadTimeline = async () => {
    try {
      const r = await api.get(`/timeline/by-project/${projectId}`);
      setTimelineId(r.data.id);
      const parsed = JSON.parse(r.data.timeline_json);
      if (parsed.timeline && !Array.isArray(parsed.timeline)) parsed.timeline = [];
      applyMixState(parsed);
      setTimelineData(parsed);
      setAutoSaveDirty(false);
      setHistory([]);
    } catch {}
    setLoading(false);
  };

  const handleGenerate = async (style?: VideoType) => {
    if (!projectId) return false;
    setGenerating(true); setError('');
    const targetStyle = style || projectStyle || 'campus_memory';
    try {
      const profile = await api.get(`/video/${projectId}/profile`);
      applySemanticProfile(profile.data);
      if (timelineId && style) {
        await api.post(`/timeline/${timelineId}/restyle`, { new_style: targetStyle });
      } else {
        await api.post('/timeline/generate', { project_id: projectId, style: targetStyle });
      }
      await loadTimeline();
      setHistory([]);
      setSelectedSeg(null);
      return true;
    } catch (e: any) {
      const message = formatApiError(e, '生成 Music Timeline 失败', {
        action: 'generate_timeline',
        projectId,
        style: targetStyle,
        existingTimelineId: timelineId || null,
      });
      recordClientError('editor.generate_timeline', message, e);
      setError(message);
      return false;
    }
    finally { setGenerating(false); }
  };

  const saveSemanticProfile = async (regenerate = false) => {
    if (!projectId) return;
    setSemanticSaving(true);
    setError('');
    try {
      const r = await api.put(`/video/${projectId}/semantic`, semanticDraft);
      applySemanticProfile(r.data);
      setSaveNotice('视频理解已保存');
      if (regenerate) {
        const generated = await handleGenerate(projectStyle);
        if (generated) {
          await forceRegenerateBGM('semantic');
        }
      }
    } catch (e: any) {
      const message = formatApiError(e, '保存视频语义理解失败', { action: 'save_video_semantics', projectId });
      recordClientError('editor.save_semantics', message, e);
      setError(message);
    } finally {
      setSemanticSaving(false);
    }
  };

  const regenerateStyleAndBGM = async (style: VideoType) => {
    const generated = await handleGenerate(style);
    if (generated) {
      await forceRegenerateBGM('manual');
    }
  };

  const saveTimeline = useCallback(async (source: 'manual' | 'auto' = 'manual') => {
    if (!timelineId || !timelineData) return;
    setSaving(true);
    try {
      await api.put(`/timeline/${timelineId}`, { timeline_json: JSON.stringify(timelineData) });
      setAutoSaveDirty(false);
      setSaveNotice(`${source === 'auto' ? '已自动保存' : '已保存'}：${new Date().toLocaleTimeString()}`);
    }
    catch (e: any) {
      const message = formatApiError(e, '保存 Music Timeline 失败', { action: 'save_timeline', projectId, timelineId });
      recordClientError('editor.save_timeline', message, e);
      setError(message);
    }
    finally { setSaving(false); }
  }, [projectId, timelineData, timelineId]);

  const handleSave = () => saveTimeline('manual');

  useEffect(() => {
    window.clearTimeout(autoSaveTimerRef.current);
    if (!autoSaveDirty || !timelineId || !timelineData) return;
    autoSaveTimerRef.current = window.setTimeout(() => {
      saveTimeline('auto');
    }, 1200);
    return () => window.clearTimeout(autoSaveTimerRef.current);
  }, [autoSaveDirty, saveTimeline, timelineData, timelineId]);

  const cloneTimeline = (data: any) => JSON.parse(JSON.stringify(data));

  const pushHistorySnapshot = () => {
    if (!timelineData) return;
    setHistory(prev => [...prev.slice(-19), cloneTimeline(timelineData)]);
    setSaveNotice('');
  };

  const applyTimelineChange = (updater: (next: any) => void) => {
    if (!timelineData) return;
    const next = cloneTimeline(timelineData);
    setHistory(prev => [...prev.slice(-19), cloneTimeline(timelineData)]);
    setSaveNotice('');
    updater(next);
    setTimelineData(next);
    setAutoSaveDirty(true);
  };

  const undoLastChange = () => {
    if (history.length === 0) return;
    const previous = history[history.length - 1];
    setTimelineData(cloneTimeline(previous));
    setHistory(history.slice(0, -1));
    setSelectedSeg(null);
    setAutoSaveDirty(true);
    setSaveNotice('已回退到上一步，正在自动保存');
  };

  const updateRootField = (field: string, value: any) => {
    applyTimelineChange((next) => {
      next[field] = value;
    });
  };

  const setLocalMixValue = (field: MixSettingKey, value: number) => {
    if (field === 'original_volume') setOriginalVol(value);
    if (field === 'bgm_volume') setBgmVol(value);
    if (field === 'beat_volume') setBeatVol(value);
    if (field === 'sfx_volume') setSfxVol(value);
    if (field === 'master_volume') setMasterVol(value);
  };

  const updateMixSetting = (field: MixSettingKey, value: number) => {
    const mix = normalizeMixSettings({ ...(timelineData?.mix_settings || {}), [field]: value });
    setLocalMixValue(field, mix[field]);
    if (!timelineData) return;
    const next = cloneTimeline(timelineData);
    next.mix_settings = mix;
    setTimelineData(next);
    setAutoSaveDirty(true);
    setSaveNotice('');
  };

  const updateSegment = (idx: number, field: string, value: any) => {
    applyTimelineChange((next) => {
      const segs = [...next.timeline];
      if (field === 'sfx_type') segs[idx].sfx = value ? { type: value, position: 'start' } : null;
      else if (field === 'start' || field === 'end') segs[idx][field] = Math.round(value * 10) / 10;
      else segs[idx][field] = value;
      next.timeline = segs;
    });
  };

  const loadLatestBGM = useCallback(async (forceLoad = false) => {
    if (!projectId) return false;
    try {
      const r = await api.get(`/generate/by-project/${projectId}`);
      if (r.data.audio_url && r.data.status === 'completed') {
        setHasBGM(true);
        setGeneratingBGM(false);
        if (engineReady || forceLoad) {
          const cacheKey = bgmCacheBustRef.current || Date.now();
          await audioEngine.loadBGM(`/api/generate/public/audio/latest/${projectId}?v=${cacheKey}`);
          if (timelineDataRef.current) audioEngine.scheduleTimeline(timelineDataRef.current);
        }
        setMixStatus('已开启 BGM / Beat / SFX 混音试听');
        return true;
      }
      if (r.data.status === 'failed') {
        setHasBGM(false);
        setGeneratingBGM(false);
        setMixStatus('ACE 生成失败，请检查错误提示后重试');
        setError(r.data.error_message || 'BGM 生成失败：当前项目只允许使用 ACE 生成音频，且未得到可用结果。');
      }
      return false;
    } catch {
      return false;
    }
  }, [projectId, engineReady]);

  const pollLatestBGM = useCallback(() => {
    window.clearInterval(bgmPollRef.current);
    let attempts = 0;
    bgmPollRef.current = window.setInterval(async () => {
      attempts += 1;
      const loaded = await loadLatestBGM();
      if (loaded || attempts >= 240) {
        window.clearInterval(bgmPollRef.current);
        if (!loaded) setGeneratingBGM(false);
      }
    }, 3000);
  }, [loadLatestBGM]);

  const forceRegenerateBGM = useCallback(async (reason: 'semantic' | 'manual' = 'manual') => {
    if (!projectId) return;
    window.clearInterval(bgmPollRef.current);
    bgmCacheBustRef.current = Date.now();
    setHasBGM(false);
    setGeneratingBGM(true);
    setMixStatus(reason === 'semantic'
      ? 'ACE 正在按新的视频理解重新生成完整 BGM'
      : 'ACE 正在重新生成完整 BGM');
    setSaveNotice('已提交 ACE 重新生成，完成前试听可能仍是旧音频或轻量点缀');
    audioEngine.stop(false);
    try {
      const r = await api.post('/generate/bgm', { project_id: projectId, reason });
      bgmCacheBustRef.current = Date.now();
      setMixStatus(`ACE 已开始生成新 BGM（任务 ${String(r.data.session_id || '').slice(0, 8)}）`);
      pollLatestBGM();
    } catch (e: any) {
      setGeneratingBGM(false);
      const message = formatApiError(e, '提交 ACE 重新生成失败：当前项目只允许使用 ACE 生成音频', {
        action: 'force_regenerate_bgm',
        projectId,
        reason,
      });
      recordClientError('editor.force_regenerate_bgm', message, e);
      setError(message);
      setMixStatus('ACE 重新生成失败，请检查错误提示');
    }
  }, [projectId, pollLatestBGM]);

  const ensureBGMGeneration = useCallback(async () => {
    if (!projectId || !timelineDataRef.current) return;
    const loaded = await loadLatestBGM(true);
    if (loaded) return;
    try {
      const r = await api.get(`/generate/by-project/${projectId}`);
      if (!['segmenting', 'generating', 'started'].includes(r.data.status)) {
        await api.post('/generate/bgm', { project_id: projectId });
      }
      setGeneratingBGM(true);
      setMixStatus('完整 BGM 生成中；Beat / SFX 仅作为轻微点缀');
      pollLatestBGM();
    } catch (e: any) {
      const message = formatApiError(e, '自动生成 BGM 失败：当前项目只允许使用 ACE 生成音频', { action: 'editor_auto_generate_bgm', projectId });
      recordClientError('editor.auto_generate_bgm', message, e);
      setError(message);
      setMixStatus('ACE 生成失败：未生成完整 BGM，不使用本地效果器替代');
    }
  }, [projectId, loadLatestBGM, pollLatestBGM]);

  const prepareEditorAudio = useCallback(async () => {
    if (!timelineDataRef.current) return;
    await audioEngine.init();
    await Promise.all(userSFXs.map((sfx) =>
      audioEngine.loadSFXBuffer(userSFXKey(sfx), sfx.url).catch(() => undefined)
    ));
    setEngineReady(true);
    audioEngine.scheduleTimeline(timelineDataRef.current);
    const loaded = await loadLatestBGM();
    if (!loaded) {
      setHasBGM(false);
      setMixStatus(generatingBGM ? '完整 BGM 生成中；点缀音轨会保持很轻' : '已开启轻量点缀音轨试听');
    }
  }, [loadLatestBGM, generatingBGM, userSFXs]);

  useEffect(() => {
    if (!engineReady) return;
    userSFXs.forEach((sfx) => {
      audioEngine.loadSFXBuffer(userSFXKey(sfx), sfx.url).catch(() => undefined);
    });
  }, [engineReady, userSFXs]);

  useEffect(() => {
    if (loading || timelineData || generating || !projectId || autoTimelineRef.current) return;
    autoTimelineRef.current = true;
    handleGenerate();
  }, [loading, timelineData, generating, projectId, projectStyle]);

  useEffect(() => {
    if (!timelineData || autoBGMRef.current) return;
    autoBGMRef.current = true;
    ensureBGMGeneration();
  }, [timelineData, ensureBGMGeneration]);

  useEffect(() => {
    if (timelineData && engineReady) audioEngine.scheduleTimeline(timelineData);
  }, [timelineData, engineReady]);

  useEffect(() => {
    if (!engineReady) return;
    audioEngine.setBgmVolumeDb(sliderToDb(bgmVol));
    audioEngine.beatVolume.volume.value = sliderToDb(beatVol);
    audioEngine.sfxVolume.volume.value = sliderToDb(sfxVol);
    audioEngine.masterVolume.volume.value = sliderToDb(masterVol);
  }, [bgmVol, beatVol, sfxVol, masterVol, engineReady]);

  useEffect(() => {
    if (videoRef.current) videoRef.current.volume = browserVideoVolume(originalVol);
  }, [originalVol]);

  useEffect(() => () => {
    window.clearInterval(bgmPollRef.current);
    window.clearTimeout(autoSaveTimerRef.current);
    audioEngine.stop();
  }, []);

  const startSyncedPlayback = async (time?: number) => {
    const video = videoRef.current;
    if (!video) return;
    const duration = timelineDataRef.current?.duration || video.duration || 0;
    const target = Math.max(0, Math.min(time ?? video.currentTime ?? 0, duration || time || 0));
    try {
      if (!engineReady) await prepareEditorAudio();
      if (timelineDataRef.current) audioEngine.scheduleTimeline(timelineDataRef.current);
      audioEngine.stop(false);
      video.currentTime = target;
      video.volume = browserVideoVolume(originalVol);
      await video.play();
      await audioEngine.play(target);
      syncedPlaybackRef.current = true;
      setCurrentTime(target);
      setPlaying(true);
    } catch (e: any) {
      syncedPlaybackRef.current = false;
      audioEngine.stop(false);
      setPlaying(false);
      const message = formatApiError(e, '混音试听启动失败，已尝试只播放视频原声', { action: 'editor_start_mix_preview', projectId, time: target });
      recordClientError('editor.start_mix_preview', message, e);
      setError(message);
      try {
        video.currentTime = target;
        video.volume = browserVideoVolume(originalVol);
        await video.play();
        setPlaying(true);
      } catch {}
    }
  };

  const pauseSyncedPlayback = () => {
    syncedPlaybackRef.current = false;
    videoRef.current?.pause();
    audioEngine.stop(false);
    setPlaying(false);
  };

  // --- Canvas drag-to-resize ---
  const timeFromX = useCallback((clientX: number): number => {
    if (!canvasRef.current || !timelineData) return 0;
    const rect = canvasRef.current.getBoundingClientRect();
    const w = rect.width, dur = timelineData.duration || 15;
    const padL = 10;
    return ((clientX - rect.left - padL) / (w - padL * 2)) * dur;
  }, [timelineData]);

  const seekVideo = (time: number, shouldPlay = true) => {
    const duration = timelineDataRef.current?.duration || timelineData?.duration || time;
    const target = Math.max(0, Math.min(time, duration));
    setCurrentTime(target);
    const video = videoRef.current;
    if (!video) return;
    syncedPlaybackRef.current = false;
    audioEngine.stop(false);
    video.currentTime = target;
    if (shouldPlay) {
      startSyncedPlayback(target);
    }
  };

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!timelineData || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left, clickY = e.clientY - rect.top;
    const dur = timelineData.duration || 15, padL = 10;
    const w = rect.width, trackH = 28;
    const clickT = timeFromX(e.clientX);

    const segs = timelineData.timeline || [];

    // Check if clicking near a drag handle on the selected segment
    if (selectedSeg !== null && selectedSeg < segs.length) {
      const seg = segs[selectedSeg];
      const sx = padL + (seg.start / dur) * (w - padL * 2);
      const ex = padL + (seg.end / dur) * (w - padL * 2);
      const handleR = 6;
      // Start handle (left edge)
      if (clickY >= 5 && clickY <= 5 + trackH && Math.abs(clickX - sx) < handleR + 4) {
        pushHistorySnapshot();
        setDrag({ segIdx: selectedSeg, edge: 'start' });
        dragRef.current = { segIdx: selectedSeg, edge: 'start' };
        return;
      }
      // End handle (right edge)
      if (clickY >= 5 && clickY <= 5 + trackH && Math.abs(clickX - ex) < handleR + 4) {
        pushHistorySnapshot();
        setDrag({ segIdx: selectedSeg, edge: 'end' });
        dragRef.current = { segIdx: selectedSeg, edge: 'end' };
        return;
      }
    }

    seekVideo(clickT);

    // Check BGM track click for selection
    if (clickY >= 5 && clickY <= 5 + trackH) {
      for (let i = 0; i < segs.length; i++) {
        if (clickT >= segs[i].start && clickT <= segs[i].end) {
          setSelectedSeg(selectedSeg === i ? null : i);
          return;
        }
      }
    }
    setSelectedSeg(null);
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!drag || !timelineData) return;
    const t = timeFromX(e.clientX);
    const segs = timelineData.timeline || [];
    const d = drag;
    if (d.segIdx >= segs.length) return;

    const prevEnd = d.segIdx > 0 ? segs[d.segIdx - 1].end : 0;
    const nextStart = d.segIdx < segs.length - 1 ? segs[d.segIdx + 1].start : timelineData.duration;

    const newSegs = [...segs];
    if (d.edge === 'start') {
      newSegs[d.segIdx].start = Math.max(prevEnd, Math.min(t, newSegs[d.segIdx].end - 0.1));
    } else {
      newSegs[d.segIdx].end = Math.max(newSegs[d.segIdx].start + 0.1, Math.min(t, nextStart));
    }
    setTimelineData({ ...timelineData, timeline: newSegs });
  };

  const finishDrag = () => {
    if (dragRef.current) {
      setAutoSaveDirty(true);
      setSaveNotice('时间轴已调整，正在自动保存');
    }
    setDrag(null);
    dragRef.current = null;
  };
  const handleCanvasMouseUp = finishDrag;
  const handleCanvasMouseLeave = finishDrag;

  // --- Canvas rendering ---
  const drawTimeline = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !timelineData) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const w = canvas.width = canvas.parentElement?.clientWidth || 800;
    const h = canvas.height = 180;
    const dur = timelineData.duration || 15;
    const padL = 10;
    const segs = timelineData.timeline || [];
    const trackH = 28, gap = 4;
    const scaleX = (t: number) => padL + (t / dur) * (w - padL * 2);

    ctx.clearRect(0, 0, w, h);

    // BGM Track
    ctx.fillStyle = '#e5e7eb';
    ctx.fillRect(padL, 5, w - padL * 2, trackH);
    segs.forEach((seg: any, i: number) => {
      const x1 = scaleX(seg.start), x2 = scaleX(seg.end);
      ctx.fillStyle = EMOTION_COLORS[seg.emotion] || '#888';
      ctx.globalAlpha = 0.5 + 0.5 * (seg.energy || 0.5);
      if (selectedSeg === i) { ctx.globalAlpha = 0.85; ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 3; ctx.strokeRect(x1, 5, Math.max(x2 - x1, 2), trackH); }
      ctx.fillRect(x1, 5, Math.max(x2 - x1, 2), trackH);
      ctx.globalAlpha = 1; ctx.lineWidth = 1;
      if (x2 - x1 > 30) {
        ctx.fillStyle = selectedSeg === i ? '#1e293b' : '#fff';
        ctx.font = '10px sans-serif';
        ctx.fillText(EMOTION_LABELS[seg.emotion as EmotionType] || seg.emotion || '', x1 + 3, 5 + trackH - 8);
      }
      // Drag handles on selected segment
      if (selectedSeg === i) {
        const handleR = 5;
        ['start','end'].forEach(edge => {
          const hx = edge === 'start' ? x1 : x2;
          ctx.fillStyle = drag?.segIdx === i && drag?.edge === edge ? '#ef4444' : '#6366F1';
          ctx.fillRect(hx - handleR, 5 + trackH / 2 - handleR, handleR * 2, handleR * 2);
          ctx.fillStyle = '#fff';
          ctx.font = 'bold 8px sans-serif';
          ctx.fillText(edge === 'start' ? '◀' : '▶', hx - 4, 5 + trackH / 2 + 3);
        });
      }
    });

    // Beat Track
    const y2 = 5 + trackH + gap;
    ctx.fillStyle = '#f0f0f0'; ctx.fillRect(padL, y2, w - padL * 2, trackH);
    (timelineData.beat_points || []).forEach((point: any) => {
      const t = Number(point.time);
      if (!Number.isFinite(t) || t < 0 || t > dur) return;
      const x = scaleX(t);
      const confidence = Math.max(0.25, Math.min(1, Number(point.confidence) || 0.5));
      ctx.strokeStyle = point.type === 'onset' ? `rgba(239,68,68,${confidence})` : `rgba(249,115,22,${confidence})`;
      ctx.lineWidth = point.type === 'onset' ? 2 : 1;
      ctx.beginPath();
      ctx.moveTo(x, y2 + 5);
      ctx.lineTo(x, y2 + trackH - 5);
      ctx.stroke();
    });
    segs.forEach((seg: any) => {
      if (seg.beat_pattern) { ctx.beginPath(); ctx.arc(scaleX((seg.start + seg.end) / 2), y2 + trackH / 2, 4, 0, Math.PI * 2); ctx.fillStyle = '#f97316'; ctx.fill(); }
    });

    // SFX Track
    const y3 = 5 + (trackH + gap) * 2;
    ctx.fillStyle = '#f5f5f5'; ctx.fillRect(padL, y3, w - padL * 2, trackH);
    segs.forEach((seg: any) => {
      if (seg.sfx) { ctx.fillStyle = '#ef4444'; ctx.beginPath(); const x = scaleX(seg.start); ctx.moveTo(x, y3 + 4); ctx.lineTo(x + 6, y3 + trackH / 2); ctx.lineTo(x, y3 + trackH - 4); ctx.closePath(); ctx.fill(); }
    });

    // Ducking
    (timelineData.ducking_schedule || []).forEach((d: any) => {
      ctx.fillStyle = 'rgba(34,197,94,0.25)'; ctx.fillRect(scaleX(d.start), 5, Math.max(scaleX(d.end) - scaleX(d.start), 2), (trackH + gap) * 2 + trackH);
    });

    // Play cursor
    ctx.strokeStyle = '#ef4444'; ctx.lineWidth = 2; ctx.beginPath();
    ctx.moveTo(scaleX(currentTime), 0); ctx.lineTo(scaleX(currentTime), h); ctx.stroke();
    // Cursor label on drag
    if (drag) {
      ctx.fillStyle = '#ef4444'; ctx.font = 'bold 10px sans-serif';
      ctx.fillText(`⚠ 拖动${drag.edge==='start'?'左':'右'}边界`, 10, h - 5);
    }
  }, [timelineData, currentTime, selectedSeg, drag]);

  useEffect(() => { drawTimeline(); }, [drawTimeline]);
  useEffect(() => { const onResize = () => drawTimeline(); window.addEventListener('resize', onResize); return () => window.removeEventListener('resize', onResize); }, [drawTimeline]);
  useEffect(() => {
    const v = videoRef.current; if (!v) return;
    const stopSyncedAudio = (reset = false) => {
      syncedPlaybackRef.current = false;
      audioEngine.stop(reset);
      setPlaying(false);
    };
    const tick = () => setCurrentTime(v.currentTime);
    const pause = () => stopSyncedAudio(false);
    const end = () => {
      setCurrentTime(timelineDataRef.current?.duration || v.duration || v.currentTime);
      stopSyncedAudio(true);
    };
    const wait = () => {
      if (syncedPlaybackRef.current && !v.paused && !v.ended) stopSyncedAudio(false);
    };
    const seek = () => {
      if (syncedPlaybackRef.current) stopSyncedAudio(false);
    };
    v.addEventListener('timeupdate', tick);
    v.addEventListener('pause', pause);
    v.addEventListener('ended', end);
    v.addEventListener('waiting', wait);
    v.addEventListener('seeking', seek);
    return () => {
      v.removeEventListener('timeupdate', tick);
      v.removeEventListener('pause', pause);
      v.removeEventListener('ended', end);
      v.removeEventListener('waiting', wait);
      v.removeEventListener('seeking', seek);
    };
  }, [projectId, timelineData]);

  const togglePlay = () => { const v = videoRef.current; if (!v) return; playing ? pauseSyncedPlayback() : startSyncedPlayback(v.currentTime); };
  const stopPlaybackAndNavigate = (target: string) => {
    syncedPlaybackRef.current = false;
    videoRef.current?.pause();
    audioEngine.stop(false);
    setPlaying(false);
    navigate(target);
  };

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="animate-spin text-primary" size={32} /></div>;
  const sel = selectedSeg !== null && timelineData ? timelineData.timeline[selectedSeg] : null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 pb-20">
      <WorkflowGuide active="edit" projectId={projectId} />

      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-primary">AI Sound Desk</p>
          <h1 className="mt-1 text-3xl font-bold text-text-main">
            {timelineData ? VIDEO_TYPE_LABELS[timelineData.style as VideoType] || '声音编排' : projectTitle || 'AI 声音导演台'}
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-text-secondary">
            先让 AI 完成整体声音方案；需要微调时，点击时间轴色块即可跳到对应画面并播放。
          </p>
        </div>
        {timelineData && (
          <div className="flex flex-wrap gap-2">
            <button onClick={() => stopPlaybackAndNavigate(`/preview/${projectId}`)}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90">
              <Play size={17} /> 预览成片
            </button>
          </div>
        )}
      </div>

      <div className="mb-6 rounded-lg border border-black/10 bg-white p-4 shadow-sm">
        {!timelineData ? (
          <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
            <div className="flex gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Sparkles size={22} />
              </div>
              <div>
                <h2 className="font-bold text-text-main">下一步只需要交给 AI</h2>
                <p className="mt-1 text-sm leading-6 text-text-secondary">
                  系统正在读取视频结构、转场、人声与字幕，自动生成 BGM、Beat、SFX 和人声避让。
                </p>
              </div>
            </div>
            <button onClick={() => handleGenerate()} disabled={generating}
              className="inline-flex items-center justify-center gap-2 rounded-lg gradient-primary px-6 py-3 text-sm font-semibold text-white disabled:opacity-50">
              {generating ? <Loader2 size={17} className="animate-spin" /> : <Music size={17} />} {generating ? 'AI 正在编排' : '重新生成声音方案'}
            </button>
          </div>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="font-bold text-text-main">AI 已完成声音编排</h2>
              <p className="mt-1 text-sm leading-6 text-text-secondary">
                可直接预览或导出；想微调时，点选下方段落改情绪、乐器、Beat 和音量。
              </p>
              <p className="mt-1 text-xs text-text-muted">
                {saveNotice || `已记录 ${history.length} 步可回退修改。`}
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="mb-6 rounded-lg border border-black/10 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-bold text-text-main">AI 对画面的理解</h2>
            <p className="mt-1 text-sm leading-6 text-text-secondary">
              配乐会优先参考这里的故事摘要和声音导演意图；觉得不准可以直接改。
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-primary/10 px-3 py-1 font-semibold text-primary">
              {semanticProfile?.provider === 'qwen2.5-vl' ? 'Qwen2.5-VL 已启用' : semanticLoading ? '分析中' : '基础视觉理解'}
            </span>
            <span className="rounded-full bg-surface-warm px-3 py-1 font-semibold text-text-secondary">
              OCR {semanticProfile?.ocr_enabled ? '已开启' : '未开启'}
            </span>
          </div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-text-muted">故事摘要</span>
            <textarea
              value={semanticDraft.story_summary}
              onChange={e => setSemanticDraft(prev => ({ ...prev, story_summary: e.target.value }))}
              rows={4}
              disabled={semanticLoading}
              className="w-full resize-none rounded-lg bg-surface-warm px-3 py-2 text-sm leading-6 text-text-main focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:opacity-60"
              placeholder={semanticLoading ? '正在分析关键帧...' : '描述视频发生了什么、氛围和情绪走向'}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-semibold text-text-muted">声音导演意图</span>
            <textarea
              value={semanticDraft.music_director_brief}
              onChange={e => setSemanticDraft(prev => ({ ...prev, music_director_brief: e.target.value }))}
              rows={4}
              disabled={semanticLoading}
              className="w-full resize-none rounded-lg bg-surface-warm px-3 py-2 text-sm leading-6 text-text-main focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:opacity-60"
              placeholder="例如：前半段克制、结尾温暖抬起；不要抢人声，不要堆音效"
            />
          </label>
        </div>
        <div className="mt-3 flex flex-wrap justify-end gap-2">
          <button
            onClick={() => saveSemanticProfile(false)}
            disabled={semanticSaving || semanticLoading}
            className="inline-flex items-center gap-2 rounded-lg border border-black/10 bg-white px-4 py-2 text-sm font-semibold text-text-secondary hover:border-primary hover:text-primary disabled:opacity-50"
          >
            {semanticSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} 保存理解
          </button>
          <button
            onClick={() => saveSemanticProfile(true)}
            disabled={semanticSaving || semanticLoading || generating}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            {generating || semanticSaving ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {generating ? '正在重做声音方案' : semanticSaving ? '正在保存理解' : '按理解重做声音方案'}
          </button>
        </div>
      </div>

      {error && <div className="mb-4 whitespace-pre-wrap rounded-lg bg-red-50 px-4 py-3 font-mono text-xs leading-6 text-red-700">{error}</div>}

      {projectId && (
        <div className="mb-6 bg-black rounded-2xl overflow-hidden aspect-video max-h-[400px]">
          <video ref={videoRef} src={`/api/video/public/${projectId}/preview`} className="w-full h-full object-contain" />
        </div>
      )}

      {timelineData && (
        <>
          <div className="glass rounded-2xl p-4 mb-6">
            <div className="flex flex-wrap items-center justify-center gap-4 mb-3">
              <button onClick={togglePlay} className="p-3 rounded-full bg-primary text-white">
                {playing ? <Pause size={24} /> : <Play size={24} />}
              </button>
              <span className="text-sm text-text-muted">
                {currentTime.toFixed(1)}s / {timelineData.duration?.toFixed(1)}s
              </span>
              <div className="inline-flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
                <Volume2 size={14} />
                {engineReady ? mixStatus : '点击播放开启混音试听'}
              </div>
            </div>
            {/* BPM Slider + Key Scale */}
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted">BPM</span>
                <input type="range" min="40" max="200" value={timelineData.bpm || 82}
                  onChange={e => {
                    const newBpm = Number(e.target.value);
                    updateRootField('bpm', newBpm);
                  }}
                  className="w-24 h-1.5 rounded-full accent-primary" />
                <span className="text-xs text-text-main font-mono w-8">{timelineData.bpm || 82}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted">Key</span>
                <select value={timelineData.key || 'C_major'}
                  onChange={e => updateRootField('key', e.target.value)}
                  className="bg-surface-warm rounded-lg px-2 py-1 text-xs">
                  {['C_major','D_minor','G_major','A_minor','F_major','E_minor','D_major','Bb_major'].map(k => (
                    <option key={k} value={k}>{k.replace('_',' ')}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {[
                { label: '原声', field: 'original_volume' as MixSettingKey, value: originalVol, max: 200 },
                { label: 'BGM', field: 'bgm_volume' as MixSettingKey, value: bgmVol, max: 200, muted: !hasBGM },
                { label: 'Beat', field: 'beat_volume' as MixSettingKey, value: beatVol, max: 120 },
                { label: 'SFX', field: 'sfx_volume' as MixSettingKey, value: sfxVol, max: 120 },
                { label: 'Master', field: 'master_volume' as MixSettingKey, value: masterVol, max: 140 },
              ].map(({ label, field, value, max, muted }) => (
                <label key={label} className="rounded-lg bg-surface-warm px-3 py-2">
                  <span className="mb-1 flex items-center justify-between text-xs text-text-muted">
                    <span>{label}</span>
                    <span>{muted ? '生成中' : `${value}%`}</span>
                  </span>
                  <input
                    type="range"
                    min="0"
                    max={max}
                    value={value}
                    disabled={muted}
                    onChange={e => updateMixSetting(field, Number(e.target.value))}
                    className="w-full accent-primary disabled:opacity-40"
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="glass rounded-2xl p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm text-text-main">
                Music Timeline 时间轴
                {selectedSeg !== null && <span className="text-text-muted font-normal ml-2">（选中段落，拖动两侧手柄调整时间）</span>}
              </h3>
              <div className="flex gap-1">
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">BGM</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-orange-100 text-orange-700">Beat</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-700">SFX</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-700">Ducking</span>
              </div>
            </div>
            <canvas ref={canvasRef}
              onMouseDown={handleCanvasMouseDown}
              onMouseMove={handleCanvasMouseMove}
              onMouseUp={handleCanvasMouseUp}
              onMouseLeave={handleCanvasMouseLeave}
              className="w-full cursor-pointer"
              style={{ cursor: drag ? 'ew-resize' : 'pointer' }} />
          </div>

          {/* Segment Edit Panel */}
          {sel && selectedSeg !== null && (
            <div className="glass rounded-2xl p-5 mb-6">
              <h3 className="font-semibold text-text-main mb-3">
                编辑段落 #{selectedSeg + 1} ({sel.start}s – {sel.end}s)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <label className="text-xs text-text-muted block mb-1">情绪</label>
                  <select value={sel.emotion} onChange={e => updateSegment(selectedSeg, 'emotion', e.target.value)}
                    className="w-full bg-surface-warm rounded-lg px-3 py-2 text-sm">
                    {EMOTIONS.map(e => <option key={e} value={e}>{EMOTION_LABELS[e as EmotionType]}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">乐器</label>
                  <select value={sel.instrument} onChange={e => updateSegment(selectedSeg, 'instrument', e.target.value)}
                    className="w-full bg-surface-warm rounded-lg px-3 py-2 text-sm">
                    {INSTRUMENTS.map(i => <option key={i} value={i}>{i}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">Beat</label>
                  <select value={sel.beat_pattern || ''} onChange={e => updateSegment(selectedSeg, 'beat_pattern', e.target.value || null)}
                    className="w-full bg-surface-warm rounded-lg px-3 py-2 text-sm">
                    {BEATS.map(b => <option key={b} value={b}>{b || '无'}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">SFX</label>
                  <select value={sel.sfx?.type || ''} onChange={e => updateSegment(selectedSeg, 'sfx_type', e.target.value)}
                    className="w-full bg-surface-warm rounded-lg px-3 py-2 text-sm">
                    {SFX_TYPES.map(s => <option key={s} value={s}>{s || '无'}</option>)}
                    {userSFXs.length > 0 && <option disabled value="">── 我的音效 ──</option>}
                    {userSFXs.map(sfx => <option key={sfx.id} value={userSFXKey(sfx)}>{sfx.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">音量 ({Math.round((sel.volume||0.5)*100)}%)</label>
                  <input type="range" min="0" max="100" value={Math.round((sel.volume || 0.5) * 100)}
                    onChange={e => updateSegment(selectedSeg, 'volume', Number(e.target.value) / 100)} className="w-full" />
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">能量 ({Math.round((sel.energy||0.5)*100)}%)</label>
                  <input type="range" min="0" max="100" value={Math.round((sel.energy || 0.5) * 100)}
                    onChange={e => updateSegment(selectedSeg, 'energy', Number(e.target.value) / 100)} className="w-full" />
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">开始 ({sel.start}s)</label>
                  <input type="number" step="0.1" min={0} max={sel.end - 0.1} value={sel.start}
                    onChange={e => updateSegment(selectedSeg, 'start', parseFloat(e.target.value) || sel.start)}
                    className="w-full bg-surface-warm rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">结束 ({sel.end}s)</label>
                  <input type="number" step="0.1" min={sel.start + 0.1} max={timelineData.duration}
                    value={sel.end}
                    onChange={e => updateSegment(selectedSeg, 'end', parseFloat(e.target.value) || sel.end)}
                    className="w-full bg-surface-warm rounded-lg px-3 py-2 text-sm" />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-text-muted block mb-1">Caption (ACE-Step prompt)</label>
                  <input value={sel.caption || ''} onChange={e => updateSegment(selectedSeg, 'caption', e.target.value)}
                    className="w-full bg-surface-warm rounded-lg px-3 py-2 text-sm" placeholder="英文音乐描述..." />
                </div>
              </div>
            </div>
          )}

          {/* Style Switcher */}
          <div className="glass rounded-2xl p-4">
            <h3 className="font-semibold text-sm text-text-main mb-3">切换风格</h3>
            <div className="flex flex-wrap gap-2">
              {STYLE_LIST.map(s => (
                <button key={s} onClick={() => regenerateStyleAndBGM(s)} disabled={generating || generatingBGM}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    timelineData.style === s ? 'bg-primary text-white' : 'bg-surface-warm text-text-secondary hover:bg-surface-warm/80'
                  }`}>{VIDEO_TYPE_LABELS[s]}</button>
              ))}
            </div>
          </div>

          {/* User SFX Upload */}
          <div className="glass rounded-2xl p-4 mt-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm text-text-main">我的音效素材</h3>
              <button onClick={() => setShowSFXUpload(!showSFXUpload)}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-medium hover:bg-primary/20">
                <Upload size={12} /> 上传音效
              </button>
            </div>
            {showSFXUpload && (
              <label className="block mb-3 cursor-pointer">
                <div className="border-2 border-dashed border-text-muted/30 rounded-xl p-6 text-center hover:border-primary/50 transition-all">
                  <Upload size={20} className="mx-auto text-text-muted mb-1" />
                  <p className="text-xs text-text-muted">点击选择音效文件 (wav/mp3)</p>
                </div>
                <input type="file" accept="audio/*" className="hidden" onChange={handleSFXUpload} />
              </label>
            )}
            {userSFXs.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {userSFXs.map((sfx: any) => (
                  <div key={sfx.id} className="flex items-center gap-2 bg-surface-warm rounded-lg px-3 py-1.5 text-xs">
                    <span className="text-text-main">{sfx.name}</span>
                    <span className="text-text-muted">({sfx.sfx_type})</span>
                    <audio src={sfx.url} className="h-5 w-24" controls />
                    <button onClick={async () => {
                      try { await api.delete(`/assets/sfx/${sfx.id}`); await loadUserSFXs(); } catch (e: any) {
                        const message = formatApiError(e, '删除音效失败', { action: 'delete_sfx', sfxId: sfx.id });
                        recordClientError('editor.delete_sfx', message, e);
                        setError(message);
                      }
                    }} className="text-red-400 hover:text-red-600"><Trash2 size={12} /></button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-muted">还没有上传音效，点击上方按钮添加</p>
            )}
          </div>
        </>
      )}

      {timelineData && (
        <div className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-lg border border-black/10 bg-white/95 p-2 shadow-2xl shadow-black/15 backdrop-blur md:right-24">
          <button
            onClick={undoLastChange}
            disabled={history.length === 0}
            title="回退上一步修改"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-black/10 px-3 text-sm font-semibold text-text-secondary hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-40"
          >
            <RotateCcw size={16} /> 回退
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            title="保存当前声音编排"
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} 保存
          </button>
        </div>
      )}
    </div>
  );
}
