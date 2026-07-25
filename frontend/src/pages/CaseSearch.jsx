import { useRef, useState } from 'react';
import {
  BrainCircuit, Database, GitCompare, ScanSearch, SearchX, Target, TriangleAlert,
} from 'lucide-react';
import { EmptyState, ErrorState, Skeleton } from '../components/ui';
import { searchSimilar, searchSimilarToFir } from '../services/api';
import './CaseSearch.css';

const DISTRICTS = [
  'Bengaluru City', 'Mysuru', 'Mangaluru', 'Hubballi-Dharwad', 'Belagavi',
  'Kalaburagi', 'Ballari', 'Shivamogga', 'Tumakuru', 'Davanagere',
  'Vijayapura', 'Udupi', 'Hassan', 'Ramanagara',
];

const CATEGORIES = [
  'Property Crimes', 'Crimes Against Body', 'Cyber Crimes', 'Crimes Against Women',
  'Narcotics', 'Economic Offences', 'Road Incidents', 'Public Order',
];

const EXAMPLES = [
  'chain snatching near bus stop at night',
  'OTP shared with caller, bank account emptied',
  'house broken into, gold ornaments stolen, white van seen',
];

const HOW_IT_WORKS = [
  { icon: BrainCircuit, step: '01', title: 'Embed', desc: '384-d sentence embeddings of every FIR narrative (all-MiniLM-L6-v2)' },
  { icon: Database, step: '02', title: 'Index', desc: 'FAISS inner-product index over the full state corpus' },
  { icon: Target, step: '03', title: 'Retrieve', desc: 'Cosine-ranked retrieval surfaces linked MOs across districts' },
];

const STATUS_CHIP = {
  'Under Investigation': 'chip-warning',
  'Charge Sheeted': 'chip-good',
};

const matchPct = (score) => Math.max(0, Math.min(100, Math.round(score * 100)));

const matchColor = (pct) => {
  if (pct >= 75) return '#4cc94c';
  if (pct >= 55) return 'var(--accent-bright)';
  return 'var(--ink-secondary)';
};

const fmtDate = (d) => String(d ?? '').slice(0, 10);

