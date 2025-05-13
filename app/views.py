from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from app.services.resume_parser import ResumeParser
from app.services.job_matcher import JobMatcher
from app.services.db_manager import DBManager
from app.services.indeed_api import fetch_jobs_from_api
from django.conf import settings
from .models import ResumeAnalysis, Resume, JobMatch, Job, MatchedJob
from openai import OpenAI
import os
import uuid
import tempfile
import logging
import PyPDF2
import requests
import json
from datetime import datetime
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import traceback

# Configure logging
logger = logging.getLogger(__name__)

# Create service instances
resume_parser = ResumeParser()
job_matcher = JobMatcher()
db_manager = DBManager()

@login_required
def fetch_jobs(request, resume_id):
    try:
        logger.info(f"Fetching jobs for resume ID: {resume_id}")
        
        # Get the resume
        resume = Resume.objects.get(id=resume_id, user=request.user)
        logger.info(f"Found resume: {resume}")
        
        # Initialize job matcher
        job_matcher = JobMatcher()
        
        # Get matched jobs
        matched_jobs = MatchedJob.objects.filter(resume=resume).select_related('job')
        logger.info(f"Found {matched_jobs.count()} existing matched jobs")
        
        if not matched_jobs.exists():
            logger.info("No existing matched jobs, fetching new ones")
            # If no matched jobs exist, fetch new ones
            jobs = job_matcher.match_jobs({
                'id': resume.id,
                'skills': resume.skills or [],
                'job_titles': resume.job_titles or []
            })
            
            logger.info(f"Fetched {len(jobs)} new jobs")
            
            # Create matched job records
            for job_data in jobs:
                try:
                    job = Job.objects.create(
                        title=job_data['title'],
                        company=job_data['company'],
                        location=job_data['location'],
                        description=job_data['description'],
                        apply_link=job_data['apply_link'],
                        required_skills=job_data['required_skills']
                    )
                    MatchedJob.objects.create(
                        resume=resume,
                        job=job,
                        match_score=job_data['match_score'],
                        matching_skills=job_data['matching_skills']
                    )
                except Exception as e:
                    logger.error(f"Error creating job record: {str(e)}")
                    continue
            
            matched_jobs = MatchedJob.objects.filter(resume=resume).select_related('job')
        
        # Format jobs for response
        jobs_data = []
        for matched_job in matched_jobs:
            job = matched_job.job
            jobs_data.append({
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'location': job.location,
                'description': job.description,
                'apply_link': job.apply_link,
                'required_skills': job.required_skills,
                'match_score': matched_job.match_score,
                'matching_skills': matched_job.matching_skills
            })
        
        logger.info(f"Returning {len(jobs_data)} jobs")
        return JsonResponse({
            'success': True,
            'jobs': jobs_data
        })
        
    except Resume.DoesNotExist:
        logger.error(f"Resume not found: {resume_id}")
        return JsonResponse({
            'success': False,
            'error': 'Resume not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in fetch_jobs: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)

@login_required
def home(request):
    return render(request, 'home.html')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@require_http_methods(["POST"])
@csrf_exempt
def upload_resume(request):
    if not request.FILES.get('resume'):
        return JsonResponse({
            'success': False,
            'error': 'No resume file provided'
        }, status=400)
    
    resume_file = request.FILES['resume']
    
    # Validate file size
    if resume_file.size > settings.MAX_FILE_SIZE:
        return JsonResponse({
            'success': False,
            'error': f'File size exceeds {settings.MAX_FILE_SIZE / (1024*1024)}MB limit'
        }, status=400)
    
    # Validate file type
    file_ext = os.path.splitext(resume_file.name)[1].lower()
    if file_ext not in settings.SUPPORTED_FILE_TYPES:
        return JsonResponse({
            'success': False,
            'error': f'Unsupported file type. Please upload one of: {", ".join(settings.SUPPORTED_FILE_TYPES)}'
        }, status=400)
    
    try:
        # Save resume file
        resume = Resume.objects.create(
            user=request.user if request.user.is_authenticated else None,
            file=resume_file
        )
        
        # Parse resume
        parsed_data = resume_parser.parse_resume(resume.file.path)
        
        if "error" in parsed_data:
            return JsonResponse({
                'success': False,
                'error': parsed_data["error"]
            }, status=400)
        
        # Update resume with parsed data
        resume.skills = parsed_data.get("skills", [])
        resume.job_titles = parsed_data.get("job_titles", [])
        resume.save()
        
        # Get location and limit from request
        location = request.POST.get('location', '')
        limit = min(int(request.POST.get('limit', 10)), settings.MAX_JOBS_PER_SEARCH)
        
        # Search for jobs
        jobs_data = fetch_jobs_from_api(parsed_data["skills"], location, limit)
        matched_jobs = job_matcher.match_jobs(
            parsed_data,
            jobs_data,
            top_n=limit
        )
        
        # Save job matches
        for job in matched_jobs:
            try:
                JobMatch.objects.create(
                    resume=resume,
                    job_title=job.get("title", "Unknown Position"),
                    company=job.get("company", "Unknown Company"),
                    location=job.get("location", "Unknown Location"),
                    description=job.get("description", ""),
                    url=job.get("apply_link", "#"),  # Use apply_link instead of url
                    match_score=job.get("match_score", 0.0)
                )
            except Exception as e:
                logger.error(f"Error creating job match: {str(e)}")
                continue
        
        return JsonResponse({
            'success': True,
            'resume_id': resume.id,
            'skills': parsed_data["skills"],
            'job_titles': parsed_data["job_titles"],
            'matched_jobs': matched_jobs
        })
        
    except Exception as e:
        logger.error(f"Error processing resume: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your resume. Please try again.'
        }, status=500)

@require_http_methods(["GET", "POST"])
@csrf_exempt
def analyze_job_match(request, job_id):
    try:
        logger.info(f"Analyzing job match for job_id: {job_id}")
        
        # Get the job match from database
        job_match = JobMatch.objects.get(id=job_id)
        resume = job_match.resume
        
        if not resume or not resume.skills:
            logger.error(f"No resume or skills found for job_id: {job_id}")
            return JsonResponse({
                'success': False,
                'error': 'Resume or skills not found'
            }, status=404)
        
        logger.info(f"Found resume with {len(resume.skills)} skills")
        
        # Get the full resume text
        resume_text = ""
        try:
            with open(resume.file.path, 'r', encoding='utf-8') as f:
                resume_text = f.read()
        except:
            # If we can't read the file, create a text representation from the parsed data
            resume_text = "\n".join([
                "Skills: " + ", ".join(resume.skills),
                "Job Titles: " + ", ".join(resume.job_titles)
            ])
        
        # Get improvement suggestions
        suggestions_response = job_matcher.get_improvement_suggestions(
            resume_text,
            job_match.description
        )
        
        if not suggestions_response.get('success'):
            logger.warning("No suggestions generated, using fallback suggestions")
            suggestions_response = {
                'success': True,
                'suggestions': [{
                    'category': 'General',
                    'section': 'General',
                    'current_content': 'No specific content found',
                    'direct_implementation': 'Please upload a resume to get specific suggestions',
                    'reason_impact': 'Resume analysis is required to provide improvement suggestions'
                }]
            }
        
        # Get the suggestions from the response
        suggestions = suggestions_response.get('suggestions', [])
        
        # Ensure suggestions is a list
        if isinstance(suggestions, dict):
            suggestions = [suggestions]
        elif not isinstance(suggestions, list):
            suggestions = []
            
        # Format suggestions to ensure they have all required fields
        formatted_suggestions = []
        for suggestion in suggestions:
            if isinstance(suggestion, dict):
                formatted_suggestion = {
                    'category': suggestion.get('category', 'General'),
                    'section': suggestion.get('section', 'General'),
                    'current_content': suggestion.get('current_content', ''),
                    'direct_implementation': suggestion.get('direct_implementation', ''),
                    'reason_impact': suggestion.get('reason_impact', '')
                }
                formatted_suggestions.append(formatted_suggestion)
        
        logger.info(f"Generated {len(formatted_suggestions)} improvement suggestions")
        
        return JsonResponse({
            'success': True,
            'suggestions': formatted_suggestions
        })
        
    except JobMatch.DoesNotExist:
        logger.error(f"Job match not found for job_id: {job_id}")
        return JsonResponse({
            'success': False,
            'error': 'Job not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error analyzing job match: {str(e)}")
        logger.exception("Full traceback:")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while analyzing the job match. Please try again.'
        }, status=500)

def fetch_jobs_from_api(skills: list, location: str, limit: int) -> list:
    """Fetch jobs from JSearch API"""
    try:
    
        # Create cache key
        cache_key = f"jobs_{hash(str(skills))}_{hash(location)}_{limit}"
        
        # Check cache
        cached_jobs = cache.get(cache_key)
        if cached_jobs:
            return cached_jobs
        
        # Prepare API request
        headers = {
            "X-RapidAPI-Key": settings.JSEARCH_API_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        # Search for jobs using top skills
        matched_jobs = []
        for skill in skills[:3]:  # Use top 3 skills to avoid too many API calls
            querystring = {
                "query": f"{skill} {location}" if location else skill,
                "page": "1",
                "num_pages": "1"
            }
            
            try:
                response = requests.get(
                    settings.JSEARCH_API_URL,
                    headers=headers,
                    params=querystring
                )
                response.raise_for_status()
                
                jobs_data = response.json()
                if jobs_data.get("data"):
                    for job in jobs_data["data"]:
                        matched_jobs.append({
                            "title": job.get("job_title", "Title not specified"),
                            "company": job.get("employer_name", "Company not specified"),
                            "location": f"{job.get('job_city', '')}, {job.get('job_country', '')}".strip(", "),
                            "description": job.get("job_description", ""),
                            "url": job.get("job_apply_link", "#")
                        })
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching jobs from API: {e}")
                continue
        
        # Cache results
        cache.set(cache_key, matched_jobs, settings.JOB_CACHE_TIMEOUT)
        
        return matched_jobs
    
    except Exception as e:
        logger.error(f"Error in fetch_jobs_from_api: {e}")
        return []

@login_required
def analyze_job_match_old(request, analysis_id):
    if request.method == 'POST':
        try:
            job_description = request.POST.get('job_description')
            if not job_description:
                return JsonResponse({
                    'error': 'Job description is required',
                    'status': 'error'
                }, status=400)

            analysis = ResumeAnalysis.objects.get(id=analysis_id)
            analysis.job_description = job_description

            # Extract text from PDF
            resume_text = extract_text_from_pdf(analysis.resume_file.path)
            
            # Get recommendations
            recommendations = get_recommendations(resume_text, job_description)
            analysis.set_recommendations(recommendations)
            analysis.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Analysis completed successfully',
                'recommendations': recommendations
            })

        except ResumeAnalysis.DoesNotExist:
            return JsonResponse({
                'error': 'Analysis not found',
                'status': 'error'
            }, status=404)
        except Exception as e:
            logger.error(f"Error analyzing job match: {e}")
            return JsonResponse({
                'error': 'Error analyzing job match. Please try again.',
                'status': 'error'
            }, status=500)

    return JsonResponse({
        'error': 'Invalid request method',
        'status': 'error'
    }, status=400)

