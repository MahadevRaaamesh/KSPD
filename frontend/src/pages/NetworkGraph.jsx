import React, { useEffect, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import { Search, User } from 'lucide-react';
import { fetchNetworkGraph, fetchAccusedList } from '../services/api';
import './NetworkGraph.css';

const NetworkGraph = () => {
  const [elements, setElements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [accusedList, setAccusedList] = useState([]);
  const [filteredAccused, setFilteredAccused] = useState([]);
  const [selectedPerson, setSelectedPerson] = useState(null);

  useEffect(() => {
    const loadAccused = async () => {
      const list = await fetchAccusedList(50);
      setAccusedList(list);
      setFilteredAccused(list);
      if (list && list.length > 0) {
        handleSelectPerson(list[0].name);
      }
    };
    loadAccused();
  }, []);

  useEffect(() => {
    if (!searchTerm) {
      setFilteredAccused(accusedList);
    } else {
      setFilteredAccused(
        accusedList.filter(a => a.name.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }
  }, [searchTerm, accusedList]);

  const loadGraph = async (name) => {
    setLoading(true);
    try {
      const data = await fetchNetworkGraph(name);
      
      const cyElements = [];
      if (data.nodes) {
        data.nodes.forEach(n => {
          cyElements.push({
            data: { id: n.id, label: n.label, type: n.type }
          });
        });
      }
      if (data.edges) {
        data.edges.forEach(e => {
          cyElements.push({
            data: { source: e.source, target: e.target, label: e.relationship }
          });
        });
      }
      setElements(cyElements);
    } catch(e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleSelectPerson = (name) => {
    setSelectedPerson(name);
    loadGraph(name);
  };

  const layout = {
    name: 'cose',
    idealEdgeLength: 100,
    nodeOverlap: 20,
    refresh: 20,
    fit: true,
    padding: 30,
    randomize: false,
    componentSpacing: 100,
    nodeRepulsion: 400000,
    edgeElasticity: 100,
    nestingFactor: 5,
  };

  const stylesheet = [
    {
      selector: 'node',
      style: {
        'background-color': '#3b82f6',
        'label': 'data(label)',
        'color': '#fff',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': '12px',
        'font-size': '12px',
        'font-family': 'Inter, sans-serif',
        'text-background-color': 'rgba(17, 24, 39, 0.8)',
        'text-background-opacity': 1,
        'text-background-padding': '4px',
        'text-background-shape': 'roundrectangle'
      }
    },
    {
      selector: 'node[type = "Accused"]',
      style: { 'background-color': '#ef4444', 'width': 40, 'height': 40 }
    },
    {
      selector: 'node[type = "Case"]',
      style: { 'background-color': '#8b5cf6', 'shape': 'round-rectangle', 'width': 50, 'height': 30 }
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': 'rgba(255, 255, 255, 0.2)',
        'target-arrow-color': 'rgba(255, 255, 255, 0.2)',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'label': 'data(label)',
        'font-size': '10px',
        'color': '#9ca3af',
        'text-rotation': 'autorotate',
        'text-margin-y': '-10px'
      }
    }
  ];

  return (
    <div className="graph-container animate-fade-in">
      <header className="dashboard-header">
        <h1 className="text-gradient">Criminal Network Graph</h1>
        <p>Explore connections between accused individuals and cases</p>
      </header>
      
      <div className="graph-split-layout">
        
        {/* Left Pane: Data Table */}
        <div className="graph-table-pane glass-card">
          <div className="table-search-box">
             <Search size={16} className="search-icon" />
             <input 
               type="text" 
               placeholder="Filter accused by name..." 
               value={searchTerm}
               onChange={(e) => setSearchTerm(e.target.value)}
               className="table-search-input"
             />
          </div>
          
          <div className="accused-list">
            {filteredAccused.map(person => (
              <div 
                key={person.ROWID} 
                className={`accused-row ${selectedPerson === person.name ? 'active' : ''}`}
                onClick={() => handleSelectPerson(person.name)}
              >
                <div className="accused-icon"><User size={16} /></div>
                <div className="accused-details">
                  <div className="accused-name">{person.name}</div>
                  <div className="accused-meta">
                    {person.age ? `${person.age} yrs` : 'Unknown age'} • {person.gender || 'Unknown gender'}
                  </div>
                </div>
              </div>
            ))}
            {filteredAccused.length === 0 && (
              <div className="no-results">No accused found.</div>
            )}
          </div>
        </div>

        {/* Right Pane: Graph Canvas */}
        <div className="graph-canvas-wrapper glass-card">
          {loading && <div className="loading-badge">Generating Graph Topology...</div>}
          <CytoscapeComponent 
            elements={elements} 
            style={{ width: '100%', height: '100%' }}
            layout={layout}
            stylesheet={stylesheet}
            minZoom={0.5}
            maxZoom={3}
          />
        </div>

      </div>
    </div>
  );
};

export default NetworkGraph;