const CaseSearch = () => {
  const [query, setQuery] = useState('');
  const [district, setDistrict] = useState('');
  const [category, setCategory] = useState('');
  const [seedFir, setSeedFir] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Monotonic request id: stale responses (and StrictMode double-invokes) are ignored.
  const reqId = useRef(0);
  const lastRun = useRef(null);

  const runSearch = (fn) => {
    const id = ++reqId.current;
    lastRun.current = fn;
    setLoading(true);
    setError(null);
    fn()
      .then((res) => { if (id === reqId.current) setData(res); })
      .catch((err) => {
        if (id === reqId.current) { setData(null); setError(err.message); }
      })
      .finally(() => { if (id === reqId.current) setLoading(false); });
  };

  const runText = (text) => {
    const q = text.trim();
    if (!q || loading) return;
    setSeedFir(null);
    runSearch(() => searchSimilar(q, { district: district || null, crime_category: category || null }));
  };

  const onSubmit = (e) => {
    e.preventDefault();
    runText(query);
  };

  const applyExample = (q) => {
    if (loading) return;
    setQuery(q);
    runText(q);
  };

  const findSimilar = (fir) => {
    if (loading) return;
    setQuery(`FIR ${fir.fir_number}`);
    setSeedFir(fir.fir_number);
    runSearch(() => searchSimilarToFir(fir.ROWID, 8));
  };

  const retry = () => {
    if (lastRun.current) runSearch(lastRun.current);
  };

  const results = data?.results ?? [];
  const indexOffline = data != null && data.total_firs_indexed === 0;
  const hasSearched = loading || error != null || data != null;

  return (
    <div className="page-enter case-search">
      {/* ---- Hero search panel ---- */}
      <section className="panel corner-ticks cs-hero">
        <div className="micro-label"><span className="tick" />Semantic Case Retrieval · FAISS + MiniLM</div>
        <h1 className="cs-hero-title">Describe the incident</h1>
        <p className="cs-hero-sub">Natural-language search across every FIR narrative — matches meaning, not keywords.</p>

        <form className="cs-search-row" onSubmit={onSubmit}>
          <div className="cs-input-wrap">
            <ScanSearch size={17} />
            <input
              className="input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. two men on a motorcycle snatched a gold chain near the market"
              aria-label="Incident description"
            />
          </div>
          <select className="select" value={district} onChange={(e) => setDistrict(e.target.value)} aria-label="District filter">
            <option value="">All districts</option>
            {DISTRICTS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <select className="select" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category filter">
            <option value="">All categories</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <button type="submit" className="btn btn-accent cs-submit" disabled={loading || !query.trim()}>
            {loading && <span className="spinner" />}
            Match Cases
          </button>
        </form>

        <div className="cs-examples">
          <span className="cs-examples-label mono">Try</span>
          {EXAMPLES.map((q) => (
            <button key={q} type="button" className="cs-example" disabled={loading} onClick={() => applyExample(q)}>
              {q}
            </button>
          ))}
        </div>
      </section>

      {/* ---- Loading ---- */}
      {loading && (
        <div className="cs-results" aria-busy="true">
          {[0, 1, 2].map((i) => <Skeleton key={i} h={120} />)}
        </div>
      )}

      {/* ---- Error ---- */}
      {!loading && error && (
        <div className="panel">
          <ErrorState message={error} onRetry={retry} />
        </div>
      )}

      {/* ---- Vector index offline ---- */}
      {!loading && !error && indexOffline && (
        <div className="cs-index-warning" role="alert">
          <TriangleAlert size={16} />
          <span>
            Vector index offline — run <span className="mono">backend/scripts/build_embeddings.py</span> to enable semantic search.
          </span>
        </div>
      )}

      {/* ---- Results ---- */}
      {!loading && !error && data && !indexOffline && (
        <>
          <div className="cs-meta mono">
            {seedFir && (
              <span className="chip chip-accent"><GitCompare size={11} />Similar to FIR {seedFir}</span>
            )}
            <span>
              {results.length} match{results.length === 1 ? '' : 'es'} · ranked by cosine similarity
              · {Number(data.total_firs_indexed).toLocaleString('en-IN')} FIRs indexed
            </span>
          </div>

          {results.length === 0 ? (
            <div className="panel">
              <EmptyState
                icon={SearchX}
                title="No semantically similar cases"
                sub="Try a longer description of the incident."
              />
            </div>
          ) : (
            <div className="cs-results">
              {results.map(({ fir, similarity_score }) => {
                const pct = matchPct(similarity_score);
                const statusCls = STATUS_CHIP[fir.status];
                return (
                  <article className="panel cs-card" key={fir.ROWID}>
                    <div className="cs-match">
                      <span className="num cs-match-pct" style={{ color: matchColor(pct) }}>{pct}%</span>
                      <span className="cs-match-cap">Match</span>
                      <div className="cs-match-track">
                        <div className="cs-match-fill" style={{ width: `${pct}%` }} />
                      </div>
                    </div>

                    <div className="cs-card-main">
                      <div className="cs-card-top">
                        <span className="chip chip-accent">{fir.fir_number}</span>
                        <span className={statusCls ? `chip ${statusCls}` : 'chip'}>{fir.status}</span>
                        <span className="num cs-card-date">{fmtDate(fir.date_reported)}</span>
                      </div>
                      <div className="cs-card-title">{fir.crime_minor_head} — {fir.crime_major_head}</div>
                      <p className="cs-card-facts">{fir.brief_facts}</p>
                      <div className="cs-card-meta">
                        {fir.district} · {fir.police_station}
                        {fir.ipc_sections?.length ? ` · IPC ${fir.ipc_sections.join(', ')}` : ''}
                      </div>
                    </div>

                    <div className="cs-card-actions">
                      <button type="button" className="btn btn-ghost" disabled={loading} onClick={() => findSimilar(fir)}>
                        <GitCompare size={14} /> Find similar
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* ---- Pre-search: how it works ---- */}
      {!hasSearched && (
        <section className="cs-how" aria-label="How semantic search works">
          <div className="micro-label cs-how-label"><span className="tick" />How It Works · Retrieval Pipeline</div>
          <div className="cs-how-grid">
            {HOW_IT_WORKS.map(({ icon: Icon, step, title, desc }) => (
              <div className="panel cs-how-card" key={step}>
                <div className="cs-how-icon"><Icon size={17} /></div>
                <div>
                  <div className="cs-how-title mono">{step} · {title}</div>
                  <div className="cs-how-desc">{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default CaseSearch;