def extract_text_from_pdf(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = "".join([page.extract_text() for page in reader.pages])
    return text

def get_recommendations(resume_text, job_text):
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key is not configured. Please set OPENAI_API_KEY in your environment variables.")
        return {
            "success": False,
            "recommendations": [],
            "error": "API_NOT_CONFIGURED"
        }

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

    try:
        # Create OpenAI client if not already defined at module level
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert career advisor and resume consultant with 20+ years of experience. Provide specific, actionable recommendations with exact text to add to the resume."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        recommendations = json.loads(response.choices[0].message.content)
        return {
            "success": True,
            "recommendations": recommendations,
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return {
            "success": False,
            "recommendations": [],
            "error": str(e)
        }

@require_http_methods(["POST"])
@csrf_exempt
def analyze_resume(request):
    """Handle direct resume analysis without a job ID"""
    try:
        logger.info("Starting direct resume analysis")
        
        if not request.FILES.get('resume'):
            return JsonResponse({
                'success': False,
                'error': 'No resume file provided'
            }, status=400)
        
        job_description = request.POST.get('job_description')
        if not job_description:
            return JsonResponse({
                'success': False,
                'error': 'Job description is required'
            }, status=400)
        
        # Save and parse resume
        resume_file = request.FILES['resume']
        resume = Resume.objects.create(
            user=request.user if request.user.is_authenticated else None,
            file=resume_file
        )
        
        # Parse resume
        parsed_data = resume_parser.parse_resume(resume.file.path)
        
        if "error" in parsed_data:
            return JsonResponse({
                'success': False,
                'error': parsed_data["error"]
            }, status=400)
        
        # Update resume with parsed data
        resume.skills = parsed_data.get("skills", [])
        resume.save()
        
        # Get improvement suggestions
        suggestions = job_matcher.get_improvement_suggestions(
            resume.skills,
            job_description
        )
        
        if not suggestions:
            logger.warning("No suggestions generated, using fallback suggestions")
            suggestions = job_matcher._generate_basic_suggestions(
                resume.skills,
                job_description
            )
        
        logger.info(f"Generated {len(suggestions)} improvement suggestions")
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"Error analyzing resume: {str(e)}")
        logger.exception("Full traceback:")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while analyzing the resume. Please try again.'
        }, status=500)

