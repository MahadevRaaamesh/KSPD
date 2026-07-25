import { useCallback, useEffect, useMemo, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  FileText, Gauge, Users, Landmark, Activity, Siren, CircleCheck,
  TrendingUp, ArrowUpRight, ArrowDownRight, Minus, ChevronRight,
} from 'lucide-react';
import StatCard from '../components/StatCard';
import { PanelHeader, ErrorState, Skeleton, EmptyState } from '../components/ui';
import {
  fetchOverview, fetchTrends, fetchDistricts, fetchCategories,
  fetchIpcSections, fetchInsights, fetchRiskScores, fetchTimePatterns,
} from '../services/api';
import {
  SERIES, SEQ_BLUE, INK, SURFACE, axisTooltip, tooltip,
  catAxis, valAxis, baseGrid, baseText, legend,
} from '../services/chartTheme';
import './Dashboard.css';

const MONTH_OPTIONS = [
  { v: 6, label: 'Last 6 months' },
  { v: 12, label: 'Last 12 months' },
  { v: 24, label: 'Last 24 months' },
];

const RISK_META = {
  low: { chip: 'chip-good', label: 'LOW' },
  moderate: { chip: 'chip-warning', label: 'MODERATE' },
  elevated: { chip: 'chip-warning', label: 'ELEVATED' },
  high: { chip: 'chip-critical', label: 'HIGH' },
  critical: { chip: 'chip-critical', label: 'CRITICAL' },
};

const RISK_BAR = {
  low: 'var(--status-good)',
  moderate: 'var(--status-warning)',
  elevated: 'var(--status-serious)',
  high: 'var(--status-critical)',
  critical: 'var(--status-critical)',
};

const INSIGHT_ICON = { spike: Siren, success: CircleCheck, info: TrendingUp };

