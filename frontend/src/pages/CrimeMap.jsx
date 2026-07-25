import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
// maplibre-gl v6 is ESM-only with named exports — there is no default export.
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { ErrorState } from '../components/ui';
import { fetchClusters, fetchHeatmap, fetchMapStations } from '../services/api';
import './CrimeMap.css';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const STATE_CENTER = [76.3, 14.5];
const STATE_ZOOM = 6.3;
const DISTRICT_ZOOM = 9.5;

const SRC = { heat: 'heat-src', clusters: 'clusters-src', stations: 'stations-src' };
const LYR = { heat: 'heat-lyr', clusters: 'clusters-lyr', stations: 'stations-lyr' };

const EMPTY_FC = { type: 'FeatureCollection', features: [] };

const TOD_OPTIONS = [
  { v: '', label: 'ALL' },
  { v: 'night', label: 'NIGHT' },
  { v: 'morning', label: 'MORN' },
  { v: 'afternoon', label: 'AFTN' },
  { v: 'evening', label: 'EVE' },
];

const num = (v) => (v === null || v === undefined || v === '' ? NaN : Number(v));

/** Rows → GeoJSON FeatureCollection of points; drops rows without finite coords. */
function toFC(rows, pickProps) {
  return {
    type: 'FeatureCollection',
    features: (rows || [])
      .filter((r) => Number.isFinite(num(r.longitude)) && Number.isFinite(num(r.latitude)))
      .map((r) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [num(r.longitude), num(r.latitude)] },
        properties: pickProps(r),
      })),
  };
}

const ESC_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (ch) => ESC_MAP[ch]);

const countOf = (rows) => (rows === null ? '—' : rows.length.toLocaleString('en-IN'));

function LayerToggle({ checked, onChange, swatch, label }) {
  return (
    <label className="layer-toggle">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle-box" aria-hidden="true" />
      <span className={`swatch ${swatch}`} aria-hidden="true" />
      <span className="grow">{label}</span>
    </label>
  );
}

