import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Layout from './components/layout/Layout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import UploadPage from './pages/UploadPage';
import EditorPage from './pages/EditorPage';
import PreviewPage from './pages/PreviewPage';
import ExportPage from './pages/ExportPage';
import CommunityPage from './pages/CommunityPage';
import PostDetailPage from './pages/PostDetailPage';
import LearnPage from './pages/LearnPage';
import LearnDetailPage from './pages/LearnDetailPage';
import ProfilePage from './pages/ProfilePage';
import { AuthProvider } from './hooks/useAuth';
import { audioEngine } from './engine/musecutEngine';

function RouteAudioGuard() {
  const location = useLocation();

  useEffect(() => {
    audioEngine.stop(false);
  }, [location.pathname]);

  return null;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <RouteAudioGuard />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/editor/:projectId" element={<EditorPage />} />
            <Route path="/preview/:projectId" element={<PreviewPage />} />
            <Route path="/export/:projectId" element={<ExportPage />} />
            <Route path="/community" element={<CommunityPage />} />
            <Route path="/community/:postId" element={<PostDetailPage />} />
            <Route path="/learn" element={<LearnPage />} />
            <Route path="/learn/:lessonId" element={<LearnDetailPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
