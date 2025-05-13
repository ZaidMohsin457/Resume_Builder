// Global variables
let resumeId = null;
let userId = null;
let extractedSkills = [];
let jobTitles = [];
let currentResumeId = null;

// DOM Elements
const resumeForm = document.getElementById('resumeForm');
const resumeAnalysisForm = document.getElementById('resumeAnalysisForm');
const loadingSpinner = document.getElementById('loadingSpinner');
const analysisLoadingSpinner = document.getElementById('analysisLoadingSpinner');
const resultsContainer = document.getElementById('resultsContainer');
const extractedInfo = document.getElementById('extractedInfo');
const skillsList = document.getElementById('skillsList');
const titlesList = document.getElementById('jobTitlesList');
const recommendations = document.getElementById('recommendations');
const jobList = document.getElementById('jobList');
const recommendationsList = document.getElementById('recommendationsList');
const jobResults = document.getElementById('jobResults');

// Event Listeners
if (resumeForm) {
    resumeForm.addEventListener('submit', handleResumeUpload);
}

document.addEventListener('DOMContentLoaded', function() {
    if (resumeAnalysisForm) {
        resumeAnalysisForm.addEventListener('submit', handleResumeAnalysis);
    }
    fetchDemoRecommendations();
});

// Resume Upload Handler
async function handleResumeUpload(e) {
    e.preventDefault();
    
    if (!loadingSpinner || !extractedInfo || !jobResults) {
        console.error('Required DOM elements not found');
        return;
    }
    
    // Show loading spinner
    loadingSpinner.style.display = 'block';
    extractedInfo.style.display = 'none';
    jobResults.innerHTML = '';
    
    const formData = new FormData(this);
    
    try {
        const response = await fetch('/upload-resume/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            currentResumeId = data.resume_id;
            
            // Display extracted information
            if (skillsList && titlesList) {
                displayExtractedInfo(data.skills, data.job_titles);
            }
            
            // Display matched jobs
            displayMatchedJobs(data.matched_jobs);
            
        } else {
            showError(data.error || 'An error occurred while processing your resume.');
        }
        
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred while uploading your resume. Please try again.');
    } finally {
        if (loadingSpinner) {
            loadingSpinner.style.display = 'none';
        }
    }
}

