import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { BarChart3, BrainCircuit, FileText, Map, ScanSearch, Send, Waypoints } from 'lucide-react';
import { copilotQuery, fetchSuggestions, streamCopilot } from '../services/api';
import { SERIES, SURFACE, axisTooltip, baseGrid, baseText, catAxis, valAxis } from '../services/chartTheme';
import './CopilotChat.css';

const SUGGESTION_ICONS = {
  chart: BarChart3,
  search: ScanSearch,
  graph: Waypoints,
  table: FileText,
  map: Map,
};

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-03" -> "Mar 26"; anything else passes through unchanged. */
function fmtPeriod(period) {
  const s = String(period);
  const m = /^(\d{4})-(\d{2})/.exec(s);
  if (m) {
    const idx = Number(m[2]) - 1;
    if (idx >= 0 && idx < 12) return `${MONTHS[idx]} ${m[1].slice(2)}`;
  }
  return s;
}

function fmtCell(v) {
  if (typeof v === 'number') return v.toLocaleString('en-IN');
  if (v === null || v === undefined) return '—';
  return String(v);
}

/* ---------------- Mini visualizations ---------------- */

function TrendMiniChart({ rows }) {
  const option = useMemo(() => ({
    textStyle: baseText,
    grid: { ...baseGrid, top: 14 },
    tooltip: { ...axisTooltip },
    xAxis: catAxis(rows.map((r) => fmtPeriod(r.period)), { boundaryGap: false }),
    yAxis: valAxis(),
    series: [{
      name: 'Count',
      type: 'line',
      data: rows.map((r) => r.count),
      smooth: 0.35,
      symbol: 'circle',
      symbolSize: 6,
      showSymbol: false,
      lineStyle: { width: 2, color: SERIES[0] },
      itemStyle: { color: SERIES[0], borderColor: SURFACE, borderWidth: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(57, 135, 229, 0.24)' },
            { offset: 1, color: 'rgba(57, 135, 229, 0)' },
          ],
        },
      },
    }],
  }), [rows]);

  return <ReactECharts option={option} style={{ height: 180 }} opts={{ renderer: 'svg' }} notMerge />;
}

function BarMiniChart({ rows, catKey, valueKey }) {
  const option = useMemo(() => ({
    textStyle: baseText,
    grid: { ...baseGrid, top: 14 },
    tooltip: {
      ...axisTooltip,
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(148, 163, 184, 0.06)' } },
    },
    xAxis: catAxis(rows.map((r) => String(r[catKey])), {
      axisLabel: {
        color: '#64748b', fontSize: 10, fontFamily: '"Cascadia Mono", ui-monospace, monospace',
        formatter: (v) => (v.length > 11 ? `${v.slice(0, 10)}…` : v),
      },
    }),
    yAxis: valAxis(),
    series: [{
      name: valueKey.replace(/_/g, ' '),
      type: 'bar',
      data: rows.map((r) => r[valueKey]),
      barWidth: 10,
      itemStyle: { color: SERIES[0], borderRadius: [3, 3, 0, 0] },
    }],
  }), [rows, catKey, valueKey]);

  return <ReactECharts option={option} style={{ height: 180 }} opts={{ renderer: 'svg' }} notMerge />;
}

