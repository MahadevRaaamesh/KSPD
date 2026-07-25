import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, Fingerprint, Radar, Waypoints, BrainCircuit, TriangleAlert } from 'lucide-react';
import { useAuth } from '../services/auth';
import { login } from '../services/api';
import './Login.css';

const FEATURES = [
  { icon: Radar, text: 'Spatiotemporal hotspot detection across 14 districts' },
  { icon: Waypoints, text: 'Criminal network & repeat-offender link analysis' },
  { icon: BrainCircuit, text: 'AI copilot with semantic FIR case matching' },
];

const Login = () => {
  const { loginSession } = useAuth();
  const navigate = useNavigate();
  const [badgeId, setBadgeId] = useState('KSP-1054');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setError('');
    setBusy(true);
    try {
      const session = await login(badgeId.trim(), password);
      loginSession(session);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.status === 401 ? 'Invalid credentials. Access denied.' : err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-left">
        <div className="login-brand">
          <div className="login-mark"><Eye size={26} strokeWidth={2.2} /></div>
          <div>
            <div className="login-wordmark">DRISHTI</div>
            <div className="login-kannada">ದೃಷ್ಟಿ · ಕರ್ನಾಟಕ ರಾಜ್ಯ ಪೊಲೀಸ್</div>
          </div>
        </div>

        <div className="login-hero">
          <h1>
            Every pattern<br />tells a story.
          </h1>
          <p>
            AI-driven crime analytics & intelligence for the Karnataka State
            Police — from fragmented records to proactive policing.
          </p>
          <div className="login-features">
            {FEATURES.map(({ icon: Icon, text }) => (
              <div className="login-feature" key={text}>
                <Icon size={16} strokeWidth={2} />
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="login-classification mono">
          RESTRICTED · FOR OFFICIAL USE ONLY · SCRB / KSP
        </div>
      </div>

      <div className="login-right">
        <form className="login-card corner-ticks" onSubmit={handleSubmit}>
          <div className="micro-label" style={{ marginBottom: 6 }}>
            <span className="tick" />Officer Authentication
          </div>
          <h2>Secure Sign-in</h2>
          <p className="login-card-sub">Verify your service credentials to access the intelligence console.</p>

          <label className="login-label" htmlFor="badge">Badge ID</label>
          <div className="login-input-wrap">
            <Fingerprint size={15} />
            <input
              id="badge"
              className="input mono"
              value={badgeId}
              onChange={(e) => setBadgeId(e.target.value)}
              autoComplete="username"
              spellCheck={false}
              required
            />
          </div>

          <label className="login-label" htmlFor="pass">Password</label>
          <div className="login-input-wrap">
            <Eye size={15} />
            <input
              id="pass"
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div className="error-banner" role="alert">
              <TriangleAlert size={15} /> {error}
            </div>
          )}

          <button className="btn btn-accent login-submit" type="submit" disabled={busy}>
            {busy ? <span className="spinner" style={{ borderTopColor: 'var(--accent-ink)' }} /> : 'Authenticate'}
          </button>

          <div className="login-demo mono">DEMO ACCESS · KSP-1054 / drishti</div>
        </form>
      </div>
    </div>
  );
};

export default Login;
