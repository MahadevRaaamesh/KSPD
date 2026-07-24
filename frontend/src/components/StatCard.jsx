import React from 'react';
import './StatCard.css';

const StatCard = ({ title, value, icon: Icon, type = 'default' }) => {
  return (
    <div className={`glass-card stat-card border-${type}`}>
      <div className="stat-icon-wrapper">
        <Icon size={24} className={`icon-${type}`} />
      </div>
      <div className="stat-content">
        <h3 className="stat-title">{title}</h3>
        <p className="stat-value text-gradient">{value}</p>
      </div>
    </div>
  );
};

export default StatCard;
