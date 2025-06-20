import React, { useEffect, useState, useRef } from 'react';
import { CheckCircle, XCircle, Download, FileText } from 'lucide-react';
import './Dashboard.style.scss';
import { useParams } from 'react-router-dom';
import { getFinialReport } from '../../service/Agent.service';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import { generateReportContent } from './generateReportContent';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeIndex, setActiveIndex] = useState(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const barChartRef = useRef(null);
  const doughnutChartRef = useRef(null);

  const { analysisId } = useParams();

  const fetchData = async () => {
    try {
      const response = await getFinialReport(analysisId);
      console.log('response :', response);
      setDashboardData(response.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [analysisId]);

 const generateReport = () => {
  if (!dashboardData) return;

  setIsGeneratingReport(true);

  const reportContent = generateReportContent(dashboardData, analysisId);

  const blob = new Blob([reportContent], { type: 'text/plain' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `Career_Compatibility_Report_${analysisId}_${new Date().toISOString().split('T')[0]}.txt`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);

  setTimeout(() => {
    setIsGeneratingReport(false);
  }, 1000);
};


  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading analysis...</p>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="dashboard-error">
        <p>Failed to load analysis data</p>
      </div>
    );
  }

  const {
    compatibility_score,
    skill_alignment,
    student_intents,
    counseling_report,
    input_data
  } = dashboardData;

  // Bar Chart Configuration for Compatibility Breakdown
  const compatibilityChartData = {
    labels: ['Overall\nScore', 'Intent\nAlignment', 'Skill\nMatch', 'Cultural\nFit'],
    datasets: [
      {
        label: 'Compatibility Score',
        data: [
          compatibility_score?.overall_score || 0,
          compatibility_score?.intent_alignment || 0,
          compatibility_score?.skill_match || 0,
          compatibility_score?.cultural_fit || 0
        ],
        backgroundColor: [
          'rgba(66, 133, 244, 0.8)',
          'rgba(158, 158, 158, 0.8)',
          'rgba(52, 168, 83, 0.8)',
          'rgba(52, 168, 83, 0.8)'
        ],
        borderColor: [
          'rgba(66, 133, 244, 1)',
          'rgba(158, 158, 158, 1)',
          'rgba(52, 168, 83, 1)',
          'rgba(52, 168, 83, 1)'
        ],
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }
    ]
  };

  const compatibilityChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        cornerRadius: 8,
        displayColors: false,
        callbacks: {
          title: (context) => {
            return context[0].label.replace('\n', ' ');
          },
          label: (context) => {
            return `Score: ${context.parsed.y}%`;
          }
        }
      }
    },
    scales: {
      x: {
        grid: {
          display: false
        },
        ticks: {
          color: '#666',
          font: {
            size: 12
          }
        }
      },
      y: {
        display: false,
        beginAtZero: true,
        max: 100
      }
    },
    animation: {
      duration: 1500
    },
    interaction: {
      intersect: false,
      mode: 'index'
    }
  };

  // Doughnut Chart Configuration for Industry Distribution
  const industryLabels = student_intents?.desired_industries || [];
  const industryColors = ['#8B5CF6', '#06B6D4', '#F97316', '#FACC15', '#34D399'];

  const industryChartData = {
    labels: industryLabels,
    datasets: [
      {
        data: industryLabels.map(() => Math.round(100 / industryLabels.length)),
        backgroundColor: industryColors.slice(0, industryLabels.length),
        borderColor: industryColors.slice(0, industryLabels.length).map(color => color + 'DD'),
        borderWidth: 2,
        hoverBackgroundColor: industryColors.slice(0, industryLabels.length).map(color => color + 'CC'),
        hoverBorderWidth: 3,
        hoverOffset: 10
      }
    ]
  };

  const industryChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        cornerRadius: 8,
        callbacks: {
          label: (context) => {
            return `${context.label}: ${context.parsed}%`;
          }
        }
      }
    },
    animation: {
      animateRotate: true,
      animateScale: true,
      duration: 2000
    },
    interaction: {
      intersect: false
    },
    cutout: '60%'
  };

  // Skills Bar Chart Configuration
  const skillsData = skill_alignment?.matched_skills || [];
  const skillsChartData = {
    labels: skillsData,
    datasets: [
      {
        label: 'Proficiency',
        data: skillsData.map(() => Math.floor(Math.random() * 51) + 50), // Generates values between 50 and 100
        backgroundColor: skillsData.map(
          (_, i) =>
            [
              'rgba(255, 107, 107, 0.8)',
              'rgba(66, 133, 244, 0.8)',
              'rgba(6, 182, 212, 0.8)'
            ][i % 3]
        ),
        borderColor: skillsData.map(
          (_, i) =>
            [
              'rgba(255, 107, 107, 1)',
              'rgba(66, 133, 244, 1)',
              'rgba(6, 182, 212, 1)'
            ][i % 3]
        ),
        borderWidth: 2,
        borderRadius: 6,
        borderSkipped: false,
      }
    ]
  };

  const skillsChartOptions = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        cornerRadius: 8,
        callbacks: {
          label: (context) => {
            return `Proficiency: ${context.parsed.x}%`;
          }
        }
      }
    },
    scales: {
      x: {
        beginAtZero: true,
        max: 100,
        grid: {
          color: 'rgba(0, 0, 0, 0.1)'
        },
        ticks: {
          color: '#666',
          callback: function (value) {
            return value + '%';
          }
        }
      },
      y: {
        grid: {
          display: false
        },
        ticks: {
          color: '#666',
          font: {
            size: 12
          }
        }
      }
    },
    animation: {
      duration: 1800
    },
    interaction: {
      intersect: false,
      mode: 'index'
    }
  };

  const toggleIndex = (index) => {
    setActiveIndex(activeIndex === index ? null : index);
  };

  return (
    <div className="dashboard">
      <div className="dashboard-container">
        {/* Header */}
        <div className="dashboard-header">
          <h1>Career Compatibility Dashboard</h1>
        </div>

        <div className="metrics-row">
          <div className="metric-card">
            <div className="metric-main">
              <h3>Overall Score</h3>
              <div className="score-large">{compatibility_score.overall_score}%</div>
            </div>
          </div>

          <div className="metric-card">
            <h3>Skill Match</h3>
            <div className="score-large">{compatibility_score.skill_match}%</div>
          </div>

          <div className="metric-card">
            <h3>Matched Skills</h3>
            <div className="score-large">{skill_alignment.matched_skills.length}</div>
          </div>
        </div>

        <div className="Compatibility-container">
          <div className="chart-card">
            <h3>Compatibility Breakdown</h3>
            <div className="chart-container" style={{ height: '400px' }}>
              <Bar
                ref={barChartRef}
                data={compatibilityChartData}
                options={compatibilityChartOptions}
              />
            </div>
          </div>
        </div>

        <div className="middle-charts-row">
          <div className="Hidden-card">
            <div className="chart-left">
              <h3>Industry</h3>
              <p className="metric-subtitle">Distribution</p>
              <div className="legend-items">
                {industryLabels.map((label, index) => (
                  <div className="legend-item" key={index}>
                    <span
                      className="legend-dot"
                      style={{ backgroundColor: industryColors[index % industryColors.length] }}
                    ></span>
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="chart-right" style={{ width: '150px', height: '150px' }}>
              <Doughnut
                ref={doughnutChartRef}
                data={industryChartData}
                options={industryChartOptions}
              />
            </div>
          </div>

          <div className="culture-card">
            <h3>Company</h3>
            <p className="culture-subtitle">Culture Match</p>
            <div className="culture-items">
              <div className="culture-item">
                <CheckCircle size={16} className="check-icon" />
                <span>Collaborative Environment</span>
              </div>
              <div className="culture-item">
                <CheckCircle size={16} className="check-icon" />
                <span>Innovation Focus</span>
              </div>
              <div className="culture-item">
                <XCircle size={16} className="x-icon" />
                <span>Remote Work Options</span>
              </div>
              <div className="culture-item">
                <XCircle size={16} className="x-icon" />
                <span>Learning Support</span>
              </div>
            </div>
          </div>
        </div>

        <div className="skills-goals-row">
          <div className="skills-card">
            <h3>Current Skills Proficiency</h3>
            <div className="skills-chart" style={{ height: '300px' }}>
              <Bar data={skillsChartData} options={skillsChartOptions} />
            </div>
          </div>

          <div className="goals-card">
            <h3>Learning Goals Progress</h3>
            <div className="goals-list">
              {student_intents.learning_goals.map((goal, index) => {
                const randomPercentage = Math.floor(Math.random() * 41) + 60; // Random between 60–100
                return (
                  <div key={index} className="goal-item">
                    <div className="goal-header">
                      <span className="goal-name">{goal}</span>
                      <span className="goal-percentage">{`${randomPercentage}%`}</span>
                    </div>
                    <div className="goal-bar">
                      <div
                        className="goal-progress"
                        style={{ width: `${randomPercentage}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <footer>
          <div className="stepper-box">
            {counseling_report.actionable_advice.map((advice, index) => {
              const [title, description] = advice.split(' - ');
              // Determine priority from title (assuming last word is the level, or customize as needed)
              let priority = 'Low';
              if (title.toLowerCase().includes('high')) {
                priority = 'High';
              } else if (title.toLowerCase().includes('medium')) {
                priority = 'Medium';
              }

              // Assign class based on priority
              const statusClass = {
                High: 'stepper-completed',
                Medium: 'stepper-active',
                Low: 'stepper-pending'
              }[priority];

              return (
                <div key={index} className={`stepper-step ${statusClass}`}>
                  <div className="stepper-circle">
                    {priority === 'High' ? (
                      <svg
                        viewBox="0 0 16 16"
                        className="bi bi-check-lg"
                        fill="currentColor"
                        height="16"
                        width="16"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path d="M12.736 3.97a.733.733 0 011.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 01-1.065.02L3.217 8.384a.757.757 0 010-1.06.733.733 0 011.047 0l3.052 3.093 5.4-6.425z" />
                      </svg>
                    ) : (
                      index + 1
                    )}
                  </div>

                  {index < counseling_report.actionable_advice.length - 1 && (
                    <div className="stepper-line"></div>
                  )}

                  <div className="stepper-content">
                    <div className="stepper-title">{title}</div>
                    <div className="stepper-status">{priority}</div>
                    <div className="stepper-time">Suggested on: June 20, 2025</div>
                    {description && <div className="stepper-desc">{description}</div>}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="right-column">
            <div className="career-goals-card">
              <h3>Career Goals</h3>
              <p>{input_data?.career_goals || 'No career goals provided.'}</p>
            </div>
          </div>
        </footer>
      </div>

      {/* Floating Download Button */}
      <button
        className="floating-download-btn"
        onClick={generateReport}
        disabled={isGeneratingReport}
        title="Download Full Report"
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: '#4285f4',
          color: 'white',
          border: 'none',
          cursor: isGeneratingReport ? 'not-allowed' : 'pointer',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '20px',
          transition: 'all 0.3s ease',
          zIndex: 1000,
          opacity: isGeneratingReport ? 0.7 : 1,
          transform: isGeneratingReport ? 'scale(0.95)' : 'scale(1)',
        }}
        onMouseEnter={(e) => {
          if (!isGeneratingReport) {
            e.target.style.backgroundColor = '#3367d6';
            e.target.style.transform = 'scale(1.05)';
            e.target.style.boxShadow = '0 6px 16px rgba(0, 0, 0, 0.2)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isGeneratingReport) {
            e.target.style.backgroundColor = '#4285f4';
            e.target.style.transform = 'scale(1)';
            e.target.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
          }
        }}
      >
        {isGeneratingReport ? (
          <div
            style={{
              width: '20px',
              height: '20px',
              border: '2px solid #ffffff',
              borderTop: '2px solid transparent',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}
          />
        ) : (
          <Download size={24} />
        )}
      </button>

      {/* Add keyframes for spinner animation */}
      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default Dashboard;