# app/services/db_manager.py
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection
        
        Args:
            db_path: SQLite database path
        """
        # Get database path from environment or use default
        self.db_path = db_path or os.getenv("SQLITE_DB_PATH", "db.sqlite3")
        
        # Make sure the path is absolute
        if not os.path.isabs(self.db_path):
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.db_path = os.path.join(base_dir, self.db_path)
        
        self.conn = None
        
        # Connect to database
        self._connect()
        
    def _connect(self):
        """Connect to SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = 1")
            # Return rows as dictionaries
            self.conn.row_factory = sqlite3.Row
            
            # Create tables if they don't exist
            self._create_tables()
            
            logger.info(f"Connected to SQLite database: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error connecting to SQLite: {e}")
            raise
    
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Create resumes table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resume_data TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES auth_user(id)
        )
        ''')
        
        # Create jobs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            description TEXT,
            location TEXT,
            job_data TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        ''')
        
        # Create matches table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resume_id INTEGER NOT NULL,
            matches_data TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES auth_user(id),
            FOREIGN KEY (resume_id) REFERENCES resumes(id)
        )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)')
        
        self.conn.commit()
    
    def save_resume(self, user_id: str, resume_data: Dict[str, Any]) -> str:
        """Save parsed resume data to database
        
        Args:
            user_id: User identifier
            resume_data: Parsed resume data
            
        Returns:
            ID of saved resume document
        """
        try:
            # Add metadata
            resume_data["user_id"] = user_id
            now = datetime.now().isoformat()
            resume_data["created_at"] = now
            resume_data["updated_at"] = now
            
            # Insert into database
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO resumes (user_id, resume_data, created_at, updated_at) VALUES (?, ?, ?, ?)',
                (
                    user_id,
                    json.dumps(resume_data),
                    now,
                    now
                )
            )
            self.conn.commit()
            resume_id = str(cursor.lastrowid)
            logger.info(f"Saved resume for user {user_id} with ID {resume_id}")
            
            return resume_id
            
        except Exception as e:
            logger.error(f"Error saving resume: {e}")
            raise
    
    def get_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Get resume data by ID
        
        Args:
            resume_id: Resume document ID
            
        Returns:
            Resume data or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM resumes WHERE id = ?', (resume_id,))
            row = cursor.fetchone()
            
            if row:
                resume = dict(row)
                # Parse the JSON data
                resume_data = json.loads(resume['resume_data'])
                resume_data['id'] = resume['id']
                return resume_data
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving resume {resume_id}: {e}")
            return None
    
    def get_resume_by_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get latest resume for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Latest resume data or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT * FROM resumes WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                resume = dict(row)
                # Parse the JSON data
                resume_data = json.loads(resume['resume_data'])
                resume_data['id'] = resume['id']
                return resume_data
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving resume for user {user_id}: {e}")
            return None
    
    def save_jobs(self, jobs: List[Dict[str, Any]]) -> List[str]:
        if not jobs:
            return []
        
        try:
            # Add timestamps
            now = datetime.now().isoformat()
            job_ids = []
            cursor = self.conn.cursor()
            
            for job in jobs:
                # Check if job is a dictionary, if not convert it
                if isinstance(job, dict):
                    job_dict = job
                elif isinstance(job, str):
                    # Likely a JSON string - try to parse
                    try:
                        job_dict = json.loads(job)
                    except:
                        # If parsing fails, create a simple dict with the string
                        job_dict = {"content": job}
                else:
                    # Handle other types or skip
                    continue
                
                # Extract common fields
                title = job_dict.get('title', '')
                company = job_dict.get('company', '')
                description = job_dict.get('description', '')
                location = job_dict.get('location', '')
                
                cursor.execute(
                    'INSERT INTO jobs (title, company, description, location, job_data, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (
                        title,
                        company,
                        description,
                        location,
                        json.dumps(job_dict),
                        now
                    )
                )
                job_ids.append(str(cursor.lastrowid))
            
            self.conn.commit()
            logger.info(f"Saved {len(job_ids)} jobs to database")
            return job_ids
        
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")
            return []
            
    def get_jobs(self, job_ids: List[str]) -> List[Dict[str, Any]]:
        """Get job listings by IDs
        
        Args:
            job_ids: List of job document IDs
            
        Returns:
            List of job listings
        """
        try:
            jobs = []
            cursor = self.conn.cursor()
            
            # Convert job_ids to a format for SQL IN clause
            placeholders = ', '.join(['?'] * len(job_ids))
            query = f'SELECT * FROM jobs WHERE id IN ({placeholders})'
            
            cursor.execute(query, job_ids)
            rows = cursor.fetchall()
            
            for row in rows:
                job_dict = dict(row)
                # Parse the stored JSON data
                job_data = json.loads(job_dict['job_data'])
                job_data['id'] = job_dict['id']
                jobs.append(job_data)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error retrieving jobs: {e}")
            return []
    
    def save_matches(self, user_id: str, resume_id: str, job_matches: List[Dict[str, Any]]) -> str:
        """Save job matches for a user
        
        Args:
            user_id: User identifier
            resume_id: Resume document ID
            job_matches: List of matched jobs
            
        Returns:
            ID of saved matches document
        """
        try:
            # Create matches document
            matches_doc = {
                "user_id": user_id,
                "resume_id": resume_id,
                "matches": job_matches
            }
            
            now = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO matches (user_id, resume_id, matches_data, created_at) VALUES (?, ?, ?, ?)',
                (
                    user_id,
                    resume_id,
                    json.dumps(matches_doc),
                    now
                )
            )
            self.conn.commit()
            match_id = str(cursor.lastrowid)
            
            logger.info(f"Saved {len(job_matches)} job matches for user {user_id}")
            return match_id
            
        except Exception as e:
            logger.error(f"Error saving job matches: {e}")
            raise
    
    def get_matches(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Get job matches by ID
        
        Args:
            match_id: Matches document ID
            
        Returns:
            Matches document or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM matches WHERE id = ?', (match_id,))
            row = cursor.fetchone()
            
            if row:
                match_dict = dict(row)
                # Parse the stored JSON data
                matches_data = json.loads(match_dict['matches_data'])
                matches_data['id'] = match_dict['id']
                return matches_data
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving matches {match_id}: {e}")
            return None
    
    def get_matches_by_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get latest job matches for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Latest matches document or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT * FROM matches WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                match_dict = dict(row)
                # Parse the stored JSON data
                matches_data = json.loads(match_dict['matches_data'])
                matches_data['id'] = match_dict['id']
                return matches_data
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving matches for user {user_id}: {e}")
            return None
