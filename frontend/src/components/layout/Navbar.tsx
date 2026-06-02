import { Link, useLocation } from 'react-router-dom';
import { Music, BookOpen, PlusCircle, User, Heart, Sparkles } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export default function Navbar() {
  const { user, isLoggedIn, logout } = useAuth();
  const location = useLocation();

  const links = [
    { to: '/square', label: '广场', icon: Music },
    { to: '/theory', label: '乐理', icon: BookOpen },
    { to: '/create', label: '创作', icon: PlusCircle },
    { to: '/resonance', label: '共鸣', icon: Sparkles },
    { to: '/healing', label: '治愈', icon: Heart },
  ];

  if (location.pathname === '/login') return null;

  return (
    <nav className="glass-strong fixed top-0 left-0 right-0 z-50 px-4 py-3 flex items-center justify-between">
      <Link to="/" className="flex items-center gap-2 group">
        <span className="text-2xl">💔</span>
        <span className="text-lg font-bold text-primary bg-gradient-to-r from-primary to-primary-light bg-clip-text text-transparent">
          失恋广场
        </span>
      </Link>

      <div className="flex items-center gap-1">
        {links.map(({ to, label, icon: Icon }) => {
          const active = location.pathname === to || location.pathname.startsWith(to + '/');
          return (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                active
                  ? 'bg-primary/15 text-primary'
                  : 'text-text-secondary hover:text-primary hover:bg-primary/5'
              }`}
            >
              <Icon size={16} />
              <span className="hidden sm:inline">{label}</span>
            </Link>
          );
        })}
      </div>

      <div className="flex items-center gap-3">
        {isLoggedIn ? (
          <>
            <Link
              to="/profile"
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl hover:bg-primary/5 transition-colors"
            >
              <div className="w-7 h-7 rounded-full gradient-warm flex items-center justify-center text-white text-xs font-bold">
                {user?.username?.[0]?.toUpperCase()}
              </div>
              <span className="text-sm text-text-main hidden sm:inline">{user?.username}</span>
            </Link>
            <button onClick={logout} className="text-xs text-text-muted hover:text-text-secondary transition-colors">
              退出
            </button>
          </>
        ) : (
          <Link
            to="/login"
            className="px-4 py-2 rounded-xl gradient-warm text-white text-sm font-medium hover:opacity-90 transition-opacity"
          >
            登录
          </Link>
        )}
      </div>
    </nav>
  );
}
