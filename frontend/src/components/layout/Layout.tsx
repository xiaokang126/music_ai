import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

export default function Layout() {
  return (
    <div className="min-h-screen bg-surface-bg">
      <Navbar />
      <main className="pt-16 pb-8 px-4 max-w-6xl mx-auto">
        <Outlet />
      </main>
    </div>
  );
}
