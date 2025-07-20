import React, { useState } from 'react';
import './Layout.style.scss';
import { Outlet } from 'react-router-dom';

const Layout = () => {
  const [activeSection, setActiveSection] = useState('home');

  const sections = [
   
    {
      id: 'profile',
      title: 'Profile',
      icon: '👤',
    },
    {
      id: 'job',
      title: 'Jobs',
      icon: '⚖️',
    }
  ];


  return (
    <div className="dashboard-container">
      {/* Navigation Sidebar */}
      <nav className="sidebar">
        <div className="sidebar-header">
          <h2 className="logo">MatchMind</h2>
        </div>
        
        <ul className="nav-menu">
          {sections.map((section) => (
            <li key={section.id} className="nav-item">
              <button
                className={`nav-link ${activeSection === section.id ? 'active' : ''}`}
                onClick={() => setActiveSection(section.id)}
              >
                <span className="nav-icon">{section.icon}</span>
                <span className="nav-text">{section.title}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <main className="main-content">
        <Outlet/>
      </main>
    </div>
  );
};

export default Layout;