import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Map, Network, MessageSquareText, ShieldAlert } from 'lucide-react';
import './Sidebar.css';

const Sidebar = () => {
  const navItems = [
    { path: '/', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { path: '/map', label: 'Crime Map', icon: <Map size={20} /> },
    { path: '/graph', label: 'Knowledge Graph', icon: <Network size={20} /> },
    { path: '/copilot', label: 'AI Copilot', icon: <MessageSquareText size={20} /> },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <ShieldAlert size={28} className="logo-icon" />
        <h2 className="text-gradient">KSPD</h2>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            end={item.path === '/'}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="glass-card user-card">
          <div className="avatar">O</div>
          <div className="user-info">
            <span className="user-name">Officer Auth</span>
            <span className="user-role">Administrator</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
