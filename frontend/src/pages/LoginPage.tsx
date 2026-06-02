import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { registerUser, loginUser } from '../services/authService';
import { Music } from 'lucide-react';

export default function LoginPage() {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) { setError('请填写完整信息'); return; }
    setLoading(true);
    setError('');
    const fn = tab === 'login' ? loginUser : registerUser;
    fn(username, password).then(({ access_token, user }) => {
      login(user, access_token);
      navigate('/square');
    }).catch(err => {
      setError(err.response?.data?.detail || '操作失败，请重试');
    }).finally(() => setLoading(false));
  };

  return (
    <div className="min-h-screen bg-surface-bg flex items-center justify-center p-4">
      <div className="glass rounded-3xl p-8 w-full max-w-sm shadow-xl">
        <div className="text-center mb-6">
          <span className="text-4xl">💔</span>
          <h1 className="text-2xl font-bold text-text-main mt-2">失恋广场</h1>
          <p className="text-text-muted text-sm mt-1">每一种情绪都值得被听见</p>
        </div>

        <div className="flex bg-surface-warm rounded-xl p-1 mb-6">
          {(['login', 'register'] as const).map(t => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(''); }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t ? 'bg-white text-primary shadow-sm' : 'text-text-muted'
              }`}
            >
              {t === 'login' ? '登录' : '注册'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="用户名"
              className="w-full px-4 py-3 rounded-xl bg-surface-warm border-0 outline-none focus:ring-2 focus:ring-primary/30 text-text-main"
            />
          </div>
          <div>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="密码"
              className="w-full px-4 py-3 rounded-xl bg-surface-warm border-0 outline-none focus:ring-2 focus:ring-primary/30 text-text-main"
            />
          </div>
          {error && <p className="text-red-400 text-sm text-center">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl gradient-warm text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? '处理中...' : tab === 'login' ? '登录' : '注册'}
          </button>
        </form>
      </div>
    </div>
  );
}
