import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { User } from '../types';
import { getMe } from '../services/authService';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isLoggedIn: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredUser(): User | null {
  const stored = localStorage.getItem('user');
  if (!stored) return null;
  try {
    return JSON.parse(stored) as User;
  } catch {
    localStorage.removeItem('user');
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => readStoredUser());
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  }, []);

  const updateUser = useCallback((nextUser: User) => {
    localStorage.setItem('user', JSON.stringify(nextUser));
    setUser(nextUser);
  }, []);

  const login = useCallback((nextUser: User, token: string) => {
    localStorage.setItem('token', token);
    updateUser(nextUser);
  }, [updateUser]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      localStorage.removeItem('user');
      setUser(null);
      setLoading(false);
      return;
    }

    getMe()
      .then(updateUser)
      .catch(logout)
      .finally(() => setLoading(false));
  }, [logout, updateUser]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    isLoggedIn: !!user,
    login,
    logout,
    updateUser,
  }), [user, loading, login, logout, updateUser]);

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
