import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ChatPage } from './pages/ChatPage';
import { LabPage } from './pages/LabPage';
import { ReportPage } from './pages/ReportPage';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<LabPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/lab" element={<LabPage />} />
        <Route path="/report" element={<ReportPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
