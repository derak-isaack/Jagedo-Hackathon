import os
import json
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class AIVerificationAgent:
    """AI agent for verifying service provider applications using LangChain and OpenAI"""
    
    def __init__(self):
        self.model = "gpt-4o"
        
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
            # Gather application data
            application_data = self._gather_application_data(user, profile)
            
            # Analyze with AI
            verification_prompt = self._build_verification_prompt(application_data)
            
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a CONSTRUCTION EXPERT and verification specialist with 20+ years of experience in the construction industry. "
                        "Your expertise includes: project management, skilled trades assessment, safety compliance, quality standards, "
                        "and contractor evaluation. You understand the difference between 'fundi' (skilled craftsmen) and professional contractors. "
                        "Your job is to assess the authenticity and qualifications of service provider applications to reduce admin backlog. "
                        "Evaluate their skills, experience, certifications, and documentation with the eye of a seasoned construction professional. "
                        "Flag any red flags or inconsistencies that could indicate fraudulent applications."
                    },
                    {
                        "role": "user",
                        "content": verification_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Ensure required fields are present
            if 'approved' not in result:
                result['approved'] = False
            if 'score' not in result:
                result['score'] = 0.0
            if 'analysis' not in result:
                result['analysis'] = {}
                
            return result
            
        except Exception as e:
            logging.error(f"AI verification failed: {str(e)}")
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
        
        return f"""
        Please verify this service provider application and provide a comprehensive analysis.

        APPLICATION DATA:
        {json.dumps(data, indent=2)}

        Please analyze the following aspects and provide your response in JSON format:

        1. Profile completeness and quality
        2. Experience validation (check if experience years match skills and specialization)
        3. Skills assessment (relevant to construction/fundi work)
        4. Document verification (if any documents provided)
        5. Overall credibility assessment
        6. Red flags or concerns

        Response format:
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
        }}

        Approval criteria:
        - Overall score must be >= 0.7
        - No major red flags
        - Profile shows genuine construction/technical expertise
        - Skills match the specialization
        """

class AutofillAgent:
    """AI agent for auto-filling job application forms"""
    
    def __init__(self):
        self.model = "gpt-4o"
    
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
            # Get documents text for context
            documents_text = ""
            if profile.documents:
                for doc in profile.documents:
                    if doc.extracted_text:
                        documents_text += f"\n{doc.document_type}: {doc.extracted_text[:500]}"
            
            prompt = self._build_autofill_prompt(job, profile, documents_text)
            
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert job application assistant for construction workers and professionals. "
                        "Generate personalized, professional application content based on the applicant's profile "
                        "and the job requirements. Always be honest about skills and experience."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logging.error(f"Autofill generation failed: {str(e)}")
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
        
        return f"""
        Generate a professional job application based on the following information:

        JOB DETAILS:
        {json.dumps(job_data, indent=2)}

        APPLICANT PROFILE:
        {json.dumps(profile_data, indent=2)}

        DOCUMENTS CONTEXT:
        {documents_text}

        Please generate application content in JSON format:
        {{
            "cover_letter": "A personalized, professional cover letter (2-3 paragraphs) highlighting relevant experience and skills",
            "proposed_rate": float or null (based on job budget and applicant's hourly rate),
            "estimated_duration": "Realistic time estimate based on job description",
            "key_strengths": ["strength1", "strength2", "strength3"],
            "relevant_experience": "Brief summary of most relevant experience",
            "availability": "When the applicant can start"
        }}

        Guidelines:
        - Be honest about experience and skills
        - Match the tone to the job (professional for professional roles, practical for fundi roles)
        - Propose fair rates within the job budget range if specified
        - Provide realistic time estimates
        - Highlight the most relevant skills and experience
        - Keep cover letter concise but engaging
        """

class SmartMatchingAgent:
    """AI agent for intelligent job matching"""
    
    def __init__(self):
        self.model = "gpt-4o"
    
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
            prompt = self._build_matching_prompt(job, service_provider_profile)
            
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert job matching algorithm for construction and technical services. "
                        "Analyze job requirements against service provider profiles and calculate compatibility scores."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Ensure score is within valid range
            if 'match_score' in result:
                result['match_score'] = max(0.0, min(1.0, result['match_score']))
            else:
                result['match_score'] = 0.0
                
            return result
            
        except Exception as e:
            logging.error(f"Match scoring failed: {str(e)}")
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
        
        return f"""
        Analyze the compatibility between this job and service provider profile:

        JOB REQUIREMENTS:
        {json.dumps(job_data, indent=2)}

        SERVICE PROVIDER PROFILE:
        {json.dumps(profile_data, indent=2)}

        Calculate a match score and provide analysis in JSON format:
        {{
            "match_score": float (0.0 to 1.0),
            "analysis": {{
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
            "concerns": ["concern1", "concern2"],
            "recommendation": "string"
        }}

        Scoring guidelines:
        - 0.9-1.0: Perfect match
        - 0.7-0.89: Very good match
        - 0.5-0.69: Good match
        - 0.3-0.49: Marginal match
        - 0.0-0.29: Poor match
        """
