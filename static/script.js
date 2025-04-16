// File Upload Handling
document.getElementById('resumeUpload')?.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      localStorage.setItem('uploadedResume', file.name);
      window.location.href = '/options';
    } else {
      alert('Please upload a PDF file');
    }
  });
  
  // Shared Functions
  function loadResumeName() {
    const resumeName = localStorage.getItem('uploadedResume');
    document.querySelectorAll('#resumeName, #analysisResumeName').forEach(el => {
      el.textContent = resumeName || 'No resume uploaded';
    });
  }
  
  // Analysis Page Functionality
  function initializeAnalysisPage() {
    loadResumeName();
    
    document.querySelectorAll('.recommendation-actions').forEach(actions => {
      actions.addEventListener('click', (e) => {
        const card = e.target.closest('.recommendation-card');
        const isAccept = e.target.classList.contains('accept-button');
        
        if(isAccept) {
          card.classList.add('accepted');
          e.target.textContent = 'Accepted';
        } else if(e.target.classList.contains('reject-button')) {
          card.remove();
        }
      });
    });
    document.querySelector('.download-button')?.addEventListener('click', () => {
      alert('Downloading enhanced resume...');
      const link = document.createElement('a');
      link.download = `enhanced_${localStorage.getItem('uploadedResume')}`;
      link.href = '#';
      link.click();
    });
  }
  
  // Page Initialization
  document.addEventListener('DOMContentLoaded', () => {
    if(document.querySelector('.analysis-container')) {
      initializeAnalysisPage();
    }
  });