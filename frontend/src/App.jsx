import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { lazy, useCallback, useMemo, useState } from 'react';
import Layout from './components/Layout';
import Login from './pages/Login';
import { AuthContext } from './services/auth';
import { getSession, setSession, clearSession } from './services/api';

// Each console module carries a heavy visualization library (ECharts,
// MapLibre, Cytoscape). Splitting them keeps the initial load light and
// fetches each engine only when an officer opens that module.
const Dashboard = lazy(() => import('./pages/Dashboard'));
const CrimeMap = lazy(() => import('./pages/CrimeMap'));
const NetworkGraph = lazy(() => import('./pages/NetworkGraph'));
const CaseSearch = lazy(() => import('./pages/CaseSearch'));
const CopilotChat = lazy(() => import('./pages/CopilotChat'));

function App() {
  const [session, setSessionState] = useState(getSession);

  const loginSession = useCallback((s) => {
    setSession(s);
    setSessionState(s);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setSessionState(null);
  }, []);

  const auth = useMemo(
    () => ({ session, loginSession, logout }),
    [session, loginSession, logout],
  );

  return (
    <AuthContext.Provider value={auth}>
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={session ? <Navigate to="/" replace /> : <Login />}
          />
          <Route
            path="/"
            element={session ? <Layout /> : <Navigate to="/login" replace />}
          >
            <Route index element={<Dashboard />} />
            <Route path="map" element={<CrimeMap />} />
            <Route path="network" element={<NetworkGraph />} />
            <Route path="search" element={<CaseSearch />} />
            <Route path="copilot" element={<CopilotChat />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;
