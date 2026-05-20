import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { SensorPage } from './pages/SensorPage';
import { ChatPage } from './pages/ChatPage';
import { HomePage } from './pages/HomePage';
import { SettingsPage } from './pages/SettingsPage';
import { LabPage } from './pages/LabPage';
import { ReportPage } from './pages/ReportPage';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/sensor" element={<SensorPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/lab" element={<LabPage />} />
        <Route path="/report" element={<ReportPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
