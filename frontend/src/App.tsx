import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ChatPage } from './pages/ChatPage';
import { HomePage } from './pages/HomePage';
import { LabPage } from './pages/LabPage';
import { SensorPage } from './pages/SensorPage';
import { SettingsPage } from './pages/SettingsPage';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/sensor" element={<SensorPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/lab" element={<LabPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
