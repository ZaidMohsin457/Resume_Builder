// Global variables
let resumeId = null;
let userId = null;
let extractedSkills = [];
let jobTitles = [];

// DOM Elements
const resumeForm = document.getElementById('resumeForm');
const resumeAnalysisForm = document.getElementById('resumeAnalysisForm');
const loadingSpinner = document.getElementById('loadingSpinner');
const resultsContainer = document.getElementById('resultsContainer');
const extractedInfo = document.getElementById('extractedInfo');
const skillsList = document.getElementById('skillsList');
const titlesList = document.getElementById('jobTitlesList');
const recommendations = document.getElementById('recommendations');
const jobList = document.getElementById('jobList');

// Event Listeners
resumeForm.addEventListener('submit', handleResumeUpload);
resumeAnalysisForm.addEventListener('submit', handleResumeAnalysis);

// Resume Upload Handler
async function handleResumeUpload(e) {
    e.preventDefault();
    
    // Show loading spinner
    loadingSpinner.style.display = 'block';
    resultsContainer.style.display = 'none';
    
    const formData = new FormData(this);
    
    try {
        const response = await fetch('/upload-resume/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Display extracted information
            if (data.skills && data.skills.length > 0) {
                skillsList.innerHTML = data.skills.map(skill => 
                    `<span class="badge bg-primary me-2 mb-2">${skill}</span>`
                ).join('');
            }
            
            if (data.job_titles && data.job_titles.length > 0) {
                titlesList.innerHTML = data.job_titles.map(title => 
                    `<span class="badge bg-secondary me-2 mb-2">${title}</span>`
                ).join('');
            }
            
            // Display matched jobs
            if (data.matched_jobs && data.matched_jobs.length > 0) {
                jobList.innerHTML = data.matched_jobs.map(job => `
                    <div class="job-item">
                        <h3 class="job-title">${job.title}</h3>
                        <div class="job-company">${job.company}</div>
                        <div class="job-location">${job.location}</div>
                        <div class="job-description">${job.description}</div>
                        <a href="${job.url}" target="_blank" class="btn btn-primary mt-2">Apply Now</a>
                    </div>
                `).join('');
            } else {
                jobList.innerHTML = '<div class="alert alert-info">No matching jobs found. Try adjusting your search criteria.</div>';
            }
            
            // Show results
            extractedInfo.style.display = 'block';
            resultsContainer.style.display = 'block';
        } else {
            throw new Error(data.error || 'Failed to process resume');
        }
    } catch (error) {
        console.error('Error:', error);
        jobList.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
        resultsContainer.style.display = 'block';
    } finally {
        loadingSpinner.style.display = 'none';
    }
}

