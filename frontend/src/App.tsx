import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import HomePage from './pages/HomePage';
import SquarePage from './pages/SquarePage';
import CreatePage from './pages/CreatePage';
import TheoryPage from './pages/TheoryPage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import WorkDetailPage from './pages/WorkDetailPage';
import ResonancePage from './pages/ResonancePage';
import DiaryPage from './pages/DiaryPage';
import HealingPage from './pages/HealingPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/square" element={<SquarePage />} />
          <Route path="/create" element={<CreatePage />} />
          <Route path="/theory" element={<TheoryPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/work/:id" element={<WorkDetailPage />} />
          <Route path="/resonance" element={<ResonancePage />} />
          <Route path="/diary" element={<DiaryPage />} />
          <Route path="/healing" element={<HealingPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
