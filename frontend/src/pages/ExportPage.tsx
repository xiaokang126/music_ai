import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Check, Download, EyeOff, FileAudio, FileJson, Film, Loader2, Share2, UserRound } from 'lucide-react';
import api from '../lib/api';
import WorkflowGuide from '../components/project/WorkflowGuide';
import { formatApiError, recordClientError } from '../lib/errorUtils';

const FORMATS = [
  { id: 'mp4', label: 'MP4 成片视频', icon: Film, desc: '原视频画面 + MuseCut 配乐' },
  { id: 'wav', label: 'WAV 无损音频', icon: FileAudio, desc: '适合专业后期处理' },
  { id: 'flac', label: 'FLAC 压缩无损', icon: FileAudio, desc: '无损品质，文件更小' },
  { id: 'mp3', label: 'MP3 通用格式', icon: FileAudio, desc: '320kbps 高音质' },
  { id: 'json', label: 'JSON 配乐方案', icon: FileJson, desc: 'Music Timeline 完整数据' },
];

export default function ExportPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [selected, setSelected] = useState('mp4');
  const [exporting, setExporting] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [exported, setExported] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishSuccess, setPublishSuccess] = useState('');
  const [publishAnonymous, setPublishAnonymous] = useState(false);

  const downloadFile = async (fileUrl: string, exportId: string) => {
    const tokenRes = await api.get(`/export/download-token/${exportId}`);
    const downloadUrl = tokenRes.data?.download_url || fileUrl;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `musecut_export.${selected}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setSuccess(`导出完成，浏览器已开始下载。导出任务: ${exportId}`);
    setExported(true);
  };

  const handleExport = async () => {
    if (!projectId) return;
    setExporting(true);
    setError('');
    setSuccess('');
    setExported(false);
    setPublishSuccess('');
    try {
      const r = await api.post('/export/audio', { project_id: projectId, format: selected });
      const eid = r.data.export_id;
      setStatus('导出中...');
      pollStatus(eid);
    } catch (err: any) {
      const message = formatApiError(err, '导出请求失败', { action: 'create_export_task', projectId, format: selected });
      recordClientError('export.create_task', message, err);
      setError(message);
      setExporting(false);
    }
  };

  const pollStatus = async (eid: string, retryCount = 0) => {
    try {
      const r = await api.get(`/export/status/${eid}`);
      setStatus(r.data.status);
      if (r.data.status === 'completed') {
        setStatus('下载中...');
        if (r.data.file_url) {
          await downloadFile(r.data.file_url, eid);
        } else {
          setSuccess(`导出完成，但服务端没有返回下载地址。导出任务: ${eid}`);
        }
        setExporting(false);
      } else if (r.data.status === 'failed') {
        setError(`导出失败\n导出任务: ${eid}\n格式: ${selected}\n服务端状态: failed${r.data.message ? `\n服务端说明: ${r.data.message}` : ''}`);
        setExporting(false);
      } else {
        setTimeout(() => pollStatus(eid, 0), 2000);
      }
    } catch (err: any) {
      const retryable = (err?.code === 'ECONNABORTED' || err?.code === 'ERR_NETWORK' || !err?.response) && retryCount < 10;
      if (retryable) {
        setStatus(`导出仍在处理中，继续查询...(${retryCount + 1}/10)`);
        setTimeout(() => pollStatus(eid, retryCount + 1), 3000);
        return;
      }
      const message = formatApiError(err, '导出状态查询或下载失败', { action: 'poll_or_download_export', projectId, exportId: eid, format: selected });
      recordClientError('export.poll_or_download', message, err);
      setError(message);
      setExporting(false);
    }
  };

  const handlePublish = async () => {
    if (!projectId) return;
    setPublishing(true);
    setError('');
    setPublishSuccess('');
    try {
      const formatLabel = FORMATS.find(item => item.id === selected)?.label || selected.toUpperCase();
      await api.post('/community/posts', {
        project_id: projectId,
        title: 'MuseCut 成片作品',
        story_tags: ['成片', selected],
        description: `已完成 ${formatLabel} 导出，分享这段声音叙事与情绪表达。`,
        is_anonymous: publishAnonymous,
      });
      setPublishSuccess('已发布到故事社区。');
    } catch (err: any) {
      const message = formatApiError(err, '发布到社区失败', { action: 'publish_after_export', projectId, format: selected });
      recordClientError('export.publish_post', message, err);
      setError(message);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <WorkflowGuide active="export" projectId={projectId} />

      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">Export</p>
          <h1 className="mt-1 text-2xl font-bold text-text-main">导出作品</h1>
          <p className="mt-2 text-text-secondary">默认导出带配乐的视频成片；音频和 JSON 方案可作为补充素材下载。</p>
        </div>
        <button onClick={() => navigate(`/preview/${projectId}`)} className="inline-flex items-center gap-2 rounded-lg bg-surface-warm px-4 py-2 text-sm font-semibold text-text-secondary hover:text-primary">
          <ArrowLeft size={16} /> 返回预览
        </button>
      </div>

      {error && (
        <div className="mb-6 flex items-start gap-2 whitespace-pre-wrap rounded-lg bg-red-50 px-4 py-3 font-mono text-xs leading-6 text-red-700">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {success && (
        <div className="mb-6 rounded-lg bg-green-50 px-4 py-3 text-sm font-semibold text-green-700">
          {success}
        </div>
      )}

      {publishSuccess && (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-green-50 px-4 py-3 text-sm font-semibold text-green-700">
          <span>{publishSuccess}</span>
          <button onClick={() => navigate('/community')} className="rounded-lg bg-white px-3 py-1.5 text-green-700 hover:bg-green-100">
            查看社区
          </button>
        </div>
      )}

      <div className="mb-8 grid gap-3 md:grid-cols-2">
        {FORMATS.map(({ id, label, icon: Icon, desc }) => (
          <button key={id} onClick={() => { setSelected(id); setExported(false); setPublishSuccess(''); }}
            className={`flex min-h-[104px] w-full items-center gap-4 rounded-lg border p-4 text-left transition-all ${id === 'mp4' ? 'md:col-span-2' : ''} ${
              selected === id ? 'border-primary bg-primary/10' : 'border-black/10 bg-white hover:border-primary/30'
            }`}>
            <Icon size={24} className={selected === id ? 'text-primary' : 'text-text-muted'} />
            <div className="flex-1"><span className="font-medium text-text-main block">{label}</span><span className="text-sm text-text-muted">{desc}</span></div>
            {selected === id && <Check size={20} className="text-primary" />}
          </button>
        ))}
      </div>

      <button onClick={handleExport} disabled={exporting}
        className="flex w-full items-center justify-center gap-2 rounded-lg gradient-primary py-4 font-semibold text-white hover:opacity-90 disabled:opacity-50">
        {exporting ? <><Loader2 size={20} className="animate-spin" /> {status}</> : <><Download size={20} /> {selected === 'mp4' ? '导出带配乐视频' : '开始导出'}</>}
      </button>

      <div className="mt-6 rounded-lg border border-black/10 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-bold text-text-main">最后一步：分享作品</h2>
            <p className="mt-1 text-sm text-text-secondary">导出满意后，再把作品发布到故事社区。</p>
          </div>
          <div className="inline-flex rounded-lg bg-surface-warm p-1">
            <button onClick={() => setPublishAnonymous(false)} className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold ${!publishAnonymous ? 'bg-white text-primary shadow-sm' : 'text-text-muted'}`}>
              <UserRound size={14} /> 实名
            </button>
            <button onClick={() => setPublishAnonymous(true)} className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold ${publishAnonymous ? 'bg-white text-primary shadow-sm' : 'text-text-muted'}`}>
              <EyeOff size={14} /> 匿名
            </button>
          </div>
          <button onClick={handlePublish} disabled={!exported || publishing}
            className="inline-flex items-center gap-2 rounded-lg bg-green-50 px-5 py-2.5 text-sm font-semibold text-green-700 hover:bg-green-100 disabled:cursor-not-allowed disabled:opacity-45">
            {publishing ? <Loader2 size={17} className="animate-spin" /> : <Share2 size={17} />} 发布到社区
          </button>
        </div>
      </div>
    </div>
  );
}
