# app/services/resume_parser.py
import os
import PyPDF2
import docx
import re
import spacy
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

class ResumeParser:
    def __init__(self):
        # Common technical skills to look for
        self.common_skills = {
            'languages': [
                'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Ruby', 'PHP', 'Swift',
                'Kotlin', 'Go', 'Rust', 'TypeScript', 'HTML', 'CSS', 'SQL'
            ],
            'frameworks': [
                'Django', 'Flask', 'FastAPI', 'Spring', 'React', 'Angular', 'Vue',
                'Node.js', 'Express', 'Laravel', '.NET', 'TensorFlow', 'PyTorch'
            ],
            'tools': [
                'Git', 'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'Linux',
                'Jenkins', 'JIRA', 'Confluence', 'Selenium', 'PostgreSQL', 'MongoDB'
            ],
            'concepts': [
                'API', 'REST', 'GraphQL', 'Microservices', 'CI/CD', 'Agile', 'Scrum',
                'DevOps', 'Machine Learning', 'Data Science', 'Cloud Computing'
            ]
        }
        
        self.edu_degrees = [
            "bachelor", "bs", "b.s.", "b.a.", "master", "ms", "m.s.", "m.a.", 
            "phd", "ph.d", "doctorate", "mba", "btech", "b.tech", "mtech", "m.tech",
            "bsc", "b.sc", "msc", "m.sc", "associate", "diploma", "certification"
        ]
        
        self.job_titles = [
            "software engineer", "software developer", "web developer", "frontend developer",
            "backend developer", "full stack developer", "data scientist", "data analyst",
            "data engineer", "machine learning engineer", "devops engineer", "cloud engineer",
            "product manager", "project manager", "ui/ux designer", "ux researcher",
            "qa engineer", "test engineer", "systems administrator", "network engineer",
            "security engineer", "database administrator", "business analyst", "sales manager",
            "marketing specialist", "content writer", "graphic designer", "hr manager"
        ]
        
    def parse_resume(self, file_path: str) -> Dict[str, Any]:
        """Parse resume file and extract relevant information"""
        try:
            file_ext = file_path.lower().split('.')[-1]
            
            if file_ext == 'pdf':
                text = self._read_pdf(file_path)
            elif file_ext in ['docx', 'doc']:
                text = self._read_docx(file_path)
            elif file_ext in ['txt', 'rtf']:
                text = self._read_text(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")

            # Process the text with spaCy
            doc = nlp(text)
            
            # Extract information
            result = {
                "full_text": text,
                "skills": self._extract_skills(text),
                "education": self._extract_education(doc),
                "experience": self._extract_experience(doc),
                "job_titles": self._extract_job_titles(doc),
                "summary": self._generate_summary(doc)
            }
            
            return result

        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            return {'error': str(e)}
    
    def _read_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            raise
    
    def _read_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            raise
    
    def _read_text(self, file_path: str) -> str:
        """Read text from TXT or RTF file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading text file: {e}")
            raise
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text"""
        found_skills = set()
        
        # Convert text to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Look for skills in each category
        for category, skills in self.common_skills.items():
            for skill in skills:
                # Create a regex pattern that matches the skill as a whole word
                pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    found_skills.add(skill)
        
        # Convert set to sorted list for consistent output
        return sorted(list(found_skills))
    
    def _extract_education(self, doc) -> List[Dict[str, str]]:
        """Extract education information"""
        education_list = []
        
        # Extract education section
        edu_section = self._extract_section(doc.text, ["education", "academic background"])
        
        if edu_section:
            # Split into potential degree entries (assuming one degree per line or paragraph)
            entries = re.split(r'\n\s*\n|\r\n\s*\r\n', edu_section)
            
            for entry in entries:
                # Try to identify degree
                degree = None
                for deg in self.edu_degrees:
                    if re.search(r'\b' + re.escape(deg) + r'\b', entry.lower()):
                        degree = deg
                        break
                
                # Try to identify university/institution
                institution = None
                university_match = re.search(r'(university|college|institute|school) of [\w\s]+|[\w\s]+ (university|college|institute|school)', entry, re.IGNORECASE)
                if university_match:
                    institution = university_match.group(0)
                
                # Try to identify dates
                years = re.findall(r'\b(19|20)\d{2}\b', entry)
                year_range = " - ".join(years) if years else None
                
                if degree or institution:
                    education_list.append({
                        "degree": degree,
                        "institution": institution,
                        "years": year_range,
                        "raw_text": entry.strip()
                    })
        
        return education_list
    
    def _extract_experience(self, doc) -> List[Dict[str, str]]:
        """Extract work experience information"""
        experience_list = []
        
        # Extract experience section
        exp_section = self._extract_section(doc.text, ["experience", "work experience", "employment history", "professional experience"])
        
        if exp_section:
            # Split into potential job entries
            entries = re.split(r'\n\s*\n|\r\n\s*\r\n', exp_section)
            
            for entry in entries:
                if len(entry.strip()) < 10:  # Skip very short entries
                    continue
                    
                # Try to identify company
                company = None
                lines = entry.split('\n')
                if lines and len(lines) > 0:
                    # First line often contains job title and company
                    company_match = re.search(r'(?:at|with|for)\s+([\w\s&]+)', lines[0])
                    if company_match:
                        company = company_match.group(1).strip()
                
                # Try to identify dates
                years = re.findall(r'\b(19|20)\d{2}\b', entry)
                date_range = None
                if years:
                    if len(years) >= 2:
                        date_range = f"{years[0]} - {years[-1]}"
                    else:
                        date_range = f"{years[0]} - Present"
                
                # Try to identify job title
                job_title = None
                for title in self.job_titles:
                    if re.search(r'\b' + re.escape(title) + r'\b', entry.lower()):
                        job_title = title
                        break
                
                experience_list.append({
                    "title": job_title,
                    "company": company,
                    "date_range": date_range,
                    "description": entry.strip()
                })
        
        return experience_list
    
    def _extract_job_titles(self, doc) -> List[str]:
        """Extract job titles from resume"""
        titles = []
        text_lower = doc.text.lower()
        
        for title in self.job_titles:
            if re.search(r'\b' + re.escape(title) + r'\b', text_lower):
                titles.append(title)
        
        return titles
    
    def _extract_section(self, text: str, section_headers: List[str]) -> str:
        """Extract text from a specific section"""
        text_lower = text.lower()
        
        for header in section_headers:
            # Pattern for section header with various formatting
            pattern = r'(?i)(?:^|\n)(?:[\*\-\s]*)({})([\s\:]*)\n'.format(re.escape(header))
            match = re.search(pattern, text_lower)
            
            if match:
                start_idx = match.end()
                
                # Find the next section header
                next_section_pattern = r'(?i)(?:^|\n)(?:[\*\-\s]*)(' + '|'.join([re.escape(h) for h in section_headers if h != header]) + r')([\s\:]*)\n'
                next_match = re.search(next_section_pattern, text_lower[start_idx:])
                
                if next_match:
                    end_idx = start_idx + next_match.start()
                    return text[start_idx:end_idx].strip()
                else:
                    # If no next section, take the rest of the text
                    return text[start_idx:].strip()
        
        return ""
    
    def _generate_summary(self, doc) -> str:
        """Generate a brief summary of the candidate's profile"""
        # Extract the first 500 characters as a simple summary
        # In a real implementation, you might want to use more sophisticated summarization techniques
        text = doc.text.strip()
        summary = text[:500] + "..." if len(text) > 500 else text
        return summary
