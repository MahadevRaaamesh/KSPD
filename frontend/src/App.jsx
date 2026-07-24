import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import CrimeMap from './pages/CrimeMap';
import NetworkGraph from './pages/NetworkGraph';
import CopilotChat from './pages/CopilotChat';
import Login from './pages/Login';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/" replace /> : <Login onLogin={() => setIsAuthenticated(true)} />
        } />
        
        <Route path="/" element={
          isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
        }>
          <Route index element={<Dashboard />} />
          <Route path="map" element={<CrimeMap />} />
          <Route path="graph" element={<NetworkGraph />} />
          <Route path="copilot" element={<CopilotChat />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
