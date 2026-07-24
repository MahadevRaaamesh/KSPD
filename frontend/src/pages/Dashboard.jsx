import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Shield, Users, Activity, CheckCircle, AlertTriangle, FileText } from 'lucide-react';
import StatCard from '../components/StatCard';
import { fetchOverviewStats, fetchCrimeTrends, fetchDistrictStats, fetchIPCStats } from '../services/api';
import './Dashboard.css';

const Dashboard = () => {
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [ipc, setIpc] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [oData, tData, dData, iData] = await Promise.all([
          fetchOverviewStats(),
          fetchCrimeTrends(),
          fetchDistrictStats(),
          fetchIPCStats()
        ]);
        
        if (oData) {
          setOverview(oData);
          setTrends(tData || []);
          setDistricts(dData || []);
          setIpc(iData || []);
        } else {
          throw new Error("No data returned");
        }
      } catch (e) {
        console.warn("API offline or error, falling back to mock UI data for demo.");
        // Fallback for visual demo if backend is offline
        setOverview({ total_firs: 1245, total_accused: 890, cases_pending: 345, cases_solved: 900 });
        setTrends([
          {period: '2023-01', count: 120}, {period: '2023-02', count: 150},
          {period: '2023-03', count: 110}, {period: '2023-04', count: 180},
          {period: '2023-05', count: 130}, {period: '2023-06', count: 210}
        ]);
        setDistricts([
          {district: 'Bengaluru Urban', total_cases: 500},
          {district: 'Mysuru', total_cases: 320},
          {district: 'Hubballi', total_cases: 280},
          {district: 'Mangaluru', total_cases: 145}
        ]);
        setIpc([{section: '379', count: 200}, {section: '420', count: 150}]);
      }
      setLoading(false);
    };
    loadData();
  }, []);

  if (loading) return <div className="loading">Loading Analytics...</div>;

  const trendOption = {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(17, 24, 39, 0.9)', textStyle: { color: '#fff' } },
    xAxis: { type: 'category', data: trends.map(t => t.period), axisLabel: { color: '#9ca3af' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }, axisLabel: { color: '#9ca3af' } },
    series: [{ 
      data: trends.map(t => t.count), 
      type: 'line', 
      smooth: true, 
      areaStyle: { opacity: 0.2 }, 
      itemStyle: { color: '#3b82f6' },
      lineStyle: { width: 3 }
    }]
  };

  const districtOption = {
    tooltip: { trigger: 'item', backgroundColor: 'rgba(17, 24, 39, 0.9)', textStyle: { color: '#fff' } },
    xAxis: { type: 'category', data: districts.slice(0, 5).map(d => d.district), axisLabel: { color: '#9ca3af', rotate: 30 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }, axisLabel: { color: '#9ca3af' } },
    series: [{ 
      data: districts.slice(0, 5).map(d => d.total_cases), 
      type: 'bar', 
      itemStyle: { borderRadius: [4, 4, 0, 0], color: '#8b5cf6' },
      barWidth: '40%'
    }]
  };

  return (
    <div className="dashboard-container animate-fade-in">
      <header className="dashboard-header">
        <h1 className="text-gradient">Statewide Analytics Dashboard</h1>
        <p>Real-time insights across all districts</p>
      </header>

      <div className="stats-grid">
        <StatCard title="Total FIRs" value={overview?.total_firs || 0} icon={FileText} type="primary" />
        <StatCard title="Accused Arrested" value={overview?.total_accused || 0} icon={Users} type="warning" />
        <StatCard title="Pending Investigation" value={overview?.cases_pending || 0} icon={Activity} type="danger" />
        <StatCard title="Cases Solved" value={overview?.cases_solved || 0} icon={CheckCircle} type="success" />
      </div>

      <div className="charts-grid">
        <div className="glass-card chart-container">
          <h3>Crime Trends (YTD)</h3>
          <ReactECharts option={trendOption} style={{ height: '300px' }} opts={{ renderer: 'svg' }} />
        </div>
        <div className="glass-card chart-container">
          <h3>Top Districts by Volume</h3>
          <ReactECharts option={districtOption} style={{ height: '300px' }} opts={{ renderer: 'svg' }} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
