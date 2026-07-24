import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { fetchHeatmapData, fetchStationMarkers } from '../services/api';
import './CrimeMap.css';

const CrimeMap = () => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [77.5946, 12.9716],
      zoom: 11
    });

    map.current.on('load', async () => {
      try {
        const [heatmap, stations] = await Promise.all([
          fetchHeatmapData(),
          fetchStationMarkers()
        ]);
        
        const hData = heatmap?.length ? heatmap : [
          {longitude: 77.5946, latitude: 12.9716, intensity: 10},
          {longitude: 77.61, latitude: 12.95, intensity: 5}
        ];
        
        const heatmapGeojson = {
          type: 'FeatureCollection',
          features: hData.map(p => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [p.longitude, p.latitude] },
            properties: { mag: p.intensity || 1 }
          }))
        };

        map.current.addSource('crimes', {
          type: 'geojson',
          data: heatmapGeojson
        });

        map.current.addLayer({
          id: 'crimes-heat',
          type: 'heatmap',
          source: 'crimes',
          maxzoom: 15,
          paint: {
            'heatmap-weight': ['interpolate', ['linear'], ['get', 'mag'], 0, 0, 6, 1],
            'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 15, 3],
            'heatmap-color': [
              'interpolate', ['linear'], ['heatmap-density'],
              0, 'rgba(33,102,172,0)',
              0.2, 'rgb(103,169,207)',
              0.4, 'rgb(209,229,240)',
              0.6, 'rgb(253,219,199)',
              0.8, 'rgb(239,138,98)',
              1, 'rgb(178,24,43)'
            ],
            'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 2, 15, 20],
            'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 10, 1, 15, 0.5]
          }
        });
        
        if (stations?.length) {
            stations.forEach(st => {
                if (st.longitude && st.latitude) {
                    new maplibregl.Marker({ color: '#10b981' })
                        .setLngLat([st.longitude, st.latitude])
                        .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(`<h3>${st.station_name}</h3><p>Cases: ${st.case_count}</p>`))
                        .addTo(map.current);
                }
            });
        }
      } catch (e) {
        console.error("Map layer error:", e);
      }
      setLoading(false);
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  return (
    <div className="map-page-container animate-fade-in">
      <header className="dashboard-header" style={{ marginBottom: '1rem' }}>
        <h1 className="text-gradient">Crime Hotspot Map</h1>
        <p>Geospatial clustering and real-time station data</p>
      </header>
      <div className="map-glass-wrapper glass-card">
        {loading && <div className="loading-badge">Loading Layers...</div>}
        <div ref={mapContainer} className="map-container" />
      </div>
    </div>
  );
};

export default CrimeMap;
