import { Check, Download, Film, Music2, Upload } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

type StepId = 'upload' | 'edit' | 'preview' | 'export';
type DisplayStepId = 'upload' | 'compose' | 'export';

interface WorkflowGuideProps {
  active: StepId;
  projectId?: string;
}

const steps: { id: DisplayStepId; label: string; hint: string; icon: typeof Upload }[] = [
  { id: 'upload', label: '上传素材', hint: '选择表达方向', icon: Upload },
  { id: 'compose', label: '编排试听', hint: '生成、微调并预览', icon: Music2 },
  { id: 'export', label: '导出作品', hint: '保存成片视频', icon: Download },
];

const activeToDisplay: Record<StepId, DisplayStepId> = {
  upload: 'upload',
  edit: 'compose',
  preview: 'compose',
  export: 'export',
};

const routes: Record<DisplayStepId, (projectId?: string) => string | null> = {
  upload: () => '/upload',
  compose: (projectId) => projectId ? `/editor/${projectId}` : null,
  export: (projectId) => projectId ? `/export/${projectId}` : null,
};

export default function WorkflowGuide({ active, projectId }: WorkflowGuideProps) {
  const navigate = useNavigate();
  const activeDisplay = activeToDisplay[active];
  const activeIndex = steps.findIndex((step) => step.id === activeDisplay);

  return (
    <section className="mb-6 rounded-lg border border-black/10 bg-white p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Workflow</p>
          <h2 className="mt-1 text-lg font-bold text-text-main">按这 3 步完成作品</h2>
        </div>
        <div className="hidden items-center gap-2 rounded-lg bg-primary/10 px-3 py-2 text-xs font-semibold text-primary sm:flex">
          <Film size={14} />
          当前：{steps[activeIndex]?.label || '创作'}
        </div>
      </div>
      <div className="grid gap-2 md:grid-cols-3">
        {steps.map((step, index) => {
          const Icon = step.icon;
          const done = index < activeIndex;
          const current = step.id === activeDisplay;
          const target = routes[step.id](projectId);
          const enabled = Boolean(target);
          return (
            <button
              key={step.id}
              type="button"
              disabled={!enabled}
              onClick={() => target && navigate(target)}
              className={`flex min-h-[74px] items-center gap-3 rounded-lg border px-3 py-3 text-left transition ${
                current
                  ? 'border-primary bg-primary/10 text-primary'
                  : done
                    ? 'border-primary/20 bg-surface-bg text-text-main hover:border-primary/40'
                    : 'border-black/10 bg-surface-bg text-text-secondary hover:border-primary/30'
              } ${enabled ? '' : 'cursor-not-allowed opacity-60'}`}
            >
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${done ? 'bg-primary text-white' : current ? 'bg-primary/15 text-primary' : 'bg-white text-text-muted'}`}>
                {done ? <Check size={17} /> : <Icon size={17} />}
              </span>
              <span>
                <span className="block text-sm font-semibold">{index + 1}. {step.label}</span>
                <span className="mt-1 block text-xs text-text-muted">{step.hint}</span>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
