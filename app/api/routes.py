import os
import uuid
import tempfile
from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional

from app.models.models import (
    ResumeModel, JobModel, JobMatchesResponse, UserModel,
    ResumeUploadResponse, JobSearchRequest, ErrorResponse
)
from app.services.resume_parser import ResumeParser
from app.services.job_matcher import JobMatcher
from app.services.db_manager import DBManager
from app.config.settings import settings
from app.services.indeed_api import fetch_jobs_from_api
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create service instances
resume_parser = ResumeParser()
job_matcher = JobMatcher()

# Database manager dependency
def get_db():
    db_manager = DBManager()
    try:
        yield db_manager
    finally:
        pass

# Generate a user ID if not provided
def get_user_id(user_id: Optional[str] = Form(None)):
    return user_id or str(uuid.uuid4())

@router.post("/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
    resume_file: UploadFile = File(...),
    db: DBManager = Depends(get_db)
):
    try:
        logger.info(f"Processing resume upload for user {user_id}")

        file_ext = os.path.splitext(resume_file.filename)[1].lower()
        if file_ext not in [".pdf", ".docx", ".doc", ".txt", ".rtf"]:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, DOCX, DOC, TXT, or RTF file.")

        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
            temp_file_path = temp_file.name
            content = await resume_file.read()
            temp_file.write(content)

        try:
            resume_data = resume_parser.parse_resume(temp_file_path)
            if "error" in resume_data:
                raise HTTPException(status_code=400, detail=resume_data["error"])

            resume_data["user_id"] = user_id
            resume_id = db.save_resume(user_id, resume_data)
            background_tasks.add_task(os.unlink, temp_file_path)

            return ResumeUploadResponse(
                resume_id=resume_id,
                user_id=user_id,
                message="Resume uploaded and parsed successfully",
                skills=resume_data.get("skills", []),
                job_titles=resume_data.get("job_titles", [])
            )

        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            background_tasks.add_task(os.unlink, temp_file_path)
            raise HTTPException(status_code=500, detail=f"Error parsing resume: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing resume upload: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing resume upload: {str(e)}")

@router.post("/search-jobs", response_model=JobMatchesResponse)
async def search_jobs(
    request: JobSearchRequest,
    db: DBManager = Depends(get_db)
):
    try:
        logger.info(f"Processing job search for resume {request.resume_id}")

        resume_data = db.get_resume(request.resume_id)
        if not resume_data:
            raise HTTPException(status_code=404, detail="Resume not found")

        search_keywords = request.keywords or resume_data.get("skills", [])
        if not search_keywords and resume_data.get("job_titles"):
            search_keywords = resume_data.get("job_titles", [])
        if not search_keywords:
            raise HTTPException(status_code=400, detail="No search keywords found")

        if settings.use_mock_data:
            logger.info("Using mock job data")
            job_listings = job_matcher.get_mock_jobs(search_keywords[:5], request.location)
        else:
            logger.info("Fetching jobs from Indeed API...")
            job_listings = fetch_jobs_from_api(search_keywords[:5], request.location)

        if not job_listings:
            raise HTTPException(status_code=404, detail="No job listings found")

        job_ids = db.save_jobs(job_listings)
        matched_jobs = job_matcher.match_jobs(resume_data, job_listings, top_n=request.limit)
        enriched_matches = job_matcher.enrich_job_matches(matched_jobs, resume_data)
        match_id = db.save_matches(request.user_id, request.resume_id, enriched_matches)

        return JobMatchesResponse(
            match_id=match_id,
            user_id=request.user_id,
            resume_id=request.resume_id,
            matches=enriched_matches,
            created_at=enriched_matches[0].get("created_at") if enriched_matches else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing job search: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing job search: {str(e)}")

@router.get("/matches/{match_id}", response_model=JobMatchesResponse)
async def get_matches(match_id: str, db: DBManager = Depends(get_db)):
    try:
        matches = db.get_matches(match_id)
        if not matches:
            raise HTTPException(status_code=404, detail="Matches not found")

        return JobMatchesResponse(**matches)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving matches: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving matches: {str(e)}")

@router.get("/user/{user_id}/matches", response_model=JobMatchesResponse)
async def get_user_matches(user_id: str, db: DBManager = Depends(get_db)):
    try:
        matches = db.get_matches_by_user(user_id)
        if not matches:
            raise HTTPException(status_code=404, detail="No matches found for this user")

        return JobMatchesResponse(**matches)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user matches: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user matches: {str(e)}")

@router.get("/user/{user_id}/resume", response_model=ResumeModel)
async def get_user_resume(user_id: str, db: DBManager = Depends(get_db)):
    try:
        resume = db.get_resume_by_user(user_id)
        if not resume:
            raise HTTPException(status_code=404, detail="No resume found for this user")

        return ResumeModel(**resume)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user resume: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user resume: {str(e)}")

@router.get("/health")
async def health_check():
    return {"status": "OK", "message": "API is running"}
