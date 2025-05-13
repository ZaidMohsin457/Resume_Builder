# app/services/job_matcher.py
import re
from typing import List, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from django.core.cache import cache
import logging
from openai import OpenAI
from django.conf import settings
import json
import traceback

logger = logging.getLogger(__name__)

class JobMatcher:
    def __init__(self):
        """Initialize the job matching service"""
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),  # Use both unigrams and bigrams
            max_features=10000
        )
        # Configure OpenAI API
        if not settings.OPENAI_API_KEY:
            logger.error("OpenAI API key is not configured. Please set OPENAI_API_KEY in your environment variables.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.model = "gpt-3.5-turbo"
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {e}")
                self.client = None
        
    def match_jobs(self, resume_data: Dict[str, Any], job_listings: List[Dict[str, Any]], top_n: int = 20) -> List[Dict[str, Any]]:
        """Match resume to job listings and return top matches
        
        Args:
            resume_data: Parsed resume data
            job_listings: List of job listings
            top_n: Number of top matches to return
            
        Returns:
            List of top matching jobs with score
        """
        try:
            logger.info(f"Starting job matching for resume ID: {resume_data.get('id', 'Unknown')}")
            
            # Get resume skills
            skills = resume_data.get("skills", [])
            logger.info(f"Resume skills: {skills}")
            
            # Fetch jobs from API
            jobs = job_listings
            logger.info(f"Fetched {len(jobs)} jobs from API")
            
            # Calculate match scores
            matched_jobs = []
            for job in jobs:
                try:
                    # Extract required skills from job description
                    required_skills = self._extract_skills_from_description(job['description'])
                    logger.info(f"Required skills for {job['title']}: {required_skills}")
                    
                    # Calculate match score
                    matching_skills = [skill for skill in skills if skill.lower() in [s.lower() for s in required_skills]]
                    match_score = len(matching_skills) / len(required_skills) if required_skills else 0
                    
                    matched_jobs.append({
                        'title': job['title'],
                        'company': job['company'],
                        'location': job['location'],
                        'description': job['description'],
                        'apply_link': job['url'],
                        'required_skills': required_skills,
                        'match_score': match_score,
                        'matching_skills': matching_skills
                    })
                except Exception as e:
                    logger.error(f"Error processing job {job.get('title', 'Unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Successfully matched {len(matched_jobs)} jobs")
            return matched_jobs
            
        except Exception as e:
            logger.error(f"Error in match_jobs: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _extract_skills_from_description(self, description):
        """Extract skills from job description using basic keyword matching"""
        # Common programming languages and technologies
        common_skills = [
            'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php',
            'html', 'css', 'react', 'angular', 'vue', 'node.js', 'django',
            'flask', 'spring', 'express', 'sql', 'nosql', 'mongodb',
            'postgresql', 'mysql', 'aws', 'azure', 'gcp', 'docker',
            'kubernetes', 'git', 'agile', 'scrum', 'ci/cd'
        ]
        
        # Convert description to lowercase for case-insensitive matching
        desc_lower = description.lower()
        
        # Find matching skills
        found_skills = []
        for skill in common_skills:
            if skill in desc_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def _create_resume_profile(self, resume_data: Dict[str, Any]) -> str:
        """Create a text profile from resume data for matching
        
        Args:
            resume_data: Parsed resume data
            
        Returns:
            String representation of resume for text matching
        """
        profile_parts = []
        
        # Add skills (3x to give them more weight)
        skills = resume_data.get("skills", [])
        profile_parts.extend(skills * 3)
        
        # Add job titles (2x to give them more weight)
        job_titles = resume_data.get("job_titles", [])
        profile_parts.extend(job_titles * 2)
        
        # Add experience
        experience = resume_data.get("experience", [])
        for exp in experience:
            if exp.get("title"):
                profile_parts.append(exp["title"])
            if exp.get("description"):
                profile_parts.append(exp["description"])
        
        # Add education
        education = resume_data.get("education", [])
        for edu in education:
            if edu.get("degree"):
                profile_parts.append(edu["degree"])
            if edu.get("raw_text"):
                profile_parts.append(edu["raw_text"])
        
        return " ".join(profile_parts)
    
    def _create_job_profile(self, job: Dict[str, Any]) -> str:
        """Create a text profile from job listing for matching
        
        Args:
            job: Job listing data
            
        Returns:
            String representation of job for text matching
        """
        profile_parts = []
        
        # Add job title (3x to give it more weight)
        if "title" in job and job["title"]:
            profile_parts.extend([job["title"]] * 3)
        
        # Add company name
        if "company" in job and job["company"]:
            profile_parts.append(job["company"])
        
        # Add job description
        if "description" in job and job["description"]:
            profile_parts.append(job["description"])
        
        # Add seniority and employment type
        if "seniority_level" in job and job["seniority_level"]:
            profile_parts.append(job["seniority_level"])
            
        if "employment_type" in job and job["employment_type"]:
            profile_parts.append(job["employment_type"])
        
        return " ".join(profile_parts)
    
    def _find_matching_skills(self, resume_skills: List[str], job_description: str) -> List[str]:
        """Find skills from the resume that match the job description
        
        Args:
            resume_skills: List of skills from the resume
            job_description: Job description text
            
        Returns:
            List of matching skills
        """
        matching_skills = []
        job_description_lower = job_description.lower()
        
        for skill in resume_skills:
            # Check if skill appears as a whole word in the job description
            if re.search(r'\b' + re.escape(skill.lower()) + r'\b', job_description_lower):
                matching_skills.append(skill)
        
        return matching_skills
    
    def enrich_job_matches(self, matched_jobs: List[Dict[str, Any]], resume_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add additional matching information to enhance user experience
        
        Args:
            matched_jobs: List of matched jobs with scores
            resume_data: Parsed resume data
            
        Returns:
            Enhanced job matches with additional insights
        """
        for job in matched_jobs:
            # Calculate percentage match score (0-100)
            job["match_percentage"] = round(job["match_score"] * 100)
            
            # Identify missing skills (skills mentioned in job but not in resume)
            if "description" in job and job["description"]:
                job_skills = self._extract_potential_skills(job["description"])
                resume_skills = resume_data.get("skills", [])
                
                missing_skills = [skill for skill in job_skills 
                                 if skill not in resume_skills and
                                 not any(re.search(r'\b' + re.escape(skill) + r'\b', s, re.IGNORECASE) for s in resume_skills)]
                
                job["missing_skills"] = missing_skills[:5]  # Limit to top 5 missing skills
            
            # Add role compatibility comment
            job["compatibility_note"] = self._generate_compatibility_note(
                job.get("match_percentage", 0),
                job.get("matching_skills", []),
                job.get("missing_skills", [])
            )
        
        return matched_jobs
    
    def calculate_match_score(self, skills: List[str], job_description: str) -> float:
        """Calculate match score between skills and job description
        
        Args:
            skills: List of skills from resume
            job_description: Job description text
            
        Returns:
            Match score between 0 and 1
        """
        if not skills or not job_description:
            return 0.0
            
        # Convert skills list to text
        skills_text = " ".join(skills)
        
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer()
        try:
            tfidf_matrix = vectorizer.fit_transform([skills_text, job_description])
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(similarity[0][0])
        except:
            return 0.0
    
    def get_improvement_suggestions(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """Get AI-powered suggestions for improving resume based on job description"""
        if not self.client:
            logger.error("OpenAI client not configured")
            return {
                "success": False,
                "suggestions": [],
                "error": "API_NOT_CONFIGURED"
            }
            
        try:
            # Log the input lengths
            logger.info(f"Resume text length: {len(resume_text)}")
            logger.info(f"Job description length: {len(job_description)}")
            
            # Prepare the prompt for OpenAI
            prompt = f"""
            You are a professional resume analyst. Analyze the following resume against the job description and provide EXACTLY 3 specific suggestions for improvement.
            
            Resume:
            {resume_text}
            
            Job Description:
            {job_description}
            
            Provide your response as a JSON array of exactly 3 suggestions. Each suggestion must be a JSON object with these exact fields:
            - category: one of ["skills", "experience", "content"]
            - section: one of ["skills", "experience", "projects", "education", "summary"]
            - current_content: what's currently in the resume (exact text)
            - direct_implementation: the exact text to copy-paste into the resume (be specific and detailed)
            - reason_impact: why this change is needed and its impact

            Requirements:
            1. You MUST return a valid JSON array with EXACTLY 3 suggestions
            2. Each suggestion MUST be unique and cover a different aspect of the resume
            3. Each suggestion must be specific and actionable:
               - For skills: List exact technologies, tools, or methodologies to add
               - For experience: Provide exact bullet points to add or replace
               - For content: Provide exact text to add or modify
            4. The direct_implementation field must contain text that can be directly copied and pasted into the resume
            5. Focus on:
               - Missing required skills or qualifications (be specific)
               - Areas where experience could be better emphasized (with exact text)
               - Specific formatting or content suggestions (with exact implementation)
            6. Each suggestion must be tailored to the specific job description
            7. DO NOT include generic suggestions
            8. Each suggestion must provide concrete, actionable improvements
            9. Ensure each suggestion has a clear impact statement that ties to the job requirements
            10. The direct_implementation must be complete, copy-pasteable text

            Example format:
            [
                {{
                    "category": "skills",
                    "section": "skills",
                    "current_content": "AWS, Cloud Computing",
                    "direct_implementation": "Add these specific skills: AWS Solutions Architecture Design, Customer Advocacy Strategies in Cloud Migration Projects",
                    "reason_impact": "The job description requires expertise in designing customer-centric cloud solutions and driving successful business outcomes through cloud migration strategies. Adding these skills will showcase your ability to meet those requirements."
                }},
                {{
                    "category": "experience",
                    "section": "experience",
                    "current_content": "Developed cloud infrastructure using AWS",
                    "direct_implementation": "Replace with: 'Led a team of 5 engineers in designing and implementing a scalable cloud infrastructure using AWS services (EC2, S3, Lambda, RDS), resulting in 40% cost reduction and 99.9% uptime. Successfully migrated 3 enterprise applications to AWS, reducing deployment time by 60% and improving system reliability.'",
                    "reason_impact": "This detailed experience demonstrates your leadership in cloud architecture and quantifiable achievements in cost reduction and system reliability, which are key requirements for the role."
                }},
                {{
                    "category": "content",
                    "section": "summary",
                    "current_content": "Cloud Engineer with AWS experience",
                    "direct_implementation": "Replace with: 'Senior Cloud Architect with 5+ years of experience in AWS cloud solutions and infrastructure design. Proven track record in leading cloud migration projects and optimizing cloud costs. Expert in designing scalable, secure, and cost-effective cloud architectures. Successfully delivered 10+ enterprise cloud solutions with an average cost reduction of 35%.'",
                    "reason_impact": "A more detailed summary that highlights your cloud architecture expertise, quantifiable achievements, and leadership experience will better position you for this senior role."
                }}
            ]
            """
            
            logger.info("Making API call to OpenAI...")
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional resume analyst. You MUST return a valid JSON array with exactly 3 suggestions. Each suggestion must be unique, specific, and actionable. The direct_implementation must be complete, copy-pasteable text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                presence_penalty=0.6,
                frequency_penalty=0.6,
                response_format={ "type": "json_object" }  # Force JSON response
            )
            
            # Extract and parse the suggestions
            suggestions_text = response.choices[0].message.content.strip()
            logger.info(f"Raw API response: {suggestions_text[:200]}...")
            
            try:
                # Clean up the response text
                if suggestions_text.startswith('```'):
                    lines = suggestions_text.split('\n')
                    if len(lines) > 2:
                        suggestions_text = '\n'.join(lines[1:-1])
                        logger.info("Removed markdown code block formatting")
                
                # Try to parse the suggestions as JSON
                try:
                    suggestions = json.loads(suggestions_text)
                    # Handle case where response is a single object instead of array
                    if isinstance(suggestions, dict):
                        if "suggestions" in suggestions:
                            suggestions = suggestions["suggestions"]
                        else:
                            suggestions = [suggestions]
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response")
                    return {
                        "success": False,
                        "suggestions": [],
                        "error": "Invalid JSON response"
                    }
                
                # Validate and format suggestions
                validated_suggestions = []
                seen_categories = set()  # Track unique categories
                
                for i, suggestion in enumerate(suggestions):
                    if isinstance(suggestion, dict):
                        category = suggestion.get("category", "General").strip('`')
                        
                        # Skip if we've already seen this category
                        if category in seen_categories:
                            continue
                            
                        seen_categories.add(category)
                        
                        # Clean up any markdown formatting in the values
                        validated_suggestion = {
                            "category": category,
                            "section": suggestion.get("section", "General").strip('`'),
                            "current_content": suggestion.get("current_content", "").strip('`'),
                            "direct_implementation": suggestion.get("direct_implementation", "").strip('`'),
                            "reason_impact": suggestion.get("reason_impact", "").strip('`')
                        }
                        
                        # Skip generic suggestions
                        if "review and enhance" in validated_suggestion["direct_implementation"].lower():
                            continue
                            
                        # Log each suggestion for debugging
                        logger.info(f"Suggestion {i+1}: {json.dumps(validated_suggestion, indent=2)}")
                        validated_suggestions.append(validated_suggestion)
                    else:
                        logger.warning(f"Invalid suggestion format: {suggestion}")
                
                if not validated_suggestions:
                    logger.warning("No valid suggestions found after validation")
                    # Generate specific fallback suggestions based on common resume improvements
                    fallback_suggestions = [
                        {
                            "category": "skills",
                            "section": "skills",
                            "current_content": "Current technical skills",
                            "direct_implementation": "Add these specific skills: AWS Solutions Architecture Design, Customer Advocacy Strategies in Cloud Migration Projects, Infrastructure as Code (Terraform), CI/CD Pipeline Design, Cloud Cost Optimization",
                            "reason_impact": "These specific skills demonstrate your expertise in cloud architecture and customer-focused solutions, which are key requirements for the role."
                        },
                        {
                            "category": "experience",
                            "section": "experience",
                            "current_content": "Current work experience",
                            "direct_implementation": "Add this experience: 'Led a team of 5 engineers in designing and implementing a scalable cloud infrastructure using AWS services (EC2, S3, Lambda, RDS), resulting in 40% cost reduction and 99.9% uptime. Successfully migrated 3 enterprise applications to AWS, reducing deployment time by 60% and improving system reliability.'",
                            "reason_impact": "This detailed experience demonstrates your leadership in cloud architecture and quantifiable achievements in cost reduction and system reliability."
                        },
                        {
                            "category": "content",
                            "section": "summary",
                            "current_content": "Current summary",
                            "direct_implementation": "Replace with: 'Senior Cloud Architect with 5+ years of experience in AWS cloud solutions and infrastructure design. Proven track record in leading cloud migration projects and optimizing cloud costs. Expert in designing scalable, secure, and cost-effective cloud architectures. Successfully delivered 10+ enterprise cloud solutions with an average cost reduction of 35%.'",
                            "reason_impact": "A more detailed summary that highlights your cloud architecture expertise, quantifiable achievements, and leadership experience will better position you for this senior role."
                        }
                    ]
                    logger.info("Using specific fallback suggestions")
                    return {
                        "success": True,
                        "suggestions": fallback_suggestions,
                        "error": None
                    }
                
                # Ensure we have exactly 3 suggestions
                while len(validated_suggestions) < 3:
                    # Add specific suggestions based on missing categories
                    missing_categories = {"skills", "experience", "content"} - seen_categories
                    if missing_categories:
                        category = missing_categories.pop()
                        if category == "skills":
                            validated_suggestions.append({
                                "category": "skills",
                                "section": "skills",
                                "current_content": "Technical skills section",
                                "direct_implementation": "Add these specific skills: AWS Solutions Architecture Design, Customer Advocacy Strategies in Cloud Migration Projects, Infrastructure as Code (Terraform), CI/CD Pipeline Design, Cloud Cost Optimization",
                                "reason_impact": "These specific skills demonstrate your expertise in cloud architecture and customer-focused solutions, which are key requirements for the role."
                            })
                        elif category == "experience":
                            validated_suggestions.append({
                                "category": "experience",
                                "section": "experience",
                                "current_content": "Work experience section",
                                "direct_implementation": "Add this experience: 'Led a team of 5 engineers in designing and implementing a scalable cloud infrastructure using AWS services (EC2, S3, Lambda, RDS), resulting in 40% cost reduction and 99.9% uptime. Successfully migrated 3 enterprise applications to AWS, reducing deployment time by 60% and improving system reliability.'",
                                "reason_impact": "This detailed experience demonstrates your leadership in cloud architecture and quantifiable achievements in cost reduction and system reliability."
                            })
                        else:
                            validated_suggestions.append({
                                "category": "content",
                                "section": "summary",
                                "current_content": "Professional summary",
                                "direct_implementation": "Replace with: 'Senior Cloud Architect with 5+ years of experience in AWS cloud solutions and infrastructure design. Proven track record in leading cloud migration projects and optimizing cloud costs. Expert in designing scalable, secure, and cost-effective cloud architectures. Successfully delivered 10+ enterprise cloud solutions with an average cost reduction of 35%.'",
                                "reason_impact": "A more detailed summary that highlights your cloud architecture expertise, quantifiable achievements, and leadership experience will better position you for this senior role."
                            })
                
                # Limit to exactly 3 suggestions
                validated_suggestions = validated_suggestions[:3]
                
                logger.info(f"Returning {len(validated_suggestions)} validated suggestions")
                return {
                    "success": True,
                    "suggestions": validated_suggestions,
                    "error": None
                }
                
            except Exception as e:
                logger.error(f"Error parsing suggestions: {e}")
                logger.error(f"Failed to parse suggestions text: {suggestions_text}")
                return {
                    "success": False,
                    "suggestions": [],
                    "error": str(e)
                }
            
        except Exception as e:
            logger.error(f"Error getting improvement suggestions: {e}")
            logger.exception("Full traceback:")
            return {
                "success": False,
                "suggestions": [],
                "error": str(e)
            }
    
    def _extract_potential_skills(self, text: str) -> List[str]:
        """Extract potential skills from job description
        
        Args:
            text: Job description text
            
        Returns:
            List of potential skills
        """
        # Common technical skills to look for in job descriptions
        common_skills = [
            "python", "java", "javascript", "typescript", "html", "css", "react", "angular", "vue", 
            "node.js", "express", "django", "flask", "fastapi", "ruby", "php", "laravel", "sql", 
            "mysql", "postgresql", "mongodb", "firebase", "redis", "aws", "azure", "gcp", "docker", 
            "kubernetes", "terraform", "ci/cd", "jenkins", "git", "github", "gitlab", "bitbucket",
            "agile", "scrum", "kanban", "jira", "rest api", "graphql", "machine learning", "tensorflow", 
            "pytorch", "keras", "scikit-learn", "pandas", "numpy", "data science", "nlp", "computer vision",
            "r", "tableau", "power bi", "excel", "microsoft office", "photoshop", "illustrator",
            "figma", "sketch", "adobe xd", "ui/ux", "product management", "project management",
            "salesforce", "sap", "oracle", "java spring", "hibernate", "c++", "c#", ".net", "asp.net",
            "swift", "ios", "android", "kotlin", "flutter", "dart", "golang", "rust", "scala"
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in common_skills:
            # Look for whole word matches only
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                found_skills.append(skill)
                
        return found_skills
    
    def _generate_compatibility_note(self, match_percentage: int, matching_skills: List[str], missing_skills: List[str]) -> str:
        """Generate a note about job compatibility
        
        Args:
            match_percentage: Match percentage score
            matching_skills: List of matching skills
            missing_skills: List of missing skills
            
        Returns:
            Compatibility note string
        """
        if match_percentage >= 80:
            note = "Strong match! Your background aligns well with this position."
        elif match_percentage >= 60:
            note = "Good match with your qualifications."
        elif match_percentage >= 40:
            note = "Moderate match. You have some relevant skills for this role."
        else:
            note = "This role may require additional skills beyond your current resume."
        
        # Add skill details if available
        if matching_skills:
            note += f" Your skills in {', '.join(matching_skills[:3])} are relevant."
            
        if missing_skills:
            note += f" Consider developing skills in {', '.join(missing_skills[:3])}."
            
        return note