@require_http_methods(["POST"])
@csrf_exempt
def get_resume_suggestions(request):
    """Get AI-powered suggestions for improving a resume based on a job description"""
    try:
        if not request.FILES.get('resume'):
            return JsonResponse({
                'success': False,
                'error': 'No resume file provided'
            }, status=400)

        resume_file = request.FILES['resume']
        job_description = request.POST.get('job_description', '').strip()

        if not job_description:
            return JsonResponse({
                'success': False,
                'error': 'No job description provided'
            }, status=400)

        # Validate file size
        if resume_file.size > settings.MAX_FILE_SIZE:
            return JsonResponse({
                'success': False,
                'error': f'File size exceeds {settings.MAX_FILE_SIZE / (1024*1024)}MB limit'
            }, status=400)

        # Validate file type
        file_ext = os.path.splitext(resume_file.name)[1].lower()
        if file_ext not in settings.SUPPORTED_FILE_TYPES:
            return JsonResponse({
                'success': False,
                'error': f'Unsupported file type. Please upload one of: {", ".join(settings.SUPPORTED_FILE_TYPES)}'
            }, status=400)

        # Save resume to database
        resume = Resume.objects.create(
            user=request.user if request.user.is_authenticated else None,
            file=resume_file
        )

        # Save resume temporarily for text extraction
        temp_path = os.path.join(tempfile.gettempdir(), f"resume_{uuid.uuid4()}{file_ext}")
        with open(temp_path, 'wb+') as destination:
            for chunk in resume_file.chunks():
                destination.write(chunk)

        try:
            # Extract text from resume
            if file_ext == '.pdf':
                with open(temp_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    resume_text = ""
                    for page in pdf_reader.pages:
                        resume_text += page.extract_text()
            else:
                with open(temp_path, 'r', encoding='utf-8') as file:
                    resume_text = file.read()

            # Get suggestions using JobMatcher
            suggestions_response = job_matcher.get_improvement_suggestions(resume_text, job_description)

            if suggestions_response.get('success'):
                # Create ResumeAnalysis record
                analysis = ResumeAnalysis.objects.create(
                    resume=resume,
                    job_description=job_description
                )
                
                # Save the suggestions
                suggestions_text = suggestions_response.get('suggestions')
                
                # Try to parse JSON if it's a JSON string, otherwise use as is
                try:
                    if isinstance(suggestions_text, str) and (suggestions_text.startswith('[') or suggestions_text.startswith('{')):
                        suggestions_data = json.loads(suggestions_text)
                    else:
                        suggestions_data = {"text": suggestions_text}
                    
                    # Save using the model's method
                    analysis.set_recommendations(suggestions_data)
                    analysis.save()
                    
                    logger.info(f"Saved resume analysis with ID {analysis.id}")
                    
                    return JsonResponse({
                        'success': True,
                        'suggestions': suggestions_text,
                        'analysis_id': analysis.id
                    })
                except json.JSONDecodeError as e:
                    # If not valid JSON, save as plain text
                    analysis.set_recommendations({"text": suggestions_text})
                    analysis.save()
                    
                    logger.info(f"Saved resume analysis with ID {analysis.id} (plain text)")
                    
                    return JsonResponse({
                        'success': True,
                        'suggestions': suggestions_text,
                        'analysis_id': analysis.id
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': suggestions_response.get('error') or 'Failed to generate suggestions'
                }, status=500)

        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Error getting resume suggestions: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while analyzing your resume. Please try again.'
        }, status=500)

