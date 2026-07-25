import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import './StatCard.css';

function Sparkline({ data, color = 'var(--s1)' }) {
  if (!data || data.length < 2) return null;
  const w = 68, h = 26, pad = 2;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2);
    const y = h - pad - ((v - min) / span) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg className="stat-spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <polyline
        points={pts.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * StatCard — hero-number tile.
 * delta: e.g. "+12.4%" · deltaDir: 'up'|'down'|'flat' · deltaGood: whether the direction is desirable
 */
const StatCard = ({ label, value, icon: Icon, delta, deltaDir = 'flat', deltaGood = true, spark, sparkColor }) => {
  // A direction arrow only means something for an actual change; a plain
  // supporting figure ("1,417 solved") gets no icon.
  const DeltaIcon = deltaDir === 'up' ? ArrowUpRight : deltaDir === 'down' ? ArrowDownRight : null;
  return (
    <div className="panel stat-card">
      <div className="stat-top">
        <span className="micro-label"><span className="tick" />{label}</span>
        {Icon && <Icon size={15} className="stat-icon" strokeWidth={2} />}
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-bottom">
        {delta != null && (
          <span className={`stat-delta ${DeltaIcon ? (deltaGood ? 'good' : 'bad') : 'neutral'}`}>
            {DeltaIcon && <DeltaIcon size={13} strokeWidth={2.4} />}
            <span className="num">{delta}</span>
          </span>
        )}
        <span className="grow" />
        {spark && <Sparkline data={spark} color={sparkColor} />}
      </div>
    </div>
  );
};

export default StatCard;
