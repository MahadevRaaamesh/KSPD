import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  LayoutDashboard, Map, Waypoints, ScanSearch, BrainCircuit,
  LogOut, Eye,
} from 'lucide-react';
import { useAuth } from '../services/auth';
import { fetchHealth } from '../services/api';
import './Sidebar.css';

const NAV_SECTIONS = [
  {
    label: 'Operations',
    items: [
      { path: '/', label: 'Command Dashboard', icon: LayoutDashboard },
      { path: '/map', label: 'GeoIntel Map', icon: Map },
      { path: '/network', label: 'Network Explorer', icon: Waypoints },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { path: '/search', label: 'Case Matcher', icon: ScanSearch },
      { path: '/copilot', label: 'AI Copilot', icon: BrainCircuit },
    ],
  },
];

const Sidebar = () => {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const [apiUp, setApiUp] = useState(null);
  const [indexed, setIndexed] = useState(null);

  useEffect(() => {
    let alive = true;
    const check = () =>
      fetchHealth()
        .then((h) => { if (alive) { setApiUp(true); setIndexed(h?.firs_indexed ?? null); } })
        .catch(() => { if (alive) setApiUp(false); });
    check();
    const t = setInterval(check, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const officer = session?.officer || {};
  const initials = (officer.name || 'O')
    .replace(/^(Insp|SI|PSI|ASI|DySP)\.?\s+/i, '')
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark"><Eye size={20} strokeWidth={2.2} /></div>
        <div>
          <div className="brand-name">DRISHTI</div>
          <div className="brand-sub">KSP · CRIME INTELLIGENCE</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_SECTIONS.map((section) => (
          <div className="nav-section" key={section.label}>
            <div className="micro-label nav-section-label"><span className="tick" />{section.label}</div>
            {section.items.map(({ path, label, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                end={path === '/'}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <Icon size={17} strokeWidth={2} />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sys-status">
          <span className={`sys-dot ${apiUp === null ? 'wait' : apiUp ? 'up' : 'down'}`} />
          <span className="mono sys-text">
            {apiUp === null ? 'CHECKING API…' : apiUp ? `API ONLINE${indexed != null ? ` · ${indexed} FIRs` : ''}` : 'API OFFLINE'}
          </span>
        </div>
        <div className="officer-card">
          <div className="officer-avatar">{initials}</div>
          <div className="grow officer-meta">
            <div className="officer-name">{officer.name || 'Officer'}</div>
            <div className="officer-rank mono">{officer.badge_id || ''} · {officer.rank || 'KSP'}</div>
          </div>
          <button
            className="btn-ghost logout-btn"
            title="Sign out"
            aria-label="Sign out"
            onClick={() => { logout(); navigate('/login'); }}
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