@require_http_methods(["GET"])
def get_stored_suggestions(request, analysis_id=None):
    """Retrieve previously generated resume suggestions from the database"""
    try:
        # If an analysis_id is provided, get that specific analysis
        if analysis_id:
            analysis = ResumeAnalysis.objects.get(id=analysis_id)
            recommendations = analysis.get_recommendations()
            
            return JsonResponse({
                'success': True,
                'analysis_id': analysis.id,
                'suggestions': recommendations,
                'job_description': analysis.job_description,
                'created_at': analysis.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # If no analysis_id is provided, get the most recent analyses
        else:
            # Get user's analyses if authenticated, otherwise get the most recent ones
            if request.user.is_authenticated:
                analyses = ResumeAnalysis.objects.filter(
                    resume__user=request.user
                ).order_by('-created_at')[:10]
            else:
                analyses = ResumeAnalysis.objects.all().order_by('-created_at')[:10]
            
            # Format the analyses data
            analyses_data = []
            for analysis in analyses:
                analyses_data.append({
                    'id': analysis.id,
                    'created_at': analysis.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'job_description': analysis.job_description[:100] + '...' if len(analysis.job_description) > 100 else analysis.job_description,
                    'has_recommendations': bool(analysis.recommendations)
                })
            
            return JsonResponse({
                'success': True,
                'analyses': analyses_data
            })
            
    except ResumeAnalysis.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Analysis with ID {analysis_id} not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error retrieving stored suggestions: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while retrieving the suggestions'
        }, status=500)

