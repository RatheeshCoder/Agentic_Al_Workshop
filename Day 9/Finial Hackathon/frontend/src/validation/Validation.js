import * as Yup from 'yup'

import { link,description } from '../contant/regex'
export const validationSchema = Yup.object({
    resume: Yup.mixed()
        .required('Resume file is required')
        .test('fileType', 'Only PDF files are allowed', (value) => {
            if (!value) return false
            return value.type === 'application/pdf' || value.name?.endsWith('.pdf')
        })
        .test('fileSize', 'File size must be less than 5MB', (value) => {
            if (!value) return false
            return value.size <= 5 * 1024 * 1024 // 5MB
        }),

    careerGoals: Yup.string()
        .required('Career goals are required')
        .min(50, 'Career goals must be at least 50 characters')
        .max(1000, 'Career goals must not exceed 1000 characters'),

    linkedinProfile: Yup.mixed()
        .required('LinkedIn profile file is required')
        .test('fileType', 'Only TXT files are allowed', (value) => {
            if (!value) return false
            return value.type === 'text/plain' || value.name?.endsWith('.txt')
        })
        .test('fileSize', 'File size must be less than 2MB', (value) => {
            if (!value) return false
            return value.size <= 2 * 1024 * 1024 // 2MB
        }),

    companyData: Yup.mixed()
        .required('Company data file is required')
        .test('fileType', 'Only PDF files are allowed', (value) => {
            if (!value) return false
            return value.type === 'application/pdf' || value.name?.endsWith('.pdf')
        })
        .test('fileSize', 'File size must be less than 10MB', (value) => {
            if (!value) return false
            return value.size <= 10 * 1024 * 1024 // 10MB
        }),

    jobDescriptions: Yup.string()
        .required('Job descriptions are required')
        .min(100, 'Job descriptions must be at least 100 characters')
        .max(5000, 'Job descriptions must not exceed 5000 characters'),

    companyUrls: Yup.array()
        .of(
            Yup.string()
                .url('Invalid URL format')
              
        )
        .min(1, 'At least one company URL is required')
        .max(10, 'Maximum 10 URLs allowed')
})