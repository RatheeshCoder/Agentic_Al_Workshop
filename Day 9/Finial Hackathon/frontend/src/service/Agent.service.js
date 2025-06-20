import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, 
});

export const agentService = {

  analyzeCompatibility: async (formData) => {
    try {
      const data = new FormData();

      if (formData.resume) {
        data.append('resume_file', formData.resume);
      }
      
      if (formData.linkedinProfile) {
        data.append('linkedin_profile', formData.linkedinProfile);
      }
      
      if (formData.companyData) {
        data.append('company_data', formData.companyData);
      }

      if (formData.careerGoals) {
        data.append('career_goals', formData.careerGoals);
      }
      
      if (formData.jobDescriptions) {
        data.append('job_descriptions', formData.jobDescriptions);
      }

      if (formData.companyUrls && formData.companyUrls.length > 0) {
        data.append('company_urls', JSON.stringify(formData.companyUrls));
      }

      const response = await apiClient.post('/analyze-compatibility', data, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          console.log(`Upload Progress: ${percentCompleted}%`);
        },
      });

      return response.data;
    } catch (error) {
      if (error.response) {
        const errorMessage = error.response.data?.message || 
                           error.response.data?.error || 
                           `Server error: ${error.response.status}`;
        throw new Error(errorMessage);
      } else if (error.request) {
        throw new Error('Network error: Unable to connect to server');
      } else {
        throw new Error(error.message || 'An unexpected error occurred');
      }
    }
  },


  validateFormData: (formData) => {
    const errors = [];

    if (!formData.resume) {
      errors.push('Resume file is required');
    }
    
    if (!formData.linkedinProfile) {
      errors.push('LinkedIn profile file is required');
    }
    
    if (!formData.companyData) {
      errors.push('Company data file is required');
    }

    if (!formData.careerGoals || formData.careerGoals.trim().length === 0) {
      errors.push('Career goals are required');
    }
    
    if (!formData.jobDescriptions || formData.jobDescriptions.trim().length === 0) {
      errors.push('Job descriptions are required');
    }

    if (!formData.companyUrls || formData.companyUrls.length === 0) {
      errors.push('At least one company URL is required');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }
};


export const  getFinialReport = async (reportId) => {
  try {
    const response = await apiClient.get(`/analysis/${reportId}`);
    return response.data;
  } catch (error) {
    if (error.response) {
      const errorMessage = error.response.data?.message || 
                           error.response.data?.error || 
                           `Server error: ${error.response.status}`;
      throw new Error(errorMessage);
    } else if (error.request) {
      throw new Error('Network error: Unable to connect to server');
    } else {
      throw new Error(error.message || 'An unexpected error occurred');
    }
  }
}