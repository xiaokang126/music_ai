import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-surface-bg">
      <Navbar />
      <main className="pt-16 flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-black/10 bg-white px-4 py-6 text-center text-sm text-text-muted">
        <p>&copy; {new Date().getFullYear()} MuseCut - AI 声音叙事与情感表达平台</p>
      </footer>
    </div>
  );
}
