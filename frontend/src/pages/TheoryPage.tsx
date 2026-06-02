import { useState, useEffect } from 'react';
import { theoryChapters, type TheoryLesson } from '../data/theoryData';
import { toneEngine } from '../engine/toneEngine';
import { Play, Square, ChevronRight, Check, X } from 'lucide-react';

export default function TheoryPage() {
  const [activeChapter, setActiveChapter] = useState(theoryChapters[0].id);
  const [activeLesson, setActiveLesson] = useState(theoryChapters[0].lessons[0].id);
  const [playing, setPlaying] = useState(false);
  const [quizAnswer, setQuizAnswer] = useState<number | null>(null);
  const [quizResult, setQuizResult] = useState<boolean | null>(null);

  const chapter = theoryChapters.find(c => c.id === activeChapter)!;
  const lesson = chapter.lessons.find(l => l.id === activeLesson)!;

  useEffect(() => { setQuizAnswer(null); setQuizResult(null); }, [activeLesson]);

  const handlePlay = async (notes: string[]) => {
    await toneEngine.init();
    if (playing) { toneEngine.stop(); setPlaying(false); return; }
    const ToneModule = (window as any).Tone;
    if (!ToneModule) { return; }
    const synth = new ToneModule.PolySynth().toDestination();
    setPlaying(true);
    const now = ToneModule.now();
    notes.forEach((note: string, i: number) => {
      synth.triggerAttackRelease(note, '8n', now + i * 0.3, 0.5);
    });
    setTimeout(() => { synth.dispose(); setPlaying(false); }, notes.length * 300 + 1000);
  };

  const handleQuiz = (idx: number) => {
    if (!lesson.quiz) return;
    setQuizAnswer(idx);
    setQuizResult(idx === lesson.quiz.answer);
  };

  return (
    <div className="flex gap-6">
      <aside className="w-48 flex-shrink-0 glass rounded-2xl p-4 h-fit hidden md:block">
        {theoryChapters.map(ch => (
          <div key={ch.id} className="mb-3">
            <button onClick={() => { setActiveChapter(ch.id); setActiveLesson(ch.lessons[0].id); }}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                activeChapter === ch.id ? 'bg-primary/10 text-primary' : 'text-text-secondary hover:text-primary'
              }`}>{ch.title}</button>
            {activeChapter === ch.id && (
              <div className="ml-3 mt-1 space-y-1">
                {ch.lessons.map(l => (
                  <button key={l.id} onClick={() => setActiveLesson(l.id)}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-xs transition-all flex items-center gap-1 ${
                      activeLesson === l.id ? 'bg-primary/5 text-primary font-medium' : 'text-text-muted hover:text-text-secondary'
                    }`}>
                    <ChevronRight size={10} /> {l.title}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </aside>

      <div className="flex-1 glass rounded-2xl p-6 md:p-8">
        <h2 className="text-xl font-bold text-text-main mb-4">{lesson.title}</h2>
        <div className="prose prose-sm max-w-none mb-6 text-text-secondary leading-relaxed whitespace-pre-line">{lesson.content}</div>

        {lesson.example && (
          <div className="glass rounded-xl p-4 mb-6 inline-flex items-center gap-4">
            <button onClick={() => handlePlay(lesson.example!.notes)}
              className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                playing ? 'bg-red-100 text-red-500' : 'bg-primary/10 text-primary hover:bg-primary/20'
              }`}>
              {playing ? <Square size={16} /> : <Play size={16} fill="currentColor" />}
            </button>
            <span className="text-sm font-medium text-text-main">{lesson.example.label}</span>
          </div>
        )}

        {lesson.quiz && (
          <div className="glass rounded-xl p-5 mt-6">
            <h4 className="font-medium text-text-main mb-3">小测验：{lesson.quiz.question}</h4>
            <div className="space-y-2">
              {lesson.quiz.options.map((opt, i) => (
                <button key={i} onClick={() => handleQuiz(i)}
                  className={`w-full text-left px-4 py-2.5 rounded-lg text-sm transition-all ${
                    quizAnswer === i
                      ? quizResult ? 'bg-green-50 text-green-600 border border-green-200' : 'bg-red-50 text-red-500 border border-red-200'
                      : 'bg-surface-warm text-text-secondary hover:bg-primary/5'
                  } flex items-center justify-between`}>
                  {opt}
                  {quizAnswer === i && (quizResult ? <Check size={16} /> : <X size={16} />)}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-between mt-8">
          <button
            onClick={() => {
              const idx = chapter.lessons.findIndex(l => l.id === activeLesson);
              if (idx > 0) setActiveLesson(chapter.lessons[idx - 1].id);
            }}
            className="text-sm text-text-muted hover:text-primary transition-colors">← 上一节</button>
          <button
            onClick={() => {
              const idx = chapter.lessons.findIndex(l => l.id === activeLesson);
              if (idx < chapter.lessons.length - 1) setActiveLesson(chapter.lessons[idx + 1].id);
            }}
            className="text-sm text-primary hover:underline">下一节 →</button>
        </div>
      </div>
    </div>
  );
}
