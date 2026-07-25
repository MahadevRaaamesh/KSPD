import { useCallback, useEffect, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import { Eraser, Maximize2, Search, Waypoints, X } from 'lucide-react';
import { EmptyState, ErrorState, Skeleton } from '../components/ui';
import {
  fetchAccusedGraph, fetchCaseGraph, fetchNetworkByName, fetchRepeatOffenders,
} from '../services/api';
import './NetworkGraph.css';

/* Node styling per entity type — colors from the validated series palette,
   identity double-encoded via shape + the on-canvas legend. */
const NODE_STYLE = {
  Accused: { color: '#e66767', shape: 'ellipse', size: 34, label: 'Accused' },
  Case: { color: '#3987e5', shape: 'round-rectangle', size: 30, label: 'Case' },
  Victim: { color: '#d55181', shape: 'ellipse', size: 22, label: 'Victim' },
  PoliceStation: { color: '#c98500', shape: 'diamond', size: 26, label: 'Police Station' },
  CrimeCategory: { color: '#199e70', shape: 'hexagon', size: 24, label: 'Crime Category' },
  IPCSection: { color: '#9085e9', shape: 'round-tag', size: 20, label: 'IPC Section' },
};

const STYLESHEET = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      'font-size': 9.5,
      'font-family': '"Segoe UI", system-ui, sans-serif',
      color: '#a8b3c4',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 6,
      'text-wrap': 'ellipsis',
      'text-max-width': 92,
      'border-width': 2,
      'border-color': '#0a0e15',
    },
  },
  ...Object.entries(NODE_STYLE).map(([type, s]) => ({
    selector: `node[type = "${type}"]`,
    style: { 'background-color': s.color, shape: s.shape, width: s.size, height: s.size },
  })),
  {
    selector: 'node:selected',
    style: { 'border-width': 3, 'border-color': '#e6b345' },
  },
  {
    selector: 'edge',
    style: {
      width: 1.3,
      'line-color': 'rgba(148,163,184,0.35)',
      'curve-style': 'bezier',
      'target-arrow-shape': 'triangle',
      'target-arrow-color': 'rgba(148,163,184,0.35)',
      'arrow-scale': 0.7,
      label: 'data(relationship)',
      'font-size': 7,
      'font-family': '"Cascadia Mono", ui-monospace, Consolas, monospace',
      color: '#64748b',
      'text-rotation': 'autorotate',
      'text-background-color': '#0a0e15',
      'text-background-opacity': 0.85,
      'text-background-padding': 2,
    },
  },
];

const LAYOUT = {
  name: 'cose',
  animate: 'end',
  animationDuration: 500,
  // Networks are dense (a hub offender links every case he shares), so the
  // graph needs real breathing room or node labels collide into mush.
  padding: 90,
  nodeRepulsion: 42000,
  idealEdgeLength: 165,
  edgeElasticity: 120,
  nodeOverlap: 28,
  gravity: 55,
  componentSpacing: 180,
  randomize: false,
};

// Keep the auto-fit clear of the floating profile card (bottom-left) and the
// legend (top-left) so the graph never renders underneath them.
const FIT_PADDING = { top: 74, right: 70, bottom: 70, left: 70 };

/** Merge an API graph payload into an existing element list, deduped by id.
    Edges whose endpoints are absent from the merged node set are skipped. */
function mergeGraph(prev, graph) {
  const byId = new Map();
  const nodeIds = new Set();
  prev.forEach((el) => {
    byId.set(el.data.id, el);
    if (!el.data.source) nodeIds.add(el.data.id);
  });
  (graph?.nodes || []).forEach((n) => {
    if (!byId.has(n.id)) {
      byId.set(n.id, { data: { id: n.id, label: n.label, type: n.type, ...(n.properties || {}) } });
    }
    nodeIds.add(n.id);
  });
  (graph?.edges || []).forEach((e) => {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) return;
    const id = `${e.source}->${e.target}-${e.relationship}`;
    if (!byId.has(id)) {
      byId.set(id, { data: { id, source: e.source, target: e.target, relationship: e.relationship } });
    }
  });
  return [...byId.values()];
}

