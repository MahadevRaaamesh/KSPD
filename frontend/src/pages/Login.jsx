import React, { useState } from 'react';
import { Shield } from 'lucide-react';
import './Login.css';

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (username === 'admin' && password === 'password') {
      onLogin();
    } else {
      setError('Invalid credentials. Hint: admin / password');
    }
  };

  return (
    <div className="login-container animate-fade-in">
      <div className="login-glass-card">
        <div className="login-header">
          <Shield size={48} className="icon-primary" style={{ marginBottom: '1rem' }} />
          <h1 className="text-gradient">KSP Analytics</h1>
          <p>Secure Portal Login</p>
        </div>
        
        {error && <div className="login-error">{error}</div>}
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label htmlFor="username">Username</label>
            <input 
              type="text" 
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
            />
          </div>
          
          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input 
              type="password" 
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
            />
          </div>
          
          <button type="submit" className="login-btn">
            Authenticate
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
