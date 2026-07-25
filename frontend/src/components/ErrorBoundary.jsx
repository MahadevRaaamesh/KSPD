import { Component } from 'react';
import { TriangleAlert, RefreshCw } from 'lucide-react';

/**
 * Catches render errors in a page module so one broken panel never
 * white-screens the whole console. Navigating to another route
 * (a changed resetKey) clears the error automatically.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, lastKey: props.resetKey };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  static getDerivedStateFromProps(props, state) {
    if (props.resetKey !== state.lastKey) {
      return { error: null, lastKey: props.resetKey };
    }
    return null;
  }

  render() {
    if (this.state.error) {
      return (
        <div className="empty-state" style={{ paddingTop: 80 }}>
          <TriangleAlert size={36} color="var(--status-serious)" />
          <div className="empty-title">This module hit an unexpected error</div>
          <div className="empty-sub">{String(this.state.error?.message || this.state.error)}</div>
          <button className="btn" onClick={() => this.setState({ error: null })}>
            <RefreshCw size={14} /> Reload module
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