function VizTable({ rows }) {
  const cols = Object.keys(rows[0]);
  return (
    <table className="data-table">
      <thead>
        <tr>
          {cols.map((c) => (
            <th key={c} className={typeof rows[0][c] === 'number' ? 'num-th' : undefined}>
              {c.replace(/_/g, ' ')}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.slice(0, 6).map((r, i) => (
          <tr key={i}>
            {cols.map((c) => (
              <td key={c} className={typeof r[c] === 'number' ? 'num' : undefined}>{fmtCell(r[c])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/**
 * Post-stream visualization block, derived from the payload's raw tool
 * results: chart OR table for SQL rows, a strip for graph results, and
 * FIR chips for semantic matches.
 */
function VizBlock({ msg, onOpenNetwork }) {
  const raw = msg.payload?.data?.raw;
  if (!Array.isArray(raw) || raw.length === 0) return null;

  const hint = msg.hint ?? msg.payload?.visualization_hint ?? null;

  // Hotspot results are shaped like SQL rows and render the same way.
  const dataItem = raw.find(
    (it) => Array.isArray(it?.data) && it.data.length > 0 && it.data[0] && typeof it.data[0] === 'object',
  ) || raw.find(
    (it) => Array.isArray(it?.hotspots) && it.hotspots.length > 0 && typeof it.hotspots[0] === 'object',
  );
  const rows = dataItem ? (dataItem.data || dataItem.hotspots) : null;
  const graphItem = raw.find(
    (it) => it?.graph && Array.isArray(it.graph.nodes) && Array.isArray(it.graph.edges),
  );
  const firs = raw.find((it) => Array.isArray(it?.similar_firs) && it.similar_firs.length > 0)?.similar_firs;

  let chartEl = null;
  let tableRows = null;
  if (rows) {
    const row0 = rows[0];
    if (hint === 'chart') {
      if ('period' in row0 && 'count' in row0) {
        chartEl = <TrendMiniChart rows={rows} />;
      } else {
        const catKey = ['district', 'station_name', 'section'].find((k) => k in row0);
        const valueKey = catKey
          ? Object.keys(row0).find((k) => k !== catKey && typeof row0[k] === 'number')
          : null;
        if (catKey && valueKey) chartEl = <BarMiniChart rows={rows} catKey={catKey} valueKey={valueKey} />;
      }
    }
    if (!chartEl) tableRows = rows;
  }

  if (!chartEl && !tableRows && !graphItem && !firs) return null;

  return (
    <div className="viz-stack">
      {chartEl && <div className="panel viz-chart">{chartEl}</div>}
      {tableRows && <div className="panel viz-table-wrap"><VizTable rows={tableRows} /></div>}
      {graphItem && (
        <div className="panel viz-graph-strip">
          <Waypoints size={15} />
          <span className="grow">
            Network retrieved — <span className="num">{graphItem.graph.nodes.length}</span> entities
            {' · '}<span className="num">{graphItem.graph.edges.length}</span> links
          </span>
          <button type="button" className="btn" onClick={onOpenNetwork}>Open in Network Explorer</button>
        </div>
      )}
      {firs && (
        <div className="fir-row">
          {firs.slice(0, 4).map((f, i) => {
            const label = typeof f === 'string' ? f : f?.fir_number || f?.fir_id || `MATCH ${i + 1}`;
            return <span key={`${label}-${i}`} className="chip fir-chip">{label}</span>;
          })}
        </div>
      )}
    </div>
  );
}

/* ---------------- Message renderers ---------------- */

function AssistantMessage({ msg, onOpenNetwork }) {
  const streaming = msg.status === 'streaming';
  return (
    <div className="copilot-msg assistant">
      <div className="msg-avatar"><BrainCircuit size={14} /></div>
      <div className="msg-content">
        {typeof msg.intent === 'string' && msg.intent !== '' && (
          <div className="msg-meta">
            <span className="chip">Intent · {msg.intent.toUpperCase().replace(/_/g, ' ')}</span>
          </div>
        )}

        {msg.text ? (
          <div className={`markdown-body${streaming ? ' streaming' : ''}`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
            {streaming && <span className="stream-caret">▍</span>}
          </div>
        ) : streaming ? (
          <div className="msg-waiting">
            <div className="typing-dots"><span /><span /><span /></div>
            {msg.statusLine && <div className="status-line mono">{msg.statusLine}</div>}
          </div>
        ) : null}

        {msg.status === 'error' && (
          <div className="msg-error">{msg.error || 'The copilot could not answer this question.'}</div>
        )}

        {msg.status === 'done' && <VizBlock msg={msg} onOpenNetwork={onOpenNetwork} />}

        {msg.status === 'done' && Array.isArray(msg.sources) && msg.sources.length > 0 && (
          <div className="sources-row">
            <span className="sources-caption mono">Sources</span>
            {msg.sources.map((s, i) => (
              <span key={`${s}-${i}`} className="chip source-chip"><FileText size={11} />{s}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------------- Page ---------------- */

const CopilotChat = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [suggestions, setSuggestions] = useState(null); // null = loading, [] = hide

  const transcriptRef = useRef(null);
  const closeRef = useRef(null);
  const idRef = useRef(0);

  // Load suggestion prompts once; hide the section entirely on error.
  useEffect(() => {
    let alive = true;
    fetchSuggestions()
      .then((s) => { if (alive) setSuggestions(Array.isArray(s) ? s : []); })
      .catch(() => { if (alive) setSuggestions([]); });
    return () => { alive = false; };
  }, []);

  // Close any open SSE stream on unmount (StrictMode-safe: closeRef is
  // only populated by user-initiated sends, never by mount effects).
  useEffect(() => () => {
    if (closeRef.current) {
      closeRef.current();
      closeRef.current = null;
    }
  }, []);

  // Pin the transcript to the bottom on every message update.
  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const patch = (id, fn) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));
  };

  const send = (rawText) => {
    const question = String(rawText || '').trim();
    if (!question || streaming) return;

    // Defensive: never leave a previous stream open.
    if (closeRef.current) {
      closeRef.current();
      closeRef.current = null;
    }

    idRef.current += 1;
    const userId = idRef.current;
    idRef.current += 1;
    const asstId = idRef.current;

    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', text: question },
      {
        id: asstId, role: 'assistant', text: '', intent: null, status: 'streaming',
        hint: null, payload: null, sources: null, statusLine: 'Gathering information…', error: null,
      },
    ]);
    setInput('');
    setStreaming(true);

    let gotText = false;
    let finished = false;

    const onEvent = (frame) => {
      if (finished) return;
      switch (frame.event) {
        case 'intent':
          patch(asstId, (m) => ({ ...m, intent: frame.intent || m.intent }));
          break;
        case 'searching':
          patch(asstId, (m) => ({ ...m, statusLine: frame.message || m.statusLine }));
          break;
        case 'data_ready':
          patch(asstId, (m) => ({ ...m, hint: frame.hint ?? m.hint, statusLine: 'Data ready — composing answer…' }));
          break;
        case 'response':
          if (typeof frame.text === 'string' && frame.text !== '') {
            gotText = true;
            patch(asstId, (m) => ({ ...m, text: m.text + frame.text }));
          }
          break;
        case 'sources':
          if (Array.isArray(frame.sources)) patch(asstId, (m) => ({ ...m, sources: frame.sources }));
          break;
        case 'payload':
          if (frame.data) {
            patch(asstId, (m) => ({
              ...m,
              payload: frame.data,
              sources: m.sources ?? (Array.isArray(frame.data.sources) ? frame.data.sources : null),
              hint: m.hint ?? frame.data.visualization_hint ?? null,
            }));
          }
          break;
        case 'done':
          finished = true;
          closeRef.current = null;
          patch(asstId, (m) => ({ ...m, status: 'done', text: m.text || m.payload?.answer || '' }));
          setStreaming(false);
          break;
        default:
          break;
      }
    };

    const onError = (err) => {
      if (finished) return;
      finished = true;
      closeRef.current = null;

      if (gotText) {
        // Partial answer already on screen — close it out gracefully.
        patch(asstId, (m) => ({ ...m, status: 'done', text: m.text || m.payload?.answer || '' }));
        setStreaming(false);
        return;
      }

      // Nothing rendered yet — fall back to the non-streaming endpoint.
      copilotQuery(question)
        .then((res) => {
          patch(asstId, (m) => ({
            ...m,
            status: 'done',
            text: res?.answer || '',
            sources: Array.isArray(res?.sources) ? res.sources : m.sources,
            hint: res?.visualization_hint ?? m.hint,
            payload: res || m.payload,
          }));
        })
        .catch((fallbackErr) => {
          patch(asstId, (m) => ({ ...m, status: 'error', error: fallbackErr?.message || err?.message }));
        })
        .finally(() => setStreaming(false));
    };

    closeRef.current = streamCopilot(question, onEvent, onError);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    send(input);
  };

  return (
    <div className="copilot">
      {/* -------- Header strip -------- */}
      <header className="copilot-head">
        <div className="copilot-head-left">
          <div className="copilot-mark"><BrainCircuit size={17} /></div>
          <div>
            <div className="copilot-title">DRISHTI Copilot</div>
            <div className="copilot-subtitle mono">LANGGRAPH AGENT · LIVE SCRB DATA</div>
          </div>
        </div>
        {streaming
          ? <span className="chip chip-accent"><span className="spinner spinner-xs" />Analysing</span>
          : <span className="chip">Ready</span>}
      </header>

      {/* -------- Transcript -------- */}
      <div className="copilot-transcript" ref={transcriptRef}>
        <div className="transcript-inner">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-mark"><BrainCircuit size={26} /></div>
              <h2 className="welcome-title">Ask the state&rsquo;s crime data anything.</h2>
              <p className="welcome-sub">
                Natural-language questions over live FIR records — trends, hotspots,
                criminal networks and semantic case matching.
              </p>
              {suggestions === null ? (
                <div className="suggest-grid" aria-hidden="true">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="skeleton" style={{ height: 48 }} />
                  ))}
                </div>
              ) : suggestions.length > 0 ? (
                <div className="suggest-grid">
                  {suggestions.slice(0, 6).map((s, i) => {
                    const Icon = SUGGESTION_ICONS[s.icon] || FileText;
                    return (
                      <button key={`${s.text}-${i}`} type="button" className="panel suggest-card" onClick={() => send(s.text)}>
                        <Icon size={15} />
                        <span>{s.text}</span>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          ) : (
            messages.map((msg) => (
              msg.role === 'user' ? (
                <div key={msg.id} className="copilot-msg user">
                  <div className="user-bubble">{msg.text}</div>
                </div>
              ) : (
                <AssistantMessage key={msg.id} msg={msg} onOpenNetwork={() => navigate('/network')} />
              )
            ))
          )}
        </div>
      </div>

      {/* -------- Composer -------- */}
      <div className="copilot-composer">
        <div className="composer-inner">
          <form className="composer-form" onSubmit={handleSubmit}>
            <input
              className="input grow composer-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about trends, hotspots, networks, or describe a case…"
              aria-label="Ask the DRISHTI copilot"
            />
            <button
              type="submit"
              className="btn btn-accent composer-send"
              disabled={!input.trim() || streaming}
              aria-label="Send question"
            >
              <Send size={17} />
            </button>
          </form>
          <div className="composer-hint mono">
            DRISHTI can query live FIR data, trace networks and run semantic case matching.
          </div>
        </div>
      </div>
    </div>
  );
};

export default CopilotChat;
