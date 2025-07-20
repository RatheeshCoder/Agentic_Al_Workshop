import React from 'react';
import './UserType.style.scss';
import { useNavigate } from 'react-router-dom';

const UserType = () => {
    const navigate = useNavigate();
  return (
    <section className="user-type-container">
      <h2 className="user-type-heading">Choose Your Role</h2>
      <div className="card-wrapper">
        <div onClick={() => navigate('/upload-data/student')} className="card">
          <div className="icon">
            🎓
          </div>
          <strong>Student</strong>
          <div className="card__body">Discover jobs and find your best career fit.</div>
          <span>Enter as Student</span>
        </div>

       <div onClick={() => navigate('/upload-data/company')} className="card">
          <div className="icon">
            🏢
          </div>
          <strong>Company</strong>
          <div className="card__body">Analyze candidate compatibility and recruit smart.</div>
          <span>Enter as Company</span>
        </div>
      </div>
    </section>
  );
};

export default UserType;