const CrimeMap = () => {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const popupRef = useRef(null);

  const [styleReady, setStyleReady] = useState(false);

  // Filters
  const [district, setDistrict] = useState('');
  const [category, setCategory] = useState('');
  const [tod, setTod] = useState('');

  // Layer visibility
  const [showHeat, setShowHeat] = useState(true);
  const [showClusters, setShowClusters] = useState(true);
  const [showStations, setShowStations] = useState(true);

  // Data (null = never loaded)
  const [heatPoints, setHeatPoints] = useState(null);
  const [clusters, setClusters] = useState(null);
  const [stations, setStations] = useState(null);
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);
  const [retryToken, setRetryToken] = useState(0);

  /* ---------------- Map bootstrap (once) ---------------- */
  useEffect(() => {
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: STATE_CENTER,
      zoom: STATE_ZOOM,
      maxZoom: 15,
      attributionControl: { compact: true },
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), 'top-right');

    let disposed = false;

    map.on('load', () => {
      if (disposed) return;

      map.addSource(SRC.heat, { type: 'geojson', data: EMPTY_FC });
      map.addSource(SRC.clusters, { type: 'geojson', data: EMPTY_FC });
      map.addSource(SRC.stations, { type: 'geojson', data: EMPTY_FC });

      map.addLayer({
        id: LYR.heat,
        type: 'heatmap',
        source: SRC.heat,
        paint: {
          'heatmap-weight': ['interpolate', ['linear'], ['get', 'intensity'], 0, 0, 5, 1],
          'heatmap-color': [
            'interpolate', ['linear'], ['heatmap-density'],
            0, 'rgba(13, 54, 107, 0)',
            0.15, '#0d366b',
            0.35, '#256abf',
            0.55, '#c98500',
            0.75, '#ec835a',
            1, '#d03b3b',
          ],
          'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 6, 14, 10, 26, 14, 44],
          'heatmap-opacity': 0.85,
        },
      });

      map.addLayer({
        id: LYR.clusters,
        type: 'circle',
        source: SRC.clusters,
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['get', 'count'], 1, 4, 10, 10, 40, 20],
          'circle-color': '#3987e5',
          'circle-opacity': 0.55,
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#0a0e15',
        },
      });

      map.addLayer({
        id: LYR.stations,
        type: 'circle',
        source: SRC.stations,
        paint: {
          'circle-radius': 4.5,
          'circle-color': '#e6b345',
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#0a0e15',
        },
      });

      const popup = new maplibregl.Popup({ closeButton: true, closeOnClick: true, offset: 10, maxWidth: '260px' });
      popupRef.current = popup;

      map.on('click', LYR.clusters, (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties;
        popup
          .setLngLat(f.geometry.coordinates)
          .setHTML(`<b>${p.count} incidents</b><br/>${esc(p.minor_head)} · ${esc(p.crime_category)}`)
          .addTo(map);
      });

      map.on('click', LYR.stations, (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties;
        popup
          .setLngLat(f.geometry.coordinates)
          .setHTML(
            `<b>${esc(p.station_name)}</b><br/><span style="color:#a8b3c4">${esc(p.district)} · ${p.case_count} cases</span>`,
          )
          .addTo(map);
      });

      [LYR.clusters, LYR.stations].forEach((id) => {
        map.on('mouseenter', id, () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', id, () => { map.getCanvas().style.cursor = ''; });
      });

      setStyleReady(true);
    });

    return () => {
      disposed = true;
      setStyleReady(false);
      if (popupRef.current) {
        popupRef.current.remove();
        popupRef.current = null;
      }
      mapRef.current = null;
      map.remove();
    };
  }, []);

  /* ---------------- Stations (once per retry) ---------------- */
  useEffect(() => {
    let alive = true;
    fetchMapStations()
      .then((rows) => { if (alive) setStations(Array.isArray(rows) ? rows : []); })
      .catch(() => { if (alive) setStations([]); });
    return () => { alive = false; };
  }, [retryToken]);

  /* ---------------- Heat + clusters (per filter change) ---------------- */
  useEffect(() => {
    let alive = true;
    setBusy(true);
    setError(null);
    Promise.all([
      fetchHeatmap({ district, crime_category: category, tod }),
      fetchClusters({ district, crime_category: category, tod }),
    ])
      .then(([h, c]) => {
        if (!alive) return;
        const clusterRows = Array.isArray(c) ? c : [];
        setHeatPoints(Array.isArray(h) ? h : []);
        setClusters(clusterRows);
        // Options accumulate across responses so a filtered fetch never shrinks the list
        setCategoryOptions((prev) => {
          const set = new Set(prev);
          clusterRows.forEach((row) => { if (row.crime_category) set.add(row.crime_category); });
          return [...set].sort();
        });
      })
      .catch((err) => { if (alive) setError(err.message); })
      .finally(() => { if (alive) setBusy(false); });
    return () => { alive = false; };
  }, [district, category, tod, retryToken]);

  /* ---------------- Apply data to live sources (no map reinit) ---------------- */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady || heatPoints === null) return;
    const src = map.getSource(SRC.heat);
    if (src) src.setData(toFC(heatPoints, (r) => ({ intensity: Number(r.intensity) || 0 })));
  }, [heatPoints, styleReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady || clusters === null) return;
    const src = map.getSource(SRC.clusters);
    if (src) {
      src.setData(toFC(clusters, (r) => ({
        count: Number(r.count) || 0,
        crime_category: r.crime_category,
        minor_head: r.minor_head,
      })));
    }
  }, [clusters, styleReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady || stations === null) return;
    const src = map.getSource(SRC.stations);
    if (src) {
      src.setData(toFC(stations, (r) => ({
        station_name: r.station_name,
        district: r.district,
        case_count: Number(r.case_count) || 0,
      })));
    }
  }, [stations, styleReady]);

  /* ---------------- Layer visibility ---------------- */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady || !map.getLayer(LYR.heat)) return;
    map.setLayoutProperty(LYR.heat, 'visibility', showHeat ? 'visible' : 'none');
    map.setLayoutProperty(LYR.clusters, 'visibility', showClusters ? 'visible' : 'none');
    map.setLayoutProperty(LYR.stations, 'visibility', showStations ? 'visible' : 'none');
  }, [showHeat, showClusters, showStations, styleReady]);

  /* ---------------- Handlers & derived ---------------- */
  const districtOptions = useMemo(() => {
    const set = new Set((stations || []).map((s) => s.district).filter(Boolean));
    return [...set].sort();
  }, [stations]);

  const handleDistrict = useCallback((value) => {
    setDistrict(value);
    const map = mapRef.current;
    if (!map) return;
    if (!value) {
      map.flyTo({ center: STATE_CENTER, zoom: STATE_ZOOM, duration: 1300 });
      return;
    }
    const pts = (stations || []).filter((s) => s.district === value);
    if (pts.length === 0) return;
    const lng = pts.reduce((sum, s) => sum + Number(s.longitude), 0) / pts.length;
    const lat = pts.reduce((sum, s) => sum + Number(s.latitude), 0) / pts.length;
    map.flyTo({ center: [lng, lat], zoom: DISTRICT_ZOOM, duration: 1300 });
  }, [stations]);

  const retry = useCallback(() => setRetryToken((t) => t + 1), []);

  const initialFail = Boolean(error) && heatPoints === null && clusters === null;
  const refetchError = Boolean(error) && !initialFail;
  const noMatches = !busy && !error && heatPoints !== null
    && heatPoints.length === 0 && (clusters?.length ?? 0) === 0;

  /* ---------------- Render ---------------- */
  return (
    <div className="map-page page-enter">
      <div ref={containerRef} className="map-canvas" aria-label="Karnataka crime density map" />

      {/* Floating layer-control panel */}
      <div className="map-panel panel corner-ticks">
        <div className="micro-label"><span className="tick" />Layer Control</div>

        <div className="map-filter-stack">
          <select
            className="select"
            value={district}
            onChange={(e) => handleDistrict(e.target.value)}
            aria-label="District filter"
          >
            <option value="">All districts</option>
            {districtOptions.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>

          <select
            className="select"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            aria-label="Crime category filter"
          >
            <option value="">All categories</option>
            {categoryOptions.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>

          <div className="tod-seg" role="group" aria-label="Time of day">
            {TOD_OPTIONS.map((t) => (
              <button
                key={t.label}
                type="button"
                className={`tod-btn${tod === t.v ? ' active' : ''}`}
                aria-pressed={tod === t.v}
                onClick={() => setTod(t.v)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="map-toggles">
          <LayerToggle checked={showHeat} onChange={setShowHeat} swatch="swatch-heat" label="Density heat" />
          <LayerToggle checked={showClusters} onChange={setShowClusters} swatch="swatch-cluster" label="Incident clusters" />
          <LayerToggle checked={showStations} onChange={setShowStations} swatch="swatch-station" label="Police stations" />
        </div>

        <div className={`map-readout mono${busy ? ' dimmed-refetch' : ''}`}>
          {busy && <span className="spinner" />}
          <span>{countOf(heatPoints)} pts · {countOf(clusters)} clusters · {countOf(stations)} PS</span>
        </div>
      </div>

      {/* Density legend */}
      <div className="map-legend panel">
        <div className="micro-label"><span className="tick" />Incident Density</div>
        <div className="legend-bar" aria-hidden="true" />
        <div className="legend-scale mono"><span>Low</span><span>High</span></div>
        <div className="legend-notes">
          <span className="legend-note"><span className="swatch swatch-cluster" aria-hidden="true" />Cluster — sized by count</span>
          <span className="legend-note"><span className="swatch swatch-station" aria-hidden="true" />Police station</span>
        </div>
      </div>

      {noMatches && <div className="map-float-chip chip">No incidents match filters</div>}
      {refetchError && <div className="map-float-chip chip chip-critical">{error}</div>}

      {initialFail && (
        <div className="map-error-overlay">
          <div className="panel corner-ticks map-error-card">
            <ErrorState message={error} onRetry={retry} />
          </div>
        </div>
      )}
    </div>
  );
};

export default CrimeMap;
