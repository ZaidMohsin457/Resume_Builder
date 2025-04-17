from django.db import models

# Create your models here.

class ResumeAnalysis(models.Model):
    resume_file = models.FileField(upload_to='uploads/')
    job_description = models.TextField()
    recommendations = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Analysis {self.id}"
