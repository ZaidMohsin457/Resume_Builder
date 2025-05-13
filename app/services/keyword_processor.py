import logging
from typing import List, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)

class KeywordProcessor:
    # Common tech stacks and their related technologies
    TECH_STACKS = {
        "frontend": ["react", "vue", "angular", "javascript", "typescript", "html", "css", "sass", "webpack", "babel"],
        "backend": ["python", "java", "nodejs", "php", "ruby", "golang", "django", "flask", "spring", "express"],
        "database": ["sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "oracle", "nosql"],
        "devops": ["docker", "kubernetes", "aws", "azure", "gcp", "jenkins", "gitlab", "ci/cd", "terraform"],
        "mobile": ["android", "ios", "react native", "flutter", "swift", "kotlin", "mobile development"],
        "ai_ml": ["machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "computer vision", "data science"]
    }

    # Common skill variations and synonyms
    SKILL_SYNONYMS = {
        "javascript": ["js", "ecmascript", "node.js", "nodejs"],
        "python": ["py", "python3", "python2"],
        "react": ["reactjs", "react.js"],
        "machine learning": ["ml", "machine-learning"],
        "artificial intelligence": ["ai", "artificial-intelligence"],
    }

    def __init__(self):
        # Create reverse mappings for quick lookups
        self.skill_to_stack = {}
        self.skill_to_synonyms = {}
        
        for stack, skills in self.TECH_STACKS.items():
            for skill in skills:
                self.skill_to_stack[skill] = stack
        
        for main_skill, synonyms in self.SKILL_SYNONYMS.items():
            for synonym in synonyms:
                self.skill_to_synonyms[synonym] = main_skill

    def process_keywords(self, keywords: List[str], max_queries: int = 3) -> List[str]:
        """
        Process raw keywords into intelligent search queries
        """
        logger.info(f"Processing keywords: {keywords}")
        
        # Normalize keywords
        normalized_keywords = self._normalize_keywords(keywords)
        
        # Group by tech stacks
        stack_groups = self._group_by_tech_stack(normalized_keywords)
        
        # Generate optimized queries
        queries = self._generate_queries(stack_groups, max_queries)
        
        logger.info(f"Generated queries: {queries}")
        return queries

    def _normalize_keywords(self, keywords: List[str]) -> List[str]:
        """Normalize keywords by handling synonyms and standardizing format"""
        normalized = []
        for keyword in keywords:
            keyword = keyword.lower().strip()
            # Replace with main term if it's a synonym
            if keyword in self.skill_to_synonyms:
                keyword = self.skill_to_synonyms[keyword]
            normalized.append(keyword)
        return list(set(normalized))  # Remove duplicates

    def _group_by_tech_stack(self, keywords: List[str]) -> Dict[str, List[str]]:
        """Group keywords by their tech stack"""
        groups = defaultdict(list)
        ungrouped = []
        
        for keyword in keywords:
            if keyword in self.skill_to_stack:
                stack = self.skill_to_stack[keyword]
                groups[stack].append(keyword)
            else:
                ungrouped.append(keyword)
        
        if ungrouped:
            groups["other"] = ungrouped
            
        return groups

    def _generate_queries(self, stack_groups: Dict[str, List[str]], max_queries: int) -> List[str]:
        """Generate optimized search queries from grouped keywords"""
        queries = []
        
        # Prioritize full-stack combinations
        if "frontend" in stack_groups and "backend" in stack_groups:
            frontend_skill = stack_groups["frontend"][0]
            backend_skill = stack_groups["backend"][0]
            queries.append(f"fullstack {frontend_skill} {backend_skill} developer")
        
        # Generate role-specific queries
        for stack, skills in stack_groups.items():
            if stack == "other":
                continue
                
            if len(skills) >= 2:
                main_skills = " ".join(skills[:2])
                queries.append(f"{stack} developer {main_skills}")
            elif len(skills) == 1:
                queries.append(f"{stack} {skills[0]} developer")
        
        # Add general skills query if needed
        if "other" in stack_groups:
            other_skills = " ".join(stack_groups["other"][:3])  # Limit to top 3 other skills
            if other_skills:
                queries.append(f"developer {other_skills}")
        
        return queries[:max_queries]  # Limit to max_queries 