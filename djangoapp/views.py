from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import os
from django.conf import settings
from .models import ResumeAnalysis
import PyPDF2
import openai
import json

global analysis_id
@csrf_exempt
def index(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(settings.BASE_DIR, 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # Save the file and create ResumeAnalysis object
        # Get only the filename without the path
        filename = file.name
        analysis = ResumeAnalysis(resume_file=file)
        analysis.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'File uploaded successfully',
            'analysis_id': analysis.id
        })
    
    return render(request, 'index.html')

def user_job_description(request):
    if request.method == 'POST':
        job_description = request.POST.get('job_description')
        # analysis_id = request.POST.get('analysis_id')
        analysis_id = 1
        
        try:
            analysis = ResumeAnalysis.objects.get(id=analysis_id)
            analysis.job_description = job_description
            
            # Extract text from PDF
            resume_text = extract_text_from_pdf(analysis.resume_file.path)
            
            # Get recommendations
            recommendations = get_recommendations(resume_text, job_description)
            analysis.recommendations = recommendations
            analysis.save()
            
            return redirect('resume_builder', analysis_id=analysis.id)
        except ResumeAnalysis.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Analysis not found'
            }, status=404)
    
    return render(request, 'user_job_description.html')

def resume_builder(request, analysis_id):
    try:
        analysis = ResumeAnalysis.objects.get(id=analysis_id)
        context = {
            'analysis': analysis,
            'recommendations': analysis.recommendations or []
        }
        return render(request, 'resume_builder.html', context)
    except ResumeAnalysis.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Analysis not found'
        }, status=404)

def options(request):
    return render(request, 'options.html')

def jobs(request):
    return render(request, 'jobs.html')

# Functions from 2.py
def extract_text_from_pdf(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = "".join([page.extract_text() for page in reader.pages])
    return text

def get_recommendations(resume_text, job_text):
    openai.api_key = "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"  # Replace with your actual API key
    
    prompt = f"""
    You are an expert career advisor and resume consultant. Please analyze the following resume against the job description and provide specific, actionable recommendations.

    JOB DESCRIPTION:
    {job_text}

    RESUME CONTENT:
    {resume_text}

    For each recommendation, provide:
    1. Current content (what's in the resume)
    2. Direct implementation (the exact text to add to the resume)
    3. Reason and impact (why this change is needed and how it will improve the resume)

    Format each recommendation as a JSON object with these fields:
    - current_content: string (what's currently in the resume)
    - direct_implementation: string (the exact text to add/change)
    - reason_impact: string (why this change is needed and its impact)
    - category: string (one of: "skills", "experience", "formatting", "content")
    - section: string (where to add this in the resume: "skills", "experience", "projects", "education", "summary")

    Return a list of 5-7 most important recommendations. Each recommendation should be specific and include the exact text to add to the resume.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert career advisor and resume consultant with 20+ years of experience. Provide specific, actionable recommendations with exact text to add to the resume."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    
    try:
        recommendations = json.loads(response['choices'][0]['message']['content'])
        return recommendations
    except json.JSONDecodeError:
        return []