// Resume Analysis Handler
async function handleResumeAnalysis(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    // Show loading spinner
    if (loadingSpinner) {
        loadingSpinner.style.display = 'block';
    }
    
    try {
        // Send the resume and job description for analysis
        const response = await fetch('/get-resume-suggestions/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        // Hide loading spinner
        if (loadingSpinner) {
            loadingSpinner.style.display = 'none';
        }
        
        if (data.success) {
            // Show recommendations
            if (recommendations) {
                recommendations.style.display = 'block';
                const parsedSuggestions = JSON.parse(data.suggestions);
                recommendations.innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Resume Improvement Suggestions</h5>
                            <div class="suggestions-content">
                                ${parsedSuggestions.map(suggestion => 
                                    `<div class="suggestion-item">
                                        <h6>${suggestion.category}</h6>
                                        <p><strong>Section:</strong> ${suggestion.section}</p>
                                        <p><strong>Current Content:</strong> ${suggestion.current_content}</p>
                                        <p><strong>Implementation:</strong> ${suggestion.direct_implementation}</p>
                                        <p><strong>Impact:</strong> ${suggestion.reason_impact}</p>
                                    </div>`
                                ).join('')}
                            </div>
                        </div>
                    </div>
                `;
            }
        } else {
            showError(data.error || 'An error occurred while analyzing your resume.');
        }
    } catch (error) {
        console.error('Error:', error);
        if (loadingSpinner) {
            loadingSpinner.style.display = 'none';
        }
        showError('An error occurred. Please try again.');
    }
}

// Display Functions
function displayExtractedInfo(skills, jobTitles) {
    if (!extractedInfo || !skillsList || !titlesList) {
        console.error('Required DOM elements not found');
        return;
    }
    
    extractedInfo.style.display = 'block';
    
    if (skills && skills.length > 0) {
        skillsList.innerHTML = skills.map(skill => 
            `<span class="badge bg-primary me-2 mb-2">${skill}</span>`
        ).join('');
    } else {
        skillsList.innerHTML = '<p class="text-muted">No skills found in resume.</p>';
    }
    
    if (jobTitles && jobTitles.length > 0) {
        titlesList.innerHTML = jobTitles.map(title => 
            `<span class="badge bg-secondary me-2 mb-2">${title}</span>`
        ).join('');
    } else {
        titlesList.innerHTML = '<p class="text-muted">No job titles found in resume.</p>';
    }
}

function displayMatchedJobs(jobs) {
    if (!jobResults) {
        console.error('Job results container not found');
        return;
    }
    
    if (jobs && jobs.length > 0) {
        jobResults.innerHTML = jobs.map(job => `
            <div class="job-item card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h5 class="card-title">${job.title}</h5>
                            <h6 class="card-subtitle mb-2 text-muted">${job.company}</h6>
                        </div>
                        <div class="match-score">
                            <span class="badge ${getMatchScoreClass(job.match_score)}">
                                ${(job.match_score * 100).toFixed(1)}% Match
                            </span>
                        </div>
                    </div>
                    <div class="job-details mt-3">
                        <p class="card-text">
                            <i class="fas fa-map-marker-alt"></i> ${job.location}
                            <span class="mx-2">|</span>
                            <i class="fas fa-briefcase"></i> ${job.job_type || 'Full-time'}
                        </p>
                        <div class="job-description">
                            <p class="card-text">${job.description}</p>
                        </div>
                        <div class="job-skills mt-2">
                            <h6>Required Skills:</h6>
                            <div class="skill-tags">
                                ${(job.required_skills || []).map(skill => 
                                    `<span class="badge bg-primary me-1">${skill}</span>`
                                ).join('')}
                            </div>
                        </div>
                    </div>
                    <div class="job-actions mt-3">
                        <a href="${job.apply_link}" class="btn btn-primary" target="_blank">Apply Now</a>
                        <button class="btn btn-outline-primary ms-2" onclick="showImprovements('${job.id}')">
                            Get Improvement Suggestions
                        </button>
                    </div>
                    <div id="improvements-${job.id}" class="improvement-suggestions mt-3" style="display: none;">
                        <h6>Improvement Suggestions:</h6>
                        <div class="suggestions-list">
                            <!-- Suggestions will be loaded here -->
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } else {
        jobResults.innerHTML = `
            <div class="alert alert-info">
                No matching jobs found. Try adjusting your location or search criteria.
            </div>
        `;
    }
}

// Show Improvements
async function showImprovements(jobId) {
    if (!jobId) {
        console.error('Job ID is required');
        showError('Job ID is missing. Please try again.');
        return;
    }

    const improvementsDiv = document.getElementById(`improvements-${jobId}`);
    if (!improvementsDiv) {
        console.error('Improvements div not found');
        return;
    }
    
    const suggestionsList = improvementsDiv.querySelector('.suggestions-list');
    if (!suggestionsList) {
        console.error('Suggestions list not found');
        return;
    }
    
    // Show loading state
    suggestionsList.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div></div>';
    improvementsDiv.style.display = 'block';
    
    try {
        const response = await fetch(`/analyze-job-match/${jobId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                resume_id: currentResumeId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            suggestionsList.innerHTML = data.suggestions.map(suggestion => `
                <div class="suggestion-item">
                    <h6>${suggestion.category}</h6>
                    <p><strong>Section:</strong> ${suggestion.section}</p>
                    <p><strong>Current Content:</strong> ${suggestion.current_content}</p>
                    <p><strong>Implementation:</strong> ${suggestion.direct_implementation}</p>
                    <p><strong>Impact:</strong> ${suggestion.reason_impact}</p>
                </div>
            `).join('');
        } else {
            suggestionsList.innerHTML = '<div class="alert alert-danger">Failed to load suggestions. Please try again.</div>';
        }
    } catch (error) {
        console.error('Error:', error);
        suggestionsList.innerHTML = '<div class="alert alert-danger">An error occurred. Please try again.</div>';
    }
}

// Utility Functions
function getMatchScoreClass(score) {
    if (score >= 0.8) return 'bg-success';
    if (score >= 0.6) return 'bg-warning';
    return 'bg-danger';
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
    if (!jobResults) {
        console.error('Job results container not found');
        return;
    }
    
    jobResults.innerHTML = `
        <div class="alert alert-danger">
            ${message}
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