import os
import json
import logging
from typing import Dict, Any, Optional, List
from pypdf import PdfReader
from docx import Document
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class DocumentProcessor:
    """Process and analyze uploaded documents for service provider verification"""
    
    def __init__(self):
        self.model = "gpt-4o"
        self.supported_formats = ['.pdf', '.docx', '.txt']
    
    def extract_text(self, file_path: str) -> str:
        """
        Extract text from uploaded documents
        
        Args:
            file_path: Path to the uploaded file
            
        Returns:
            Extracted text content
        """
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.pdf':
                return self._extract_pdf_text(file_path)
            elif file_extension == '.docx':
                return self._extract_docx_text(file_path)
            elif file_extension == '.txt':
                return self._extract_txt_text(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
                
        except Exception as e:
            logging.error(f"Text extraction failed for {file_path}: {str(e)}")
            return f"Text extraction failed: {str(e)}"
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
        except Exception as e:
            raise Exception(f"PDF extraction failed: {str(e)}")
        
        return text.strip()
    
    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"DOCX extraction failed: {str(e)}")
    
    def _extract_txt_text(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            try:
                # Try with different encoding
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read().strip()
            except:
                raise Exception(f"TXT extraction failed: {str(e)}")
    
    def analyze_document(self, text: str, document_type: str) -> Dict[str, Any]:
        """
        Analyze document content using AI
        
        Args:
            text: Extracted text from document
            document_type: Type of document (certificate, portfolio, id, resume)
            
        Returns:
            Dict containing analysis results
        """
        try:
            if not text or len(text.strip()) < 10:
                return {
                    'valid': False,
                    'analysis': 'Document appears to be empty or too short',
                    'extracted_info': {},
                    'confidence': 0.0
                }
            
            # Truncate text if too long (to avoid token limits)
            if len(text) > 4000:
                text = text[:4000] + "... [truncated]"
            
            prompt = self._build_analysis_prompt(text, document_type)
            
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert document analyzer specialized in construction industry "
                        "credentials, certificates, and professional documents. Analyze the provided document "
                        "and extract relevant professional information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Ensure required fields
            if 'valid' not in result:
                result['valid'] = False
            if 'confidence' not in result:
                result['confidence'] = 0.0
            if 'extracted_info' not in result:
                result['extracted_info'] = {}
                
            return result
            
        except Exception as e:
            logging.error(f"Document analysis failed: {str(e)}")
            return {
                'valid': False,
                'analysis': f'Analysis failed: {str(e)}',
                'extracted_info': {},
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _build_analysis_prompt(self, text: str, document_type: str) -> str:
        """Build analysis prompt based on document type"""
        
        base_prompt = f"""
        Analyze this {document_type} document and extract relevant professional information.

        DOCUMENT CONTENT:
        {text}

        Please analyze and provide response in JSON format:
        {{
            "valid": boolean,
            "confidence": float (0.0 to 1.0),
            "analysis": "string - overall analysis of document quality and authenticity",
            "extracted_info": {{
                // Document type specific fields will be added below
            }},
            "red_flags": ["flag1", "flag2"],
            "verification_notes": "string - notes for manual verification"
        }}
        """
        
        if document_type == 'certificate':
            return base_prompt + """
            For certificates, extract:
            "extracted_info": {
                "certificate_name": "string",
                "issuing_organization": "string",
                "issue_date": "string",
                "expiry_date": "string",
                "skills_certified": ["skill1", "skill2"],
                "certification_level": "string",
                "certificate_number": "string"
            }
            """
        
        elif document_type == 'resume':
            return base_prompt + """
            For resumes, extract:
            "extracted_info": {
                "name": "string",
                "contact_info": "string",
                "work_experience": [
                    {
                        "position": "string",
                        "company": "string",
                        "duration": "string",
                        "responsibilities": "string"
                    }
                ],
                "skills": ["skill1", "skill2"],
                "education": ["education1", "education2"],
                "years_experience": integer
            }
            """
        
        elif document_type == 'portfolio':
            return base_prompt + """
            For portfolios, extract:
            "extracted_info": {
                "projects": [
                    {
                        "project_name": "string",
                        "description": "string",
                        "skills_used": ["skill1", "skill2"],
                        "duration": "string"
                    }
                ],
                "specializations": ["spec1", "spec2"],
                "work_quality_indicators": ["indicator1", "indicator2"]
            }
            """
        
        elif document_type == 'id':
            return base_prompt + """
            For ID documents, extract:
            "extracted_info": {
                "document_type": "string",
                "name": "string",
                "id_number": "string",
                "issue_date": "string",
                "expiry_date": "string",
                "issuing_authority": "string"
            }
            """
        
        else:
            return base_prompt + """
            For general documents, extract:
            "extracted_info": {
                "document_purpose": "string",
                "relevant_skills": ["skill1", "skill2"],
                "professional_info": "string",
                "dates_mentioned": ["date1", "date2"]
            }
            """
    
    def validate_document_authenticity(self, text: str, document_type: str) -> Dict[str, Any]:
        """
        Perform additional authenticity checks on document
        
        Args:
            text: Document text
            document_type: Type of document
            
        Returns:
            Dict containing authenticity analysis
        """
        try:
            prompt = f"""
            Analyze this {document_type} document for authenticity and potential fraud indicators.

            DOCUMENT CONTENT:
            {text}

            Look for:
            1. Formatting consistency
            2. Professional language and terminology
            3. Logical information structure
            4. Potential fabrication indicators
            5. Industry-standard elements

            Provide analysis in JSON format:
            {{
                "authenticity_score": float (0.0 to 1.0),
                "fraud_indicators": ["indicator1", "indicator2"],
                "authenticity_factors": ["factor1", "factor2"],
                "recommendation": "string",
                "manual_review_required": boolean
            }}
            """
            
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fraud detection expert specializing in document authenticity. "
                        "Analyze documents for signs of fabrication or inconsistencies."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logging.error(f"Authenticity validation failed: {str(e)}")
            return {
                'authenticity_score': 0.5,
                'fraud_indicators': [f'Analysis failed: {str(e)}'],
                'authenticity_factors': [],
                'recommendation': 'Manual review required due to technical error',
                'manual_review_required': True
            }
    
    def extract_skills_from_documents(self, documents_text: str) -> List[str]:
        """
        Extract construction-related skills from document text
        
        Args:
            documents_text: Combined text from all documents
            
        Returns:
            List of extracted skills
        """
        try:
            prompt = f"""
            Extract construction and technical skills from this document text:

            {documents_text}

            Return only construction-related skills in JSON format:
            {{
                "skills": ["skill1", "skill2", "skill3"]
            }}

            Focus on:
            - Construction techniques
            - Tool proficiency
            - Trade skills
            - Certifications
            - Technical abilities
            - Safety knowledge
            """
            
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in construction industry skills and terminology. "
                        "Extract only legitimate construction-related skills from documents."
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
            return result.get('skills', [])
            
        except Exception as e:
            logging.error(f"Skill extraction failed: {str(e)}")
            return []
