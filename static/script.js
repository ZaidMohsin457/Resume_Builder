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

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('resumeUpload');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            
            if (!file) {
                return;
            }
            
            if (file.type === 'application/pdf') {
                const formData = new FormData();
                formData.append('file', file);
                
                fetch('/', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Store the analysis_id in localStorage
                        localStorage.setItem('currentAnalysisId', data.analysis_id);
                        window.location.href = '/options';
                    } else {
                        alert('Error uploading file: ' + data.message);
                    }
                })
                .catch(error => {
                    alert('Error uploading file: ' + error.message);
                });
            } else {
                alert('Please upload a PDF file');
            }
        });
    }
});