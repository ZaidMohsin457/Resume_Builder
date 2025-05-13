import requests
import logging
from typing import List, Dict
from app.config.settings import settings
from app.services.keyword_processor import KeywordProcessor

logger = logging.getLogger(__name__)
keyword_processor = KeywordProcessor()

def fetch_jobs_from_api(keywords: List[str], location: str = "", limit: int = 10) -> List[Dict]:
    """
    Fetch jobs from JSearch API using intelligent keyword processing
    """
    if not settings.rapidapi_key:
        logger.error("❌ RapidAPI key is not configured")
        return []

    # Process keywords into intelligent queries
    queries = keyword_processor.process_keywords(keywords)
    logger.info(f"🔍 Generated intelligent queries: {queries}")
    
    all_jobs = []
    seen_jobs = set()  # To track unique jobs

    for query in queries:
        logger.info(f"🌐 Fetching jobs for query: {query}")
        
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "x-rapidapi-key": settings.rapidapi_key,
            "x-rapidapi-host": "jsearch.p.rapidapi.com"
        }

        params = {
            "query": query,
            "location": location or "Remote",
            "page": "1",
            "num_pages": "1"
        }

        try:
            logger.info(f"📡 Making request to JSearch API with params: {params}")
            response = requests.get(url, headers=headers, params=params)
            
            # Log response status and headers for debugging
            logger.info(f"📥 Response status: {response.status_code}")
            logger.info(f"📥 Response headers: {response.headers}")
            
            response.raise_for_status()
            data = response.json()
            
            # Log the structure of the response
            logger.info(f"📦 Response keys: {data.keys() if isinstance(data, dict) else 'Not a dictionary'}")

            job_results = data.get("data", [])
            logger.info(f"📊 Found {len(job_results)} jobs in response")
            
            # Process and deduplicate jobs
            for job in job_results:
                job_id = job.get("job_id", "") or job.get("job_google_link", "")
                if job_id not in seen_jobs:
                    seen_jobs.add(job_id)
                    processed_job = {
                        "title": job.get("job_title"),
                        "company": job.get("employer_name"),
                        "location": job.get("job_city") or job.get("job_country"),
                        "link": job.get("job_apply_link") or job.get("job_google_link"),
                        "description": job.get("job_description", "")[:500] + "...",  # Truncate long descriptions
                        "salary": job.get("job_salary") or "Not specified",
                        "posted_at": job.get("job_posted_at_datetime_utc", ""),
                        "job_type": job.get("job_employment_type", "Not specified"),
                        "matched_query": query  # Add which query matched this job
                    }
                    all_jobs.append(processed_job)
                
                if len(all_jobs) >= limit:
                    break
            
            if len(all_jobs) >= limit:
                break

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"❌ HTTP error occurred: {http_err}")
            logger.error(f"❌ Response content: {response.text if 'response' in locals() else 'No response'}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"❌ Request error occurred: {req_err}")
        except ValueError as json_err:
            logger.error(f"❌ JSON parsing error: {json_err}")
            logger.error(f"❌ Response content: {response.text if 'response' in locals() else 'No response'}")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")

    logger.info(f"✅ Retrieved {len(all_jobs)} unique jobs from JSearch API")
    return all_jobs[:limit]