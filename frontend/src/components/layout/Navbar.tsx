import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpen, ChevronDown, FolderOpen, Heart, Home, LogOut, Settings, Upload, Users } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export default function Navbar() {
  const { user, isLoggedIn, loading, logout } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  if (location.pathname === '/login') return null;

  const links = [
    { to: '/', label: '首页', icon: Home },
    { to: '/upload', label: '创作', icon: Upload },
    { to: '/community', label: '故事社区', icon: Users },
    { to: '/learn', label: '灵感教学', icon: BookOpen },
  ];

  return (
    <nav className="glass-strong fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 shadow-sm">
      <Link to="/" className="flex items-center gap-2 group">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg gradient-primary">
          <Heart size={18} className="text-white" />
        </div>
        <div className="leading-tight">
          <span className="block text-lg font-bold text-primary">
            MuseCut
          </span>
          <span className="hidden text-[10px] font-medium uppercase tracking-[0.16em] text-text-muted md:block">
            emotion studio
          </span>
        </div>
      </Link>

      <div className="flex items-center gap-1">
        {links.map(({ to, label, icon: Icon }) => {
          const isHome = to === '/';
          const active = isHome
            ? location.pathname === '/'
            : location.pathname.startsWith(to);
          return (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 ${
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-text-secondary hover:text-primary hover:bg-primary/5'
              }`}
            >
              <Icon size={16} />
              <span className="hidden sm:inline">{label}</span>
            </Link>
          );
        })}
      </div>

      <div className="relative flex items-center gap-3">
        {isLoggedIn ? (
          <>
            <button
              onClick={() => setOpen(value => !value)}
              className="flex items-center gap-2 rounded-lg px-1.5 py-1 transition-colors hover:bg-primary/5"
              aria-label="打开个人中心菜单"
            >
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt="" className="h-8 w-8 rounded-lg object-cover" />
              ) : (
                <span className="flex h-8 w-8 items-center justify-center rounded-lg gradient-primary text-xs font-bold text-white">
                  {user?.username?.[0]?.toUpperCase() || 'U'}
                </span>
              )}
              <ChevronDown size={14} className={`text-text-muted transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>
            {open && (
              <div className="absolute right-0 top-11 w-64 rounded-lg border border-black/10 bg-white p-2 shadow-xl">
                <div className="border-b border-black/5 px-3 py-2">
                  <p className="truncate text-sm font-semibold text-text-main">{user?.username}</p>
                  <p className="mt-0.5 text-xs text-text-muted">个人中心与创作任务</p>
                </div>
                <Link
                  to="/profile#settings"
                  onClick={() => setOpen(false)}
                  className="mt-2 flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-text-secondary hover:bg-primary/5 hover:text-primary"
                >
                  <FolderOpen size={16} /> 个人中心
                </Link>
                <Link
                  to="/profile"
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-text-secondary hover:bg-primary/5 hover:text-primary"
                >
                  <Settings size={16} /> 资料设置
                </Link>
                <button
                  onClick={() => {
                    setOpen(false);
                    logout();
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium text-text-secondary hover:bg-red-50 hover:text-red-600"
                >
                  <LogOut size={16} /> 退出登录
                </button>
              </div>
            )}
          </>
        ) : loading ? (
          <span className="h-8 w-20 rounded-lg bg-surface-warm" />
        ) : (
          <Link
            to="/login"
            className="min-w-[52px] whitespace-nowrap rounded-lg gradient-primary px-3 py-2 text-center text-sm font-medium text-white transition-opacity hover:opacity-90 sm:px-4"
          >
            登录
          </Link>
        )}
      </div>
    </nav>
  );
}