// Resume Analysis Handler
async function handleResumeAnalysis(e) {
    e.preventDefault();
    
    // Hide previous results
    extractedInfo.style.display = 'none';
    resultsContainer.innerHTML = '';
    recommendations.style.display = 'none';
    
    // Show loading spinner
    loadingSpinner.style.display = 'block';
    
    try {
        const formData = new FormData(this);
        
        // First upload the resume
        const uploadResponse = await fetch('/upload-resume/', {
            method: 'POST',
            body: formData
        });
        
        const uploadData = await uploadResponse.json();
        
        if (uploadData.status === 'success') {
            // Now send the job description for analysis
            const analysisResponse = await fetch(`/analyze-job-match/${uploadData.analysis_id}/`, {
                method: 'POST',
                body: formData
            });
            
            const analysisData = await analysisResponse.json();
            
            // Hide loading spinner
            loadingSpinner.style.display = 'none';
            
            if (analysisData.status === 'success') {
                // Show recommendations
                recommendations.style.display = 'block';
                const recommendationsList = document.getElementById('recommendationsList');
                
                recommendationsList.innerHTML = analysisData.recommendations.map(rec => `
                    <div class="recommendation-card mb-4">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-subtitle mb-2 text-muted">
                                    <i class="fas fa-tag me-2"></i>${rec.category} - ${rec.section}
                                </h6>
                                <div class="current-content mb-3">
                                    <strong>Current Content:</strong>
                                    <p class="mb-2">${rec.current_content}</p>
                                </div>
                                <div class="suggested-change mb-3">
                                    <strong>Suggested Change:</strong>
                                    <p class="mb-2">${rec.direct_implementation}</p>
                                </div>
                                <div class="reason">
                                    <strong>Why This Matters:</strong>
                                    <p class="mb-0">${rec.reason_impact}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                recommendations.innerHTML = `
                    <div class="col-md-8 offset-md-2">
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i>${analysisData.error}
                        </div>
                    </div>
                `;
            }
        } else {
            loadingSpinner.style.display = 'none';
            recommendations.innerHTML = `
                <div class="col-md-8 offset-md-2">
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>${uploadData.error}
                    </div>
                </div>
            `;
        }
    } catch (error) {
        loadingSpinner.style.display = 'none';
        recommendations.innerHTML = `
            <div class="col-md-8 offset-md-2">
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>An error occurred. Please try again.
                </div>
            </div>
        `;
    }
}

// Display Functions
function showExtractedInfo() {
    if (extractedSkills.length === 0 && jobTitles.length === 0) {
        showError('No skills or job titles could be extracted from your resume.');
        return;
    }

    extractedInfo.style.display = 'block';
    
    if (extractedSkills.length > 0) {
        skillsList.innerHTML = extractedSkills
            .map(skill => `<span class="badge badge-skill">${skill}</span>`).join(' ');
    } else {
        skillsList.innerHTML = '<span class="text-muted">No skills found</span>';
    }

    if (jobTitles.length > 0) {
        titlesList.innerHTML = jobTitles
            .map(title => `<span class="badge badge-title">${title}</span>`).join(' ');
    } else {
        titlesList.innerHTML = '<span class="text-muted">No job titles found</span>';
    }
}

function displayJobMatches(matches) {
    if (!matches || matches.length === 0) {
        showInfo('No matching jobs found. Try adjusting your location or search criteria.');
        return;
    }

    let resultsHtml = `
        <div class="col-12">
            <h3 class="section-title mb-4">
                <i class="fas fa-briefcase me-2"></i>Matching Jobs (${matches.length})
            </h3>
        </div>
    `;

    matches.forEach(job => {
        const matchScore = Math.round((job.match_score || 0) * 100);
        resultsHtml += `
            <div class="col-md-6 mb-4">
                <div class="card job-card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${job.job_title || job.title || 'Job Title Not Available'}</h5>
                        <h6 class="card-subtitle mb-3 text-muted">
                            <i class="fas fa-building me-2"></i>${job.employer_name || job.company || 'Company Not Specified'}
                        </h6>
                        <div class="job-info">
                            <p class="mb-2">
                                <i class="fas fa-map-marker-alt me-2"></i>
                                <strong>Location:</strong> ${job.job_city || job.location || 'Remote'}
                            </p>
                            <p class="mb-2">
                                <i class="fas fa-money-bill-wave me-2"></i>
                                <strong>Salary:</strong> ${job.job_salary || job.salary || 'Not specified'}
                            </p>
                            <p class="mb-3">
                                <i class="fas fa-clock me-2"></i>
                                <strong>Type:</strong> ${job.job_employment_type || job.job_type || 'Not specified'}
                            </p>
                        </div>
                        <p class="card-text mb-4">${job.job_description || job.description || 'No description available'}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="match-score ${getMatchScoreClass(job.match_score)}">
                                <i class="fas fa-percentage me-2"></i>
                                Match: ${matchScore}%
                            </span>
                            <a href="${job.job_apply_link || job.job_google_link || job.url || '#'}" 
                               class="btn btn-primary" target="_blank">
                                <i class="fas fa-external-link-alt me-2"></i>Apply
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    resultsContainer.innerHTML = resultsHtml;
}

// Utility Functions
function getMatchScoreClass(score) {
    if (score >= 0.7) return 'high-match';
    if (score >= 0.4) return 'medium-match';
    return 'low-match';
}

function showLoading(message = 'Processing...') {
    loadingSpinner.querySelector('p').textContent = message;
    loadingSpinner.style.display = 'block';
    resultsContainer.innerHTML = '';
    extractedInfo.style.display = 'none';
}

function hideLoading() {
    loadingSpinner.style.display = 'none';
}

function clearResults() {
    resultsContainer.innerHTML = '';
    extractedInfo.style.display = 'none';
}

function showError(message) {
    resultsContainer.innerHTML = `
        <div class="col-12">
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle me-2"></i>${message}
            </div>
        </div>
    `;
}

function showSuccess(message) {
    resultsContainer.innerHTML = `
        <div class="col-12">
            <div class="alert alert-success">
                <i class="fas fa-check-circle me-2"></i>${message}
            </div>
        </div>
    `;
}

function showInfo(message) {
    resultsContainer.innerHTML = `
        <div class="col-12">
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>${message}
            </div>
        </div>
    `;
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
} 