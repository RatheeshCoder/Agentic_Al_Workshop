import React, { useState } from 'react';
import { submitStudentProfile } from '../../../service/Agent.service';
import './StudentProfile.scss'; // Import SCSS

const StudentProfile = () => {
  const [careerGoals, setCareerGoals] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const [linkedinProfile, setLinkedinProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    try {
      const formData = new FormData();
      formData.append('career_goals', careerGoals);
      if (resumeFile) formData.append('resume_file', resumeFile);
      if (linkedinProfile) formData.append('linkedin_profile', linkedinProfile);

      await submitStudentProfile(formData);
      setMessage('Student profile saved successfully!');
    } catch (error) {
      setMessage('Failed to save student data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="student-profile-container">
      <h2 className="title">Student Profile</h2>
      
      <form onSubmit={handleSubmit} className="profile-form">
        <div className="form-group">
          <label>Career Goals *</label>
          <textarea
            value={careerGoals}
            onChange={(e) => setCareerGoals(e.target.value)}
            rows="4"
            required
            placeholder="Describe your career goals and aspirations..."
          />
        </div>

        <div className="form-group">
          <label>Resume File</label>
          <input
            type="file"
            accept=".pdf,.txt,.docx"
            onChange={(e) => setResumeFile(e.target.files[0])}
          />
        </div>

        <div className="form-group">
          <label>LinkedIn Profile (Optional)</label>
          <input
            type="file"
            accept=".pdf,.txt,.docx"
            onChange={(e) => setLinkedinProfile(e.target.files[0])}
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Saving...' : 'Save Profile'}
        </button>
      </form>

      {message && (
        <div className={`message ${message.includes('successfully') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}
    </div>
  );
};

export default StudentProfile;
