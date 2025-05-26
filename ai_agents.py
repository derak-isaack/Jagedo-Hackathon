import os
import json
import logging
from typing import Dict, List, Any, Optional
from google.generativeai import GenerativeModel
import google.generativeai as genai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    llm = GenerativeModel('gemini-2.0-flash')
except Exception as e:
    logger.error(f"Failed to initialize Google AI model: {str(e)}")
    llm = None

class AIVerificationAgent:
    """AI agent for verifying service provider applications using Google's Generative AI"""
    
    def __init__(self):
        self.model = "gemini-2.0-flash"
        
    def verify_application(self, user, profile) -> Dict[str, Any]:
        """
        Verify a service provider application using AI analysis
        
        Args:
            user: User object
            profile: ServiceProviderProfile object
            
        Returns:
            Dict containing verification results
        """
        try:
            if not llm:
                raise Exception("LLM not properly initialized")

            # Gather application data
            application_data = self._gather_application_data(user, profile)
            
            # Analyze with AI
            verification_prompt = self._build_verification_prompt(application_data)
            
            response = llm.generate_content(verification_prompt)
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                cleaned_text = response.text.strip()
                if cleaned_text.startswith(""):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith(""):
                    cleaned_text = cleaned_text[:-3]
                result = json.loads(cleaned_text.strip())
            
            if 'approved' not in result:
                result['approved'] = False
            if 'score' not in result:
                result['score'] = 0.0
            if 'analysis' not in result:
                result['analysis'] = {}
                
            return result
            
        except Exception as e:
            logger.error(f"AI verification failed: {str(e)}", exc_info=True)
            return {
                'approved': False,
                'score': 0.0,
                'analysis': {
                    'error': f"Verification failed: {str(e)}",
                    'manual_review_required': True
                }
            }
    
    def _gather_application_data(self, user, profile) -> Dict[str, Any]:
        """Gather all relevant data for verification"""
        
        # Get documents
        documents = []
        if profile.documents:
            for doc in profile.documents:
                documents.append({
                    'type': doc.document_type,
                    'filename': doc.original_filename,
                    'extracted_text': doc.extracted_text[:1000] if doc.extracted_text else '',  # Limit text length
                    'ai_analysis': json.loads(doc.ai_analysis) if doc.ai_analysis else {}
                })
        
        return {
            'user': {
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat() if user.created_at else None
            },
            'profile': {
                'profession': profile.profession,
                'specialization': profile.specialization,
                'experience_years': profile.experience_years,
                'skills': profile.skills,
                'location': profile.location,
                'hourly_rate': float(profile.hourly_rate) if profile.hourly_rate else None,
                'bio': profile.bio
            },
            'documents': documents
        }
    
    def _build_verification_prompt(self, data: Dict[str, Any]) -> str:
        """Build the verification prompt for AI analysis"""
        
        return f"""You are a CONSTRUCTION EXPERT and verification specialist. Verify this service provider application and provide analysis.

        APPLICATION DATA:
        {json.dumps(data, indent=2)}

        Analyze profile completeness, experience validation, skills assessment, document verification, credibility and red flags.
        
        Respond only in this JSON format:
        {{
            "approved": boolean,
            "score": float (0.0 to 1.0),
            "analysis": {{
                "profile_completeness": {{
                    "score": float,
                    "notes": "string"
                }},
                "experience_validation": {{
                    "score": float,
                    "notes": "string"
                }},
                "skills_assessment": {{
                    "score": float,
                    "relevant_skills": ["skill1", "skill2"],
                    "notes": "string"
                }},
                "document_verification": {{
                    "score": float,
                    "verified_documents": int,
                    "notes": "string"
                }},
                "credibility": {{
                    "score": float,
                    "notes": "string"
                }},
                "red_flags": ["flag1", "flag2"],
                "recommendations": "string",
                "approval_reason": "string"
            }}
        }}"""