@login_required
def dashboard(request):
    """Render the dashboard page with user's resume and job matches."""
    try:
        # Get user's latest resume
        resume = Resume.objects.filter(user=request.user).order_by('-uploaded_at').first()
        
        # Get job matches for the resume
        jobs = []
        if resume:
            job_matches = JobMatch.objects.filter(resume=resume).order_by('-match_score')
            jobs = [{
                'id': match.id,
                'title': match.job_title,
                'company': match.company,
                'location': match.location,
                'job_type': 'Full-time',  # You might want to store this in the model
                'description': match.description,
                'match_score': match.match_score,
                'apply_link': match.url,
                'required_skills': resume.skills  # You might want to store this separately
            } for match in job_matches]
        
        return render(request, 'dashboard.html', {
            'resume': resume,
            'jobs': jobs
        })
    except Exception as e:
        logger.error(f"Error in dashboard view: {str(e)}")
        return render(request, 'dashboard.html', {
            'error': 'An error occurred while loading the dashboard.'
        })

@login_required
def resume_improvements(request, job_id):
    """Render the resume improvements page for a specific job."""
    try:
        # Get the job match
        job_match = JobMatch.objects.get(id=job_id, resume__user=request.user)
        
        # Get improvement suggestions
        suggestions = job_matcher.get_improvement_suggestions(
            job_match.resume.skills,
            job_match.description
        )
        
        if not suggestions:
            suggestions = job_matcher._generate_basic_suggestions(
                job_match.resume.skills,
                job_match.description
            )
        
        # Prepare job data
        job = {
            'id': job_match.id,
            'title': job_match.job_title,
            'company': job_match.company,
            'location': job_match.location,
            'job_type': 'Full-time',  # You might want to store this in the model
            'description': job_match.description,
            'apply_link': job_match.url,
            'required_skills': job_match.resume.skills  # You might want to store this separately
        }
        
        return render(request, 'resume_improvements.html', {
            'job': job,
            'suggestions': suggestions
        })
    except JobMatch.DoesNotExist:
        return render(request, 'resume_improvements.html', {
            'error': 'Job not found.'
        })
    except Exception as e:
        logger.error(f"Error in resume_improvements view: {str(e)}")
        return render(request, 'resume_improvements.html', {
            'error': 'An error occurred while loading the improvements.'
        })