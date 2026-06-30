import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { registerUser, loginUser } from '../services/authService';

export default function LoginPage() {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { from?: string; reason?: string } | null;
  const returnTo = state?.from || '/profile';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('请填写完整信息');
      return;
    }
    setLoading(true);
    setError('');
    const fn = tab === 'login' ? loginUser : registerUser;
    fn(username, password)
      .then(({ token, user }) => {
        login(user, token);
        navigate(returnTo, { replace: true });
      })
      .catch((err: unknown) => {
        console.error('Auth error:', err);
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as { response?: { data?: { detail?: string }; status?: number } };
          setError(axiosErr.response?.data?.detail || `服务器错误(${axiosErr.response?.status})`);
        } else if (err && typeof err === 'object' && 'request' in err) {
          setError('无法连接到服务器，请检查网络');
        } else if (err instanceof Error) {
          setError(err.message || '操作失败，请重试');
        } else {
          setError('操作失败，请重试');
        }
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="min-h-screen bg-surface-bg flex items-center justify-center p-4">
      <div className="glass rounded-3xl p-8 w-full max-w-sm shadow-xl">
        <div className="text-center mb-6">
          <div className="w-14 h-14 rounded-2xl gradient-primary flex items-center justify-center mx-auto mb-4">
            <span className="text-white font-bold text-2xl">M</span>
          </div>
          <h1 className="text-2xl font-bold text-text-main">MuseCut</h1>
          <p className="text-text-muted text-sm mt-1">AI短视频配乐导演</p>
        </div>
        {state?.reason && (
          <div className="mb-5 rounded-xl bg-primary/10 px-4 py-3 text-sm leading-6 text-primary">
            {state.reason}
          </div>
        )}

        <div className="flex bg-surface-warm rounded-xl p-1 mb-6">
          {(['login', 'register'] as const).map((t) => (
            <button
              key={t}
              onClick={() => {
                setTab(t);
                setError('');
              }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t
                  ? 'bg-white text-primary shadow-sm'
                  : 'text-text-muted'
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
              onChange={(e) => setUsername(e.target.value)}
              placeholder="用户名"
              className="w-full px-4 py-3 rounded-xl bg-surface-warm border-0 outline-none focus:ring-2 focus:ring-primary/30 text-text-main placeholder:text-text-muted"
            />
          </div>
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="密码"
              className="w-full px-4 py-3 rounded-xl bg-surface-warm border-0 outline-none focus:ring-2 focus:ring-primary/30 text-text-main placeholder:text-text-muted"
            />
          </div>
          {error && (
            <p className="text-red-500 text-sm text-center bg-red-50 py-2 rounded-lg">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl gradient-primary text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? '处理中...' : tab === 'login' ? '登录' : '注册'}
          </button>
        </form>
      </div>
    </div>
  );
}
