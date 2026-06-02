import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getDiaryList, getMoodChart } from '../services/diaryService';
import type { EmotionDiary } from '../types';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { BookOpen } from 'lucide-react';

export default function DiaryPage() {
  const [entries, setEntries] = useState<EmotionDiary[]>([]);
  const [chartData, setChartData] = useState<Array<{ date: string; score: number; mood_tag: string }>>([]);
  const [viewMode, setViewMode] = useState<'chart' | 'list'>('chart');

  useEffect(() => {
    getDiaryList().then(d => setEntries(d.entries));
    getMoodChart(30).then(d => setChartData(d.points));
  }, []);

  // Group by mood tags for multiple lines
  const moodColors: Record<string, string> = {
    sad: '#6B7DB3', melancholic: '#8B7EC8', hopeful: '#F0C060', calm: '#7EC8A0',
    healing: '#5DB5A4', lonely: '#9B8EC4', nostalgic: '#C8A882', bittersweet: '#C4828C',
    warm: '#E8916A', peaceful: '#82B9C8',
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <BookOpen size={24} className="text-primary" /> 情绪日记
      </h1>

      <div className="flex gap-2">
        {(['chart', 'list'] as const).map(m => (
          <button key={m} onClick={() => setViewMode(m)}
            className={`px-4 py-2 rounded-xl text-sm font-medium ${viewMode === m ? 'bg-primary text-white' : 'glass text-text-secondary'}`}>
            {m === 'chart' ? '情绪曲线' : '时间线'}
          </button>
        ))}
      </div>

      {viewMode === 'chart' && (
        <div className="glass rounded-2xl p-6">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 10]} tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: 'rgba(255,255,255,0.95)', borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}
                  labelFormatter={(label: any) => `日期: ${label}`}
                  formatter={(value: any) => [`${value}`, '心情指数']}
                />
                <Line type="monotone" dataKey="score" stroke="#E8916A" strokeWidth={3} dot={{ r: 4, fill: '#E8916A' }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center text-text-muted py-10">还没有情绪记录，去创作点什么吧</p>
          )}
        </div>
      )}

      {viewMode === 'list' && (
        <div className="space-y-3">
          {entries.map(e => (
            <div key={e.id} className="glass rounded-xl p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-full gradient-warm flex items-center justify-center text-white text-sm font-bold">{e.mood_score}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-text-main">{e.mood_tag}</span>
                  <span className="text-xs text-text-muted">{new Date(e.created_at).toLocaleDateString()}</span>
                </div>
                {e.note && <p className="text-sm text-text-secondary mt-0.5">{e.note.slice(0, 80)}</p>}
              </div>
              {e.work_id && <Link to={`/work/${e.work_id}`} className="text-xs text-primary hover:underline">听作品</Link>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