const NetworkGraph = () => {
  /* ---- Watchlist ---- */
  const [offenders, setOffenders] = useState([]);
  const [offendersLoading, setOffendersLoading] = useState(true);
  const [offendersError, setOffendersError] = useState(null);

  /* ---- Graph ---- */
  const [elements, setElements] = useState([]);
  const [profile, setProfile] = useState(null);
  const [query, setQuery] = useState('');
  const [noMatch, setNoMatch] = useState(false);
  const [tracing, setTracing] = useState(0); // in-flight graph fetch count
  const [graphError, setGraphError] = useState(null);

  const cyRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const loadOffenders = useCallback(() => {
    let alive = true;
    setOffendersLoading(true);
    setOffendersError(null);
    fetchRepeatOffenders(20)
      .then((list) => { if (alive) setOffenders(Array.isArray(list) ? list : []); })
      .catch((err) => { if (alive) setOffendersError(err.message); })
      .finally(() => { if (alive) setOffendersLoading(false); });
    return () => { alive = false; };
  }, []);

  useEffect(loadOffenders, [loadOffenders]);

  /** Run a graph fetch behind the TRACING LINKS pill, then apply the payload. */
  const runGraphFetch = useCallback(async (factory, apply) => {
    setGraphError(null);
    setTracing((t) => t + 1);
    try {
      const graph = await factory();
      if (mountedRef.current) apply(graph);
    } catch (err) {
      if (mountedRef.current) setGraphError(err.message);
    } finally {
      if (mountedRef.current) setTracing((t) => t - 1);
    }
  }, []);

  const openOffender = useCallback((offender) => {
    setProfile(offender);
    setNoMatch(false);
    runGraphFetch(
      () => fetchAccusedGraph(offender.any_accused_rowid),
      (graph) => setElements(mergeGraph([], graph)),
    );
  }, [runGraphFetch]);

  const runSearch = useCallback(() => {
    const name = query.trim();
    if (!name) return;
    setNoMatch(false);
    runGraphFetch(
      () => fetchNetworkByName(name),
      (graph) => {
        if (!graph?.nodes?.length) {
          setNoMatch(true);
          return;
        }
        setProfile(null);
        setElements(mergeGraph([], graph));
      },
    );
  }, [query, runGraphFetch]);

  /* Expand-on-tap: Case nodes pull the full case graph, Accused nodes pull
     their 2-hop co-accused network; both merge into the current elements. */
  const expandNode = useCallback((nodeId) => {
    if (nodeId.startsWith('fir_')) {
      const rowid = Number(nodeId.slice(4));
      if (Number.isFinite(rowid)) {
        runGraphFetch(
          () => fetchCaseGraph(rowid),
          (graph) => setElements((prev) => mergeGraph(prev, graph)),
        );
      }
    } else if (nodeId.startsWith('accused_')) {
      const rowid = Number(nodeId.slice(8));
      if (Number.isFinite(rowid)) {
        runGraphFetch(
          () => fetchAccusedGraph(rowid),
          (graph) => setElements((prev) => mergeGraph(prev, graph)),
        );
      }
    }
  }, [runGraphFetch]);

  const attachCy = useCallback((cy) => {
    if (cyRef.current === cy) return; // guard duplicate handler attachment
    cyRef.current = cy;
    cy.removeListener('tap');
    cy.on('tap', 'node', (evt) => expandNode(evt.target.id()));
  }, [expandNode]);

  // Re-run the force layout whenever the element set changes.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed() || elements.length === 0) return undefined;
    const layout = cy.layout(LAYOUT);
    // Centre and scale to the viewport once the force simulation settles.
    layout.one('layoutstop', () => {
      if (!cy.destroyed()) cy.animate({ fit: { padding: FIT_PADDING } }, { duration: 260 });
    });
    layout.run();
    return () => { if (!cy.destroyed()) layout.stop(); };
  }, [elements]);

  const fitView = useCallback(() => {
    const cy = cyRef.current;
    if (cy && !cy.destroyed()) cy.animate({ fit: { padding: FIT_PADDING } }, { duration: 260 });
  }, []);

  const clearAll = useCallback(() => {
    setElements([]);
    setProfile(null);
    setNoMatch(false);
    setGraphError(null);
  }, []);

  return (
    <div className="netx page-enter">
      {/* ================= Left rail ================= */}
      <aside className="netx-rail">
        <div className="netx-search">
          <div className="micro-label"><span className="tick" />Trace Subject</div>
          <div className="row">
            <input
              className="input grow"
              placeholder="Subject name…"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setNoMatch(false); }}
              onKeyDown={(e) => { if (e.key === 'Enter') runSearch(); }}
              aria-label="Trace subject by name"
            />
            <button
              type="button"
              className="btn btn-accent netx-search-btn"
              onClick={runSearch}
              disabled={!query.trim()}
              aria-label="Trace subject"
            >
              <Search size={14} />
            </button>
          </div>
          {noMatch && <div className="netx-search-note">No subject found</div>}
        </div>

        <div className="netx-list">
          <div className="micro-label"><span className="tick" />Repeat Offenders · Priority Watchlist</div>

          {offendersLoading && Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} h={78} />)}

          {!offendersLoading && offendersError && (
            <ErrorState message={offendersError} onRetry={loadOffenders} />
          )}

          {!offendersLoading && !offendersError && offenders.length === 0 && (
            <EmptyState title="No repeat offenders" sub="The priority watchlist is empty." />
          )}

          {!offendersLoading && !offendersError && offenders.map((o) => {
            const active = profile?.person_id === o.person_id;
            return (
              <button
                key={o.person_id}
                type="button"
                className={`offender-card${active ? ' active' : ''}`}
                onClick={() => openOffender(o)}
              >
                <div className="offender-head">
                  <span className="offender-name">{o.name}</span>
                  <span className="chip chip-critical">{o.case_count}× FIR</span>
                </div>
                <div className="offender-id mono">{o.person_id}</div>
                <div className="offender-line">{(o.districts || []).join(' · ') || '—'}</div>
                <div className="offender-line">MO: {(o.categories || []).slice(0, 2).join(', ') || '—'}</div>
              </button>
            );
          })}
        </div>
      </aside>

      {/* ================= Graph canvas ================= */}
      <div className="netx-canvas">
        <CytoscapeComponent
          elements={elements}
          stylesheet={STYLESHEET}
          layout={LAYOUT}
          cy={attachCy}
          minZoom={0.35}
          maxZoom={2.5}
          style={{ width: '100%', height: '100%' }}
        />

        {/* Legend */}
        <div className="panel netx-legend">
          {Object.entries(NODE_STYLE).map(([type, s]) => (
            <span key={type} className="legend-item">
              <span className="legend-dot" style={{ background: s.color }} />
              {s.label}
            </span>
          ))}
        </div>

        {/* View actions */}
        <div className="panel netx-actions">
          <button type="button" className="btn btn-ghost" onClick={fitView}>
            <Maximize2 size={13} />Fit
          </button>
          <button type="button" className="btn btn-ghost" onClick={clearAll}>
            <Eraser size={13} />Clear
          </button>
        </div>

        {/* In-flight trace pill */}
        {tracing > 0 && (
          <div className="trace-pill mono" role="status">
            <span className="spinner" />TRACING LINKS…
          </div>
        )}

        {/* Graph fetch failure */}
        {graphError && tracing === 0 && (
          <div className="netx-error-pill mono" role="alert">
            {graphError}
            <button
              type="button"
              className="netx-error-close"
              onClick={() => setGraphError(null)}
              aria-label="Dismiss error"
            >
              <X size={12} />
            </button>
          </div>
        )}

        {/* Subject profile */}
        {profile && (
          <div className="panel corner-ticks netx-profile">
            <button
              type="button"
              className="btn btn-ghost netx-profile-close"
              onClick={() => setProfile(null)}
              aria-label="Close subject profile"
            >
              <X size={14} />
            </button>
            <div className="micro-label"><span className="tick" />Subject Profile</div>
            <div className="netx-profile-name">{profile.name}</div>
            <div className="netx-profile-id mono">
              {profile.person_id}
              {profile.age != null && ` · ${profile.age} yrs`}
              {profile.gender && ` · ${profile.gender}`}
            </div>
            <div className="netx-profile-chips">
              <span className="chip chip-critical">{profile.case_count} FIRs</span>
              <span className="chip">{(profile.districts || []).length} districts</span>
            </div>
            <div className="micro-label netx-profile-mo"><span className="tick" />Modus Operandi</div>
            <div className="netx-profile-chips netx-mo-chips">
              {(profile.categories || []).map((c) => (
                <span key={c} className="chip chip-accent">{c}</span>
              ))}
            </div>
            <div className="netx-profile-active mono">
              ACTIVE {profile.first_seen} → {profile.last_seen}
            </div>
          </div>
        )}

        {/* Empty canvas */}
        {elements.length === 0 && (
          <div className="netx-empty">
            <EmptyState
              icon={Waypoints}
              title="Select a repeat offender or trace a subject"
              sub="Tap Case nodes to expand the network hop by hop."
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default NetworkGraph;
