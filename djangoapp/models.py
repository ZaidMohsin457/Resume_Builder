from django.db import models
import os

# Create your models here.

class ResumeAnalysis(models.Model):
    resume_file = models.FileField(upload_to='uploads/')
    job_description = models.TextField(blank=True, null=True)
    recommendations = models.JSONField(blank=True, null=True)
    improved_resume = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return os.path.basename(self.resume_file.name) if self.resume_file else "No file"
