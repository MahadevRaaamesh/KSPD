const API_BASE = 'http://localhost:8000/api';

export const fetchOverviewStats = async () => {
  try {
    const res = await fetch(`${API_BASE}/analytics/overview`);
    return await res.json();
  } catch (error) {
    console.error("Error fetching overview stats:", error);
    return null;
  }
};

export const fetchCrimeTrends = async () => {
  try {
    const res = await fetch(`${API_BASE}/analytics/trends`);
    return await res.json();
  } catch (error) {
    console.error("Error fetching trends:", error);
    return [];
  }
};

export const fetchDistrictStats = async () => {
  try {
    const res = await fetch(`${API_BASE}/analytics/districts`);
    return await res.json();
  } catch (error) {
    console.error("Error fetching district stats:", error);
    return [];
  }
};

export const fetchIPCStats = async () => {
  try {
    const res = await fetch(`${API_BASE}/analytics/ipc-sections`);
    return await res.json();
  } catch (error) {
    console.error("Error fetching IPC stats:", error);
    return [];
  }
};

export const fetchHeatmapData = async () => {
  try {
    const res = await fetch(`${API_BASE}/map/heatmap`);
    return await res.json();
  } catch (error) {
    console.error("Error fetching heatmap:", error);
    return [];
  }
};

export const fetchStationMarkers = async () => {
  try {
    const res = await fetch(`${API_BASE}/map/stations`);
    return await res.json();
  } catch (error) {
    console.error("Error fetching stations:", error);
    return [];
  }
};

export const fetchNetworkGraph = async (name = 'Kumar') => {
  try {
    const res = await fetch(`${API_BASE}/graph/network?name=${name}`);
    return await res.json();
  } catch (error) {
    console.error("Error fetching graph:", error);
    return { nodes: [], edges: [] };
  }
};

export const fetchAccusedList = async (limit = 100) => {
  try {
    const res = await fetch(`${API_BASE}/graph/accused?limit=${limit}`);
    return await res.json();
  } catch (error) {
    console.error("Error fetching accused list:", error);
    return [];
  }
};

export const sendCopilotQuery = async (question) => {
  try {
    const res = await fetch(`${API_BASE}/copilot/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
    return await res.json();
  } catch (error) {
    console.error("Error sending copilot query:", error);
    return { answer: "Sorry, I am currently offline." };
  }
};
