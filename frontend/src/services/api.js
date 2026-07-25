/* ============================================================
   DRISHTI API layer — hardened fetch client
   Every call: res.ok checked, params encoded, timeout guarded,
   typed ApiError on failure. No silent mock fallbacks.
   ============================================================ */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function buildUrl(path, params) {
  let url = API_BASE + path;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') qs.append(k, v);
    });
    const s = qs.toString();
    if (s) url += `?${s}`;
  }
  return url;
}

async function request(path, { method = 'GET', body, params, timeout = 20000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(buildUrl(path, params), {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    if (!res.ok) {
      let detail = `Request failed (${res.status})`;
      try {
        const data = await res.json();
        if (typeof data?.detail === 'string') detail = data.detail;
      } catch { /* non-JSON error body */ }
      throw new ApiError(detail, res.status);
    }
    return await res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err.name === 'AbortError') throw new ApiError('Request timed out — is the backend running?', 0);
    throw new ApiError('Cannot reach the DRISHTI backend. Start it on port 8000.', 0);
  } finally {
    clearTimeout(timer);
  }
}

/* ---------------- Session ---------------- */
const SESSION_KEY = 'drishti.session';

export function getSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}
export function setSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}
export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

/* ---------------- Auth ---------------- */
export const login = (badge_id, password) =>
  request('/auth/login', { method: 'POST', body: { badge_id, password } });

/* ---------------- Health ---------------- */
export const fetchHealth = () => request('/health');

/* ---------------- Analytics ---------------- */
export const fetchOverview = () => request('/analytics/overview');
export const fetchTrends = (params) => request('/analytics/trends', { params });
export const fetchDistricts = () => request('/analytics/districts');
export const fetchIpcSections = (limit = 10) => request('/analytics/ipc-sections', { params: { limit } });
export const fetchStations = (district) => request('/analytics/stations', { params: { district } });
export const fetchInsights = () => request('/analytics/insights');
export const fetchRiskScores = () => request('/analytics/risk-scores');
export const fetchTimePatterns = (district) => request('/analytics/time-patterns', { params: { district } });
export const fetchCategories = () => request('/analytics/categories');

/* ---------------- Map ---------------- */
export const fetchHeatmap = (params) => request('/map/heatmap', { params });
export const fetchClusters = (params) => request('/map/clusters', { params });
export const fetchMapStations = () => request('/map/stations');

/* ---------------- Graph ---------------- */
export const fetchCaseGraph = (firId) => request(`/graph/case/${encodeURIComponent(firId)}`);
export const fetchAccusedGraph = (accusedId) => request(`/graph/accused/${encodeURIComponent(accusedId)}`);
export const fetchNetworkByName = (name) => request('/graph/network', { params: { name } });
export const fetchAccusedList = (limit = 100) => request('/graph/accused', { params: { limit } });
export const fetchCoAccused = (accusedId) => request(`/graph/co-accused/${encodeURIComponent(accusedId)}`);
export const fetchRepeatOffenders = (limit = 20) => request('/graph/repeat-offenders', { params: { limit } });

/* ---------------- Similarity search ---------------- */
export const searchSimilar = (text, opts = {}) =>
  request('/search/similar', {
    method: 'POST',
    body: {
      text,
      top_k: opts.top_k ?? 8,
      district: opts.district ?? null,
      crime_category: opts.crime_category ?? null,
    },
  });
export const searchSimilarToFir = (firId, top_k = 8) =>
  request(`/search/similar/${encodeURIComponent(firId)}`, { params: { top_k } });
export const fetchFir = (firId) => request(`/search/fir/${encodeURIComponent(firId)}`);

/* ---------------- Copilot ---------------- */
export const copilotQuery = (question) =>
  request('/copilot/query', { method: 'POST', body: { question }, timeout: 45000 });
export const fetchSuggestions = () => request('/copilot/suggestions');

/**
 * Stream a copilot answer over SSE.
 * onEvent receives each parsed frame: {event: "intent"|"searching"|
 * "data_ready"|"response"|"sources"|"payload"|"done", ...fields}.
 * Returns a close() function; always call it on unmount.
 */
export function streamCopilot(question, onEvent, onError) {
  const es = new EventSource(buildUrl('/copilot/stream', { question }));
  es.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data);
      onEvent(data);
      if (data.event === 'done') es.close();
    } catch { /* skip malformed frame */ }
  };
  es.onerror = () => {
    es.close();
    if (onError) onError(new ApiError('Copilot stream disconnected.', 0));
  };
  return () => es.close();
}