const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function fmtMonth(period) {
  // "2026-03" -> "Mar 26"
  const [y, m] = period.split('-');
  const names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${names[Number(m) - 1]} ${y.slice(2)}`;
}

const Dashboard = () => {
  const [overview, setOverview] = useState(null);
  const [districts, setDistricts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [ipc, setIpc] = useState([]);
  const [insights, setInsights] = useState([]);
  const [risks, setRisks] = useState([]);
  const [trends, setTrends] = useState([]);
  const [timePatterns, setTimePatterns] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [trendsBusy, setTrendsBusy] = useState(false);

  // Filter row scoped to the trend + time-pattern panels
  const [district, setDistrict] = useState('');
  const [category, setCategory] = useState('');
  const [months, setMonths] = useState(12);

  const loadStatic = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchOverview(),
      fetchDistricts(),
      fetchCategories(),
      fetchIpcSections(10),
      fetchInsights(),
      fetchRiskScores(),
    ])
      .then(([ov, ds, cats, ipcs, ins, rs]) => {
        setOverview(ov);
        setDistricts(Array.isArray(ds) ? ds : []);
        setCategories(Array.isArray(cats) ? cats : []);
        setIpc(Array.isArray(ipcs) ? ipcs : []);
        setInsights(Array.isArray(ins) ? ins : []);
        setRisks(Array.isArray(rs) ? rs : []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(loadStatic, [loadStatic]);

  useEffect(() => {
    let alive = true;
    setTrendsBusy(true);
    Promise.all([
      fetchTrends({ district, crime_category: category, months }),
      fetchTimePatterns(district),
    ])
      .then(([t, tp]) => {
        if (!alive) return;
        setTrends(Array.isArray(t) ? t : []);
        setTimePatterns(tp);
      })
      .catch(() => { if (alive) { setTrends([]); setTimePatterns(null); } })
      .finally(() => alive && setTrendsBusy(false));
    return () => { alive = false; };
  }, [district, category, months]);

  /* ---------------- Derived KPIs ---------------- */
  const clearance = overview
    ? Math.round((overview.cases_solved / Math.max(overview.total_firs, 1)) * 100)
    : 0;

  const spark = useMemo(() => trends.map((t) => t.count), [trends]);

  const momDelta = useMemo(() => {
    if (trends.length < 3) return null;
    // compare the two most recent COMPLETE months
    const prev = trends[trends.length - 3].count;
    const last = trends[trends.length - 2].count;
    if (!prev) return null;
    const pct = ((last - prev) / prev) * 100;
    return {
      pct: `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}% MoM`,
      dir: pct > 2 ? 'up' : pct < -2 ? 'down' : 'flat',
      good: pct <= 0, // rising crime is bad news
    };
  }, [trends]);

  /* ---------------- Chart options ---------------- */
  const trendOption = useMemo(() => ({
    textStyle: baseText,
    grid: { ...baseGrid, top: 18 },
    tooltip: { ...axisTooltip },
    xAxis: catAxis(trends.map((t) => fmtMonth(t.period)), { boundaryGap: false }),
    yAxis: valAxis(),
    series: [{
      name: 'Reported FIRs',
      type: 'line',
      data: trends.map((t) => t.count),
      smooth: 0.35,
      symbol: 'circle',
      symbolSize: 7,
      showSymbol: false,
      lineStyle: { width: 2, color: SERIES[0] },
      itemStyle: { color: SERIES[0], borderColor: SURFACE, borderWidth: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(57, 135, 229, 0.28)' },
            { offset: 1, color: 'rgba(57, 135, 229, 0)' },
          ],
        },
      },
    }],
  }), [trends]);

  const categoryOption = useMemo(() => {
    const cats = [...categories].reverse(); // horizontal bars read top-down after reverse
    return {
      textStyle: baseText,
      grid: { ...baseGrid, top: 26, left: 4 },
      tooltip: { ...axisTooltip, axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(148,163,184,0.06)' } } },
      legend: legend(),
      xAxis: valAxis(),
      yAxis: catAxis(cats.map((c) => c.category), {
        axisLabel: { color: INK.secondary, fontSize: 11, fontFamily: '"Segoe UI", system-ui, sans-serif' },
      }),
      series: [
        {
          name: 'Reported',
          type: 'bar',
          data: cats.map((c) => c.count),
          barWidth: 9,
          itemStyle: { color: SERIES[0], borderRadius: [0, 4, 4, 0] },
        },
        {
          name: 'Solved',
          type: 'bar',
          data: cats.map((c) => c.solved),
          barWidth: 9,
          barGap: '38%',
          itemStyle: { color: SERIES[2], borderRadius: [0, 4, 4, 0] },
        },
      ],
    };
  }, [categories]);

  const heatOption = useMemo(() => {
    if (!timePatterns?.matrix?.length) return null;
    const max = Math.max(...timePatterns.matrix.map((c) => c.count), 1);
    return {
      textStyle: baseText,
      grid: { left: 8, right: 14, top: 10, bottom: 4, containLabel: true },
      tooltip: {
        ...tooltip,
        formatter: (p) =>
          `<b>${DOW[p.value[1]]} ${String(p.value[0]).padStart(2, '0')}:00</b> · ${p.value[2]} incidents`,
      },
      xAxis: catAxis(Array.from({ length: 24 }, (_, h) => (h % 3 === 0 ? `${String(h).padStart(2, '0')}` : '')), {
        axisLine: { show: false }, splitArea: { show: false },
      }),
      yAxis: catAxis(DOW, { axisLine: { show: false } }),
      visualMap: {
        show: false, min: 0, max,
        inRange: { color: [SEQ_BLUE[0], SEQ_BLUE[2], SEQ_BLUE[4], SEQ_BLUE[6]] },
      },
      series: [{
        type: 'heatmap',
        data: timePatterns.matrix.map((c) => [c.hour, c.dow, c.count]),
        itemStyle: { borderColor: SURFACE, borderWidth: 2, borderRadius: 2 },
        emphasis: { itemStyle: { borderColor: INK.secondary, borderWidth: 1 } },
      }],
    };
  }, [timePatterns]);

  const ipcOption = useMemo(() => {
    const maxIdx = ipc.reduce((mi, s, i) => (s.count > (ipc[mi]?.count ?? -1) ? i : mi), 0);
    return {
      textStyle: baseText,
      grid: { ...baseGrid, top: 22 },
      tooltip: {
        ...axisTooltip,
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(148,163,184,0.06)' } },
        formatter: (ps) => {
          const p = Array.isArray(ps) ? ps[0] : ps;
          const row = ipc[p.dataIndex];
          return `<b>IPC ${row.section}</b> · ${row.count} cases<br/><span style="color:#a8b3c4">${row.description || ''}</span>`;
        },
      },
      xAxis: catAxis(ipc.map((s) => s.section)),
      yAxis: valAxis(),
      series: [{
        name: 'Cases',
        type: 'bar',
        data: ipc.map((s, i) => ({
          value: s.count,
          label: i === maxIdx
            ? { show: true, position: 'top', color: INK.secondary, fontSize: 10.5, fontFamily: '"Cascadia Mono", monospace' }
            : undefined,
        })),
        barWidth: 14,
        itemStyle: { color: SERIES[0], borderRadius: [4, 4, 0, 0] },
      }],
    };
  }, [ipc]);

  /* ---------------- Render ---------------- */
  if (error) return <div className="page-enter"><ErrorState message={error} onRetry={loadStatic} /></div>;

  return (
    <div className="page-enter dash">
      {/* KPI row */}
      <div className="kpi-row">
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} h={104} />)
        ) : (
          <>
            <StatCard
              label="Total FIRs" value={overview.total_firs.toLocaleString('en-IN')}
              icon={FileText} spark={spark}
              delta={momDelta?.pct} deltaDir={momDelta?.dir} deltaGood={momDelta?.good}
            />
            <StatCard
              label="Clearance Rate" value={`${clearance}%`} icon={Gauge}
              delta={`${overview.cases_solved.toLocaleString('en-IN')} solved`} deltaDir="flat" deltaGood
            />
            <StatCard
              label="Under Investigation" value={overview.cases_pending.toLocaleString('en-IN')} icon={Activity}
            />
            <StatCard
              label="Chargesheets Filed" value={overview.chargesheets_filed.toLocaleString('en-IN')} icon={Landmark}
            />
            <StatCard
              label="Accused on Record" value={overview.total_accused.toLocaleString('en-IN')} icon={Users}
            />
          </>
        )}
      </div>

      {/* Emerging trend alerts */}
      {!loading && insights.length > 0 && (
        <section aria-label="Emerging trend alerts">
          <div className="micro-label alerts-label"><span className="tick" />Emerging Trend Alerts · Last 30 Days</div>
          <div className="alerts-strip">
            {insights.map((ins) => {
              const Icon = INSIGHT_ICON[ins.type] || TrendingUp;
              const critical = ins.severity === 'critical';
              return (
                <div key={ins.id || ins.title} className={`panel alert-card ${ins.type}${critical ? ' pulse-critical' : ''}`}>
                  <div className={`alert-icon ${ins.type}${critical ? ' critical' : ''}`}><Icon size={16} /></div>
                  <div className="grow">
                    <div className="alert-title">
                      {ins.title}
                      {ins.metric && (
                        <span className={`chip ${ins.type === 'spike' ? 'chip-critical' : ins.type === 'success' ? 'chip-good' : 'chip-accent'}`}>
                          {ins.metric}
                        </span>
                      )}
                    </div>
                    <div className="alert-desc">{ins.description}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Trends + Risk index */}
      <div className="dash-grid main-grid">
        <div className="panel corner-ticks">
          <PanelHeader
            label="Temporal Analysis"
            title="Crime Trend — Reported FIRs"
            right={
              <div className="filter-row">
                <select className="select" value={district} onChange={(e) => setDistrict(e.target.value)} aria-label="District filter">
                  <option value="">All districts</option>
                  {districts.map((d) => <option key={d.district} value={d.district}>{d.district}</option>)}
                </select>
                <select className="select" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category filter">
                  <option value="">All categories</option>
                  {categories.map((c) => <option key={c.category} value={c.category}>{c.category}</option>)}
                </select>
                <select className="select" value={months} onChange={(e) => setMonths(Number(e.target.value))} aria-label="Time window">
                  {MONTH_OPTIONS.map((m) => <option key={m.v} value={m.v}>{m.label}</option>)}
                </select>
              </div>
            }
          />
          <div className={`panel-pad${trendsBusy ? ' dimmed-refetch' : ''}`}>
            {trends.length === 0 && !trendsBusy
              ? <EmptyState title="No FIRs match these filters" sub="Widen the district, category or time window." />
              : <ReactECharts option={trendOption} style={{ height: 296 }} opts={{ renderer: 'svg' }} notMerge />}
          </div>
        </div>

        <div className="panel">
          <PanelHeader label="Predictive Model" title="District Risk Index" />
          <div className="risk-list">
            {loading ? <Skeleton h={296} style={{ margin: 16, width: 'auto' }} /> : risks.map((r) => {
              const meta = RISK_META[r.level] || RISK_META.moderate;
              const TrendIcon = r.trend === 'rising' ? ArrowUpRight : r.trend === 'falling' ? ArrowDownRight : Minus;
              return (
                <div className="risk-row" key={r.district} title={(r.drivers || []).join(' · ')}>
                  <div className="risk-head">
                    <span className="risk-name">{r.district}</span>
                    <TrendIcon
                      size={13}
                      className={`risk-trend ${r.trend === 'rising' ? 'bad' : r.trend === 'falling' ? 'good' : ''}`}
                    />
                    <span className={`chip ${meta.chip}`}>{meta.label}</span>
                    <span className="num risk-score">{r.score}</span>
                  </div>
                  <div className="risk-track">
                    <div
                      className="risk-fill"
                      style={{ width: `${r.score}%`, background: RISK_BAR[r.level] || 'var(--status-warning)' }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Categories + time-of-day */}
      <div className="dash-grid half-grid">
        <div className="panel">
          <PanelHeader label="Typology" title="Crime Categories — Reported vs Solved" />
          <div className="panel-pad">
            {loading ? <Skeleton h={272} /> : <ReactECharts option={categoryOption} style={{ height: 272 }} opts={{ renderer: 'svg' }} notMerge />}
          </div>
        </div>
        <div className="panel">
          <PanelHeader
            label="Spatiotemporal"
            title={`Incident Clock — Day × Hour${district ? ` · ${district}` : ''}`}
            right={timePatterns?.peak && (
              <span className="chip chip-accent">
                PEAK {DOW[timePatterns.peak.dow]} {String(timePatterns.peak.hour).padStart(2, '0')}:00
              </span>
            )}
          />
          <div className={`panel-pad${trendsBusy ? ' dimmed-refetch' : ''}`}>
            {heatOption
              ? <ReactECharts option={heatOption} style={{ height: 272 }} opts={{ renderer: 'svg' }} notMerge />
              : <Skeleton h={272} />}
          </div>
        </div>
      </div>

      {/* IPC + district table */}
      <div className="dash-grid half-grid">
        <div className="panel">
          <PanelHeader label="Legal Sections" title="Top IPC / Act Sections Invoked" />
          <div className="panel-pad">
            {loading ? <Skeleton h={252} /> : <ReactECharts option={ipcOption} style={{ height: 252 }} opts={{ renderer: 'svg' }} notMerge />}
          </div>
        </div>
        <div className="panel">
          <PanelHeader label="Jurisdictions" title="District Case Load" />
          <div className="district-table-wrap">
            {loading ? <Skeleton h={252} style={{ margin: 16, width: 'auto' }} /> : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>District</th>
                    <th className="num-cell">Cases</th>
                    <th className="num-cell">Solved</th>
                    <th className="num-cell">Pending</th>
                    <th style={{ width: '26%' }}>Clearance</th>
                  </tr>
                </thead>
                <tbody>
                  {districts.map((d) => {
                    const pct = Math.round((d.solved / Math.max(d.total_cases, 1)) * 100);
                    return (
                      <tr key={d.district}>
                        <td>{d.district}</td>
                        <td className="num-cell">{d.total_cases.toLocaleString('en-IN')}</td>
                        <td className="num-cell">{d.solved.toLocaleString('en-IN')}</td>
                        <td className="num-cell">{d.pending.toLocaleString('en-IN')}</td>
                        <td>
                          <div className="clearance-cell">
                            <div className="risk-track grow"><div className="risk-fill" style={{ width: `${pct}%`, background: 'var(--s1)' }} /></div>
                            <span className="num clearance-pct">{pct}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      <div className="dash-footnote mono">
        <ChevronRight size={11} /> DRISHTI ANALYTICAL ENGINE · DATA REFRESHED LIVE FROM SCRB RECORDS
      </div>
    </div>
  );
};

export default Dashboard;