class AutofillAgent:
    """AI agent for auto-filling job application forms"""
    
    def __init__(self):
        self.model = "gemini-2.0-flash"
    
    def generate_application_data(self, job, profile) -> Dict[str, Any]:
        """
        Generate autofill data for job application based on profile and job requirements
        
        Args:
            job: Job object
            profile: ServiceProviderProfile object
            
        Returns:
            Dict containing suggested application data
        """
        try:
            if not llm:
                raise Exception("LLM not properly initialized")

            # Get documents text for context
            documents_text = ""
            if profile.documents:
                for doc in profile.documents:
                    if doc.extracted_text:
                        documents_text += f"\n{doc.document_type}: {doc.extracted_text[:500]}"
            
            prompt = self._build_autofill_prompt(job, profile, documents_text)
            
            response = llm.generate_content(prompt)
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to clean/format the response
                cleaned_text = response.text.strip()
                if cleaned_text.startswith(""):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith(""):
                    cleaned_text = cleaned_text[:-3]
                result = json.loads(cleaned_text.strip())
            return result
            
        except Exception as e:
            logger.error(f"Autofill generation failed: {str(e)}", exc_info=True)
            return {
                'error': f"Autofill failed: {str(e)}",
                'cover_letter': "I am interested in this position and believe my skills align with your requirements.",
                'proposed_rate': None,
                'estimated_duration': "To be discussed"
            }
    
    def _build_autofill_prompt(self, job, profile, documents_text: str) -> str:
        """Build prompt for autofill generation"""
        
        job_data = {
            'title': job.title,
            'description': job.description,
            'required_skills': job.required_skills,
            'location': job.location,
            'budget_min': float(job.budget_min) if job.budget_min else None,
            'budget_max': float(job.budget_max) if job.budget_max else None,
            'profession_type': job.profession_type
        }
        
        profile_data = {
            'profession': profile.profession,
            'specialization': profile.specialization,
            'experience_years': profile.experience_years,
            'skills': profile.skills,
            'location': profile.location,
            'hourly_rate': float(profile.hourly_rate) if profile.hourly_rate else None,
            'bio': profile.bio
        }
        
        return f"""Generate a professional job application based on this information:

        JOB DETAILS:
        {json.dumps(job_data, indent=2)}

        APPLICANT PROFILE:
        {json.dumps(profile_data, indent=2)}

        DOCUMENTS CONTEXT:
        {documents_text}

        Respond only in this JSON format:
        {{
            "cover_letter": "A personalized, professional cover letter (2-3 paragraphs)",
            "proposed_rate": float or null,
            "estimated_duration": "string",
            "key_strengths": ["strength1", "strength2", "strength3"],
            "relevant_experience": "string",
            "availability": "string"
        }}"""

class SmartMatchingAgent:
    """AI agent for intelligent job matching"""
    
    def __init__(self):
        self.model = "gemini-2.0-flash"
    
    def calculate_match_score(self, job, service_provider_profile) -> Dict[str, Any]:
        """
        Calculate match score between a job and service provider
        
        Args:
            job: Job object
            service_provider_profile: ServiceProviderProfile object
            
        Returns:
            Dict containing match score and analysis
        """
        try:
            if not llm:
                raise Exception("LLM not properly initialized")

            prompt = self._build_matching_prompt(job, service_provider_profile)
            
            response = llm.generate_content(prompt)
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to clean/format the response
                cleaned_text = response.text.strip()
                if cleaned_text.startswith(""):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith(""):
                    cleaned_text = cleaned_text[:-3]
                result = json.loads(cleaned_text.strip())
            
            # Ensure score is within valid range
            if 'match_score' in result:
                result['match_score'] = max(0.0, min(1.0, result['match_score']))
            else:
                result['match_score'] = 0.0
                
            return result
            
        except Exception as e:
            logger.error(f"Match scoring failed: {str(e)}", exc_info=True)
            return {
                'match_score': 0.0,
                'reasons': [f"Matching failed: {str(e)}"],
                'concerns': ['Technical error in matching system']
            }
    
    def _build_matching_prompt(self, job, profile) -> str:
        """Build prompt for job matching analysis"""
        
        job_data = {
            'title': job.title,
            'description': job.description,
            'required_skills': job.required_skills,
            'location': job.location,
            'budget_min': float(job.budget_min) if job.budget_min else None,
            'budget_max': float(job.budget_max) if job.budget_max else None,
            'profession_type': job.profession_type
        }
        
        profile_data = {
            'profession': profile.profession,
            'specialization': profile.specialization,
            'experience_years': profile.experience_years,
            'skills': profile.skills,
            'location': profile.location,
            'hourly_rate': float(profile.hourly_rate) if profile.hourly_rate else None
        }
        
        return f"""Analyze the compatibility between this job and service provider profile.
        Give HIGHEST priority to matching job title with provider's specialization and skills.
    
        JOB REQUIREMENTS:
        {json.dumps(job_data, indent=2)}
    
        SERVICE PROVIDER PROFILE:
        {json.dumps(profile_data, indent=2)}
    
        Respond only in this JSON format:
        {{
            "match_score": float (0.0 to 1.0),
            "analysis": {{
                "title_match": {{
                    "score": float,
                    "matching_terms": ["term1", "term2"],
                    "notes": "string"
                }},
                "skills_match": {{
                    "score": float,
                    "matching_skills": ["skill1", "skill2"],
                    "missing_skills": ["skill1", "skill2"]
                }},
                "experience_match": {{
                    "score": float,
                    "notes": "string"
                }},
                "location_match": {{
                    "score": float,
                    "notes": "string"
                }},
                "budget_compatibility": {{
                    "score": float,
                    "notes": "string"
                }},
                "profession_match": {{
                    "score": float,
                    "notes": "string"
                }}
            }},
            "reasons": ["reason1", "reason2"],
            "concerns": ["concern1", "concern2"]
        }}"""