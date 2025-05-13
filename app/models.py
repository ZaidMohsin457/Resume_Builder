from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
import json

class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    skills = models.JSONField(default=list, blank=True)
    job_titles = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Resume" if self.user else "Anonymous Resume"

class Job(models.Model):
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    description = models.TextField()
    apply_link = models.URLField()
    required_skills = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} at {self.company}"

class MatchedJob(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='matched_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='matches')
    match_score = models.FloatField()
    matching_skills = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('resume', 'job')

    def __str__(self):
        return f"{self.resume} matched with {self.job} ({self.match_score:.2f})"

class JobMatch(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    description = models.TextField()
    url = models.URLField()
    match_score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.job_title} at {self.company}"

class ResumeAnalysis(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, null=True, blank=True)
    job_description = models.TextField()
    recommendations = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_recommendations(self, recommendations):
        self.recommendations = recommendations
        self.save()

    def get_recommendations(self):
        return self.recommendations or []

    def __str__(self):
        return f"Analysis for {self.resume} - {self.created_at}"

    class Meta:
        verbose_name_plural = 'Resume Analyses' 