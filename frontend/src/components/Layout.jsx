import { Outlet, useLocation } from 'react-router-dom';
import { Suspense, useEffect, useState } from 'react';
import Sidebar from './Sidebar';
import ErrorBoundary from './ErrorBoundary';
import './Layout.css';

const PAGE_META = {
  '/': { title: 'Command Dashboard', sub: 'Strategic intelligence overview · Karnataka State Police' },
  '/map': { title: 'GeoIntel Crime Map', sub: 'Spatiotemporal hotspots & cluster analysis' },
  '/network': { title: 'Network Explorer', sub: 'Criminal link analysis & repeat-offender tracking' },
  '/search': { title: 'Case Matcher', sub: 'AI semantic search across FIR narratives' },
  '/copilot': { title: 'AI Copilot', sub: 'Conversational crime intelligence analyst' },
};

function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const date = now
    .toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
    .toUpperCase();
  const time = now.toLocaleTimeString('en-IN', { hour12: false });
  return (
    <div className="topbar-clock mono" title="Local time">
      <span className="clock-date">{date}</span>
      <span className="clock-time">{time}</span>
    </div>
  );
}

const Layout = () => {
  const location = useLocation();
  const meta = PAGE_META[location.pathname] || PAGE_META['/'];

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-column">
        <header className="topbar">
          <div className="topbar-titles">
            <div className="topbar-title">{meta.title}</div>
            <div className="topbar-sub">{meta.sub}</div>
          </div>
          <div className="topbar-right">
            <div className="chip chip-good"><span className="live-dot" /> LIVE FEED</div>
            <Clock />
          </div>
        </header>
        <main className={`main-content${['/map', '/network', '/copilot'].includes(location.pathname) ? ' bleed' : ''}`}>
          <ErrorBoundary resetKey={location.pathname}>
            <Suspense fallback={<div className="module-loading"><span className="spinner" /></div>}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
};

export default Layout;
