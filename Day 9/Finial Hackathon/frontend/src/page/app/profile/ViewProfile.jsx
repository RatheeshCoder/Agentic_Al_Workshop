import React, { useEffect, useState } from 'react';
import { getStudentProfile } from '../../../service/Agent.service';
import './StudentProfile.scss';

const ViewProfile = () => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getStudentProfile();
        console.log('Profile data:', data);
        setProfile(data);
      } catch (err) {
        console.error('Error fetching profile:', err);
        setError('Unable to load profile. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  const getFileName = (filePath) => {
    if (!filePath) return '';
    return filePath.split('\\').pop().split('/').pop();
  };

  const getFileExtension = (filePath) => {
    if (!filePath) return '';
    return filePath.split('.').pop()?.toLowerCase() || '';
  };

  const handleDownload = async (filePath, fileName) => {
    try {
      // Note: This won't work with local file paths like C:\Users\...
      // You'll need a backend endpoint to serve these files
      console.warn('Cannot download local file path:', filePath);
      alert('File download is not available for local file paths. Please contact support.');
    } catch (err) {
      console.error('Error downloading file:', err);
      alert('Error downloading file. Please try again.');
    }
  };

  const handleView = (filePath) => {
    try {
      // Note: This won't work with local file paths like C:\Users\...
      // You'll need a backend endpoint to serve these files
      console.warn('Cannot view local file path:', filePath);
      alert('File viewing is not available for local file paths. Please contact support.');
    } catch (err) {
      console.error('Error viewing file:', err);
      alert('Error viewing file. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">Loading profile...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">{error}</div>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="no-profile">
        <p>No profile data available.</p>
      </div>
    );
  }

  return (
    <div className="student-profile-container">
      <div className="profile-content">
        <h2>Student Profile</h2>
        
        {/* Profile Metadata */}
        <div className="profile-metadata">
          <div className="metadata-item">
            <strong>Profile ID:</strong>
            <span>{profile.id}</span>
          </div>
          <div className="metadata-item">
            <strong>User ID:</strong>
            <span>{profile.user_id}</span>
          </div>
          <div className="metadata-item">
            <strong>Created:</strong>
            <span>{formatDate(profile.created_at)}</span>
          </div>
          <div className="metadata-item">
            <strong>Last Updated:</strong>
            <span>{formatDate(profile.updated_at)}</span>
          </div>
        </div>

        {/* Career Goals */}
        <div className="profile-section">
          <h3>Career Goals</h3>
          <div className="career-goals">
            {profile.career_goals ? (
              <p>{profile.career_goals}</p>
            ) : (
              <p className="no-data">No career goals specified.</p>
            )}
          </div>
        </div>

        {/* Resume Section */}
        {profile.resume_path && (
          <div className="profile-section">
            <h3>Resume</h3>
            <object data={profile.resume_path} type="application/pdf" width="100%" height="500px">
      <p>Unable to display PDF file. <a href="/uploads/media/default/0001/01/540cb75550adf33f281f29132dddd14fded85bfc.pdf">Download</a> instead.</p>
    </object>
            <div className="file-info">
              <div className="file-details">
                <strong>File:</strong> {getFileName(profile.resume_path)}
                <br />
                <strong>Type:</strong> {getFileExtension(profile.resume_path).toUpperCase() || 'Unknown'}
                <br />
                <strong>Path:</strong> <code>{profile.resume_path}</code>
              </div>
              <div className="file-actions">
                <button 
                  onClick={() => handleView(profile.resume_path)}
                  className="btn btn-primary"
                  disabled
                  title="File viewing not available for local paths"
                >
                  View Resume
                </button>
                <button 
                  onClick={() => handleDownload(profile.resume_path, getFileName(profile.resume_path))}
                  className="btn btn-secondary"
                  disabled
                  title="File download not available for local paths"
                >
                  Download Resume
                </button>
              </div>
            </div>
          </div>
        )}

        {/* LinkedIn Section */}
        {profile.linkedin_path && (
          <div className="profile-section">
            <h3>LinkedIn Profile</h3>
            <div className="file-info">
              <div className="file-details">
                <strong>File:</strong> {getFileName(profile.linkedin_path)}
                <br />
                <strong>Type:</strong> {getFileExtension(profile.linkedin_path).toUpperCase() || 'Unknown'}
                <br />
                <strong>Path:</strong> <code>{profile.linkedin_path}</code>
                <object data={profile.linkedin_path} type="application/pdf" width="100%" height="500px">
      <p>Unable to display PDF file. <a href="/uploads/media/default/0001/01/540cb75550adf33f281f29132dddd14fded85bfc.pdf">Download</a> instead.</p>
    </object>
              </div>
              <div className="file-actions">
                <button 
                  onClick={() => handleView(profile.linkedin_path)}
                  className="btn btn-primary"
                  disabled
                  title="File viewing not available for local paths"
                >
                  View LinkedIn
                </button>
                <button 
                  onClick={() => handleDownload(profile.linkedin_path, getFileName(profile.linkedin_path))}
                  className="btn btn-secondary"
                  disabled
                  title="File download not available for local paths"
                >
                  Download LinkedIn
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Note about file access */}
        <div className="file-access-note">
          <p><strong>Note:</strong> File viewing and downloading is currently not available as the files are stored locally. 
          To enable file access, you'll need to implement a backend endpoint that serves these files.</p>
        </div>
      </div>
    </div>
  );
};

export default ViewProfile;