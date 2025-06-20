import React, { useState } from 'react'
import { Formik, Form, Field, ErrorMessage } from 'formik'
import { toast } from 'react-toastify'
import './AgentDataUpload.style.scss'
import FileUpload from '../../components/fileUpload/FileUpload'
import { link } from '../../contant/regex'
import { validationSchema } from '../../validation/Validation'
import { agentService } from '../../service/Agent.service'
import { useNavigate } from 'react-router-dom'

const AgentDataUpload = () => {
    const [currentUrl, setCurrentUrl] = useState('')
    const [showFileUpload, setShowFileUpload] = useState(false)
    const [uploadConfig, setUploadConfig] = useState({})
    const [activeField, setActiveField] = useState('')
    const navigate = useNavigate()

    const initialValues = {
        resume: null,
        careerGoals: '',
        linkedinProfile: null,
        companyData: null,
        jobDescriptions: '',
        companyUrls: []
    }

    const openFileUpload = (type, title, description, acceptedTypes, setFieldValue) => {
        setUploadConfig({
            type,
            title,
            description,
            acceptedTypes,
            setFieldValue
        })
        setActiveField(type)
        setShowFileUpload(true)
    }

    const handleFileUpload = (file) => {
        if (!file) {
            toast.error('No file selected')
            return
        }

        const fileSize = file.size / (1024 * 1024) 

        if (activeField === 'resume' || activeField === 'companyData') {
            if (file.type !== 'application/pdf' && !file.name?.endsWith('.pdf')) {
                toast.error('Only PDF files are allowed for this field')
                return
            }
            const maxSize = activeField === 'resume' ? 5 : 10
            if (fileSize > maxSize) {
                toast.error(`File size must be less than ${maxSize}MB`)
                return
            }
        }

        if (activeField === 'linkedinProfile') {
            if (file.type !== 'text/plain' && !file.name?.endsWith('.txt')) {
                toast.error('Only TXT files are allowed for LinkedIn profile')
                return
            }
            if (fileSize > 2) {
                toast.error('File size must be less than 2MB')
                return
            }
        }

        if (uploadConfig.setFieldValue && activeField) {
            uploadConfig.setFieldValue(activeField, file)
            toast.success(`${file.name} uploaded successfully!`)
        }

        setShowFileUpload(false)
        setActiveField('')
    }

    const handleAddUrl = (url, values, setFieldValue) => {
        const trimmedUrl = url.trim()

        const urlRegex = link

        if (!trimmedUrl) {
            toast.error('Please enter a URL')
            return
        }

        if (!urlRegex.test(trimmedUrl)) {
            toast.error('Please enter a valid URL (must start with http:// or https://)')
            return
        }

        if (values.companyUrls.includes(trimmedUrl)) {
            toast.warning('This URL has already been added')
            return
        }

        if (values.companyUrls.length >= 10) {
            toast.error('Maximum 10 URLs allowed')
            return
        }

        setFieldValue('companyUrls', [...values.companyUrls, trimmedUrl])
        setCurrentUrl('')
        toast.success('URL added successfully!')
    }

    const handleRemoveUrl = (urlToRemove, values, setFieldValue) => {
        const updatedUrls = values.companyUrls.filter(url => url !== urlToRemove)
        setFieldValue('companyUrls', updatedUrls)
        toast.info('URL removed')
    }

    const handleKeyPress = (e, url, values, setFieldValue) => {
        if (e.key === 'Enter') {
            e.preventDefault()
            handleAddUrl(url, values, setFieldValue)
        }
    }

    const handleSubmit = async (values, { setSubmitting, resetForm }) => {
        try {
            setSubmitting(true)
            
            // Show loading toast
            const loadingToast = toast.loading('Uploading your data...')

            // Validate form data using service
            const validation = agentService.validateFormData(values)
            if (!validation.isValid) {
                toast.dismiss(loadingToast)
                validation.errors.forEach(error => {
                    toast.error(error)
                })
                setSubmitting(false)
                return
            }

            // Submit data using the service
            const response = await agentService.analyzeCompatibility(values)
            
            // Dismiss loading toast
            toast.dismiss(loadingToast)

            // Show success message
            toast.success('🎉 Data uploaded and analyzed successfully!', {
                position: "top-right",
                autoClose: 5000,
                hideProgressBar: false,
                closeOnClick: true,
                pauseOnHover: true,
                draggable: true,
            })

            // Handle successful response
            console.log('Analysis results:', response)
            
            // You can handle the response data here
            // For example, redirect to results page or show results
            if (response.analysis_id) {
                navigate(`/dashboard/${response.analysis_id}`)
            }

            // Reset form on success
            resetForm()
            
        } catch (error) {
            console.error('Submission error:', error)
            
            // Show error message
            toast.error(error.message || 'Failed to upload data. Please try again.', {
                position: "top-right",
                autoClose: 5000,
                hideProgressBar: false,
                closeOnClick: true,
                pauseOnHover: true,
                draggable: true,
            })
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <section className='agent-data-upload'>
            <Formik
                initialValues={initialValues}
                validationSchema={validationSchema}
                onSubmit={handleSubmit}
            >
                {({ values, setFieldValue, isSubmitting, errors, touched }) => (
                    <Form>
                        <div className="heading">
                            <h1>Start Your Career Compatibility Evaluation</h1>
                        </div>

                        {/* Resume File */}
                        <div className="form-field">
                            <label className="field-label">Resume File (PDF) *</label>
                            <div className="file-upload-section">
                                <button
                                    type="button"
                                    className={`file-upload-btn ${errors.resume && touched.resume ? 'error' : ''}`}
                                    onClick={() => openFileUpload('resume', 'Upload Resume', 'Attach your resume file below', '.pdf', setFieldValue)}
                                >
                                    <span className="upload-icon">📄</span>
                                    <span className="upload-text">
                                        {values.resume ? values.resume.name : 'Choose Resume PDF'}
                                    </span>
                                </button>
                                <ErrorMessage name="resume" component="div" className="error-message" />
                            </div>
                        </div>

                        {/* Career Goals */}
                        <div className="form-field">
                            <label className="field-label">Career Goals *</label>
                            <Field
                                as="textarea"
                                name="careerGoals"
                                className={`text-area ${errors.careerGoals && touched.careerGoals ? 'error' : ''}`}
                                placeholder="e.g., I want to work in tech startups focused on AI..."
                                rows="4"
                            />
                            <ErrorMessage name="careerGoals" component="div" className="error-message" />
                            <div className="char-count">
                                {values.careerGoals.length}/1000 characters
                            </div>
                        </div>

                        {/* LinkedIn Profile */}
                        <div className="form-field">
                            <label className="field-label">LinkedIn Profile (TXT) *</label>
                            <div className="file-upload-section">
                                <button
                                    type="button"
                                    className={`file-upload-btn ${errors.linkedinProfile && touched.linkedinProfile ? 'error' : ''}`}
                                    onClick={() => openFileUpload('linkedinProfile', 'Upload LinkedIn Profile', 'Attach your LinkedIn profile text file below', '.txt', setFieldValue)}
                                >
                                    <span className="upload-icon">📝</span>
                                    <span className="upload-text">
                                        {values.linkedinProfile ? values.linkedinProfile.name : 'Choose LinkedIn TXT'}
                                    </span>
                                </button>
                                <ErrorMessage name="linkedinProfile" component="div" className="error-message" />
                            </div>
                        </div>

                        {/* Company Data */}
                        <div className="form-field">
                            <label className="field-label">Company Data (PDF) *</label>
                            <div className="file-upload-section">
                                <button
                                    type="button"
                                    className={`file-upload-btn ${errors.companyData && touched.companyData ? 'error' : ''}`}
                                    onClick={() => openFileUpload('companyData', 'Upload Company Data', 'Attach your company data file below', '.pdf', setFieldValue)}
                                >
                                    <span className="upload-icon">🏢</span>
                                    <span className="upload-text">
                                        {values.companyData ? values.companyData.name : 'Choose Company PDF'}
                                    </span>
                                </button>
                                <ErrorMessage name="companyData" component="div" className="error-message" />
                            </div>
                        </div>

                        {/* Job Descriptions */}
                        <div className="form-field">
                            <label className="field-label">Job Descriptions *</label>
                            <Field
                                as="textarea"
                                name="jobDescriptions"
                                className={`text-area ${errors.jobDescriptions && touched.jobDescriptions ? 'error' : ''}`}
                                placeholder="Paste 1–2 job descriptions for roles you're targeting..."
                                rows="6"
                            />
                            <ErrorMessage name="jobDescriptions" component="div" className="error-message" />
                            <div className="char-count">
                                {values.jobDescriptions.length}/5000 characters
                            </div>
                        </div>

                        {/* Company URLs */}
                        <div className="form-field">
                            <label className="field-label">Company URLs *</label>
                            <div className="url-input-container">
                                <div className="url-input-wrapper">
                                    <input
                                        type="url"
                                        className={`url-input ${errors.companyUrls && touched.companyUrls ? 'error' : ''}`}
                                        placeholder="Enter company URL (https://example.com) and press Enter"
                                        value={currentUrl}
                                        onChange={(e) => setCurrentUrl(e.target.value)}
                                        onKeyPress={(e) => handleKeyPress(e, currentUrl, values, setFieldValue)}
                                    />
                                    <button
                                        type="button"
                                        className="add-url-btn"
                                        onClick={() => handleAddUrl(currentUrl, values, setFieldValue)}
                                    >
                                        Add
                                    </button>
                                </div>
                                <div className="url-chips">
                                    {values.companyUrls.map((url, index) => (
                                        <div key={index} className="url-chip">
                                            <span className="url-text">{url}</span>
                                            <button
                                                type="button"
                                                className="remove-chip"
                                                onClick={() => handleRemoveUrl(url, values, setFieldValue)}
                                            >
                                                ×
                                            </button>
                                        </div>
                                    ))}
                                </div>
                                <ErrorMessage name="companyUrls" component="div" className="error-message" />
                                <div className="url-count">
                                    {values.companyUrls.length}/10 URLs added
                                </div>
                            </div>
                        </div>

                        <div className="submit-section">
                            <button
                                type="submit"
                                className="submit-btn"
                                disabled={isSubmitting}
                            >
                                {isSubmitting ? 'Analyze...' : 'Analyze Data'}
                            </button>
                        </div>

                        {/* File Upload Modal */}
                        {showFileUpload && (
                            <FileUpload
                                title={uploadConfig.title}
                                description={uploadConfig.description}
                                acceptedFileTypes={uploadConfig.acceptedTypes}
                                onFileSelect={handleFileUpload}
                                onClose={() => setShowFileUpload(false)}
                            />
                        )}
                    </Form>
                )}
            </Formik>
        </section>
    )
}

export default AgentDataUpload