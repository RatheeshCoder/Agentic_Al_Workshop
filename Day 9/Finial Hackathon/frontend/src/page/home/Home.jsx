import React from 'react'
import './Home.style.scss'
import logo from '../../assets/img/logo.png'
import HomeRight from '../../assets/img/homeRight.png'
import { useNavigate } from 'react-router-dom'

const Home = () => {
    const navigate = useNavigate()
    return (
        <section className="home-section">
            <header>
                <div className="left-logo">
                    <img src={logo} alt="MatchMind AI" />
                    <h1>MatchMind</h1>
                </div>

                <div className="right-btn">
                    <button class="btn"  onClick={() => navigate('/upload-data')}>
                        <svg height="24" width="24" fill="#FFFFFF" viewBox="0 0 24 24" data-name="Layer 1" id="Layer_1" class="sparkle">
                            <path d="M10,21.236,6.755,14.745.264,11.5,6.755,8.255,10,1.764l3.245,6.491L19.736,11.5l-6.491,3.245ZM18,21l1.5,3L21,21l3-1.5L21,18l-1.5-3L18,18l-3,1.5ZM19.333,4.667,20.5,7l1.167-2.333L24,3.5,21.667,2.333,20.5,0,19.333,2.333,17,3.5Z"></path>
                        </svg>

                        <span class="text">Try Now</span>
                    </button>
                </div>
            </header>


            <div className="main-container">
                <div className="left-container">
                    <div className="tag-content">
                        <h1>Best Tool</h1>
                    </div>

                    <div className="heading">
                        <h1>We Help Every Student Discover The Best Career Fit With <span> AI-Powered</span> Insights</h1>
                        <p>The fastest and smartest way to evaluate your career path, skill match, and cultural alignment — driven by AI and backed by data.</p>
                    </div>

                    <div className="CTA-container">
                            <div className="data-item">
                                <h2>500+</h2>
                                <p>Career paths analyzed with MatchMind AI</p>
                            </div>
                            <div className="data-item">
                                <h2>4.9⭐ </h2>
                                <p>Rating across trusted educational platforms</p>
                            </div>
                           
                    </div>
                </div>

                <div className="right-container">
                    <div className="image-container">
                        <img src={HomeRight } alt="Career Path" />
                    </div>
                </div>
            </div>
        </section>
    )
}

export default Home
