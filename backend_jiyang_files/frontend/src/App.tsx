import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { EventsPage } from './pages/EventsPage';
import { TestPage } from './pages/TestPage';
import { SensorPage } from './pages/SensorPage';
import { ChatPage } from './pages/ChatPage';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/test" element={<TestPage />} />
        <Route path="/sensor" element={<SensorPage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
