import os
import json
import logging
import re
from typing import Dict, Any, List
from pypdf import PdfReader
from docx import Document
import google.generativeai as genai
from dotenv import load_dotenv

class DocumentProcessor:
    """Process and analyze uploaded documents for service provider verification using Google Gemini."""

    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.txt']
        # Initialize Gemini
        load_dotenv()
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def extract_text(self, file_path: str) -> str:
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
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file, strict=False)
                for page in pdf_reader.pages:
                    if page is not None:
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        except Exception as e:
                            logging.warning(f"Failed to extract text from page: {str(e)}")
                            continue
        except Exception as e:
            raise Exception(f"PDF extraction failed: {str(e)}")
        return text.strip()

    def _extract_docx_text(self, file_path: str) -> str:
        try:
            doc = Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs]).strip()
        except Exception as e:
            raise Exception(f"DOCX extraction failed: {str(e)}")

    def _extract_txt_text(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read().strip()
            except:
                raise Exception(f"TXT extraction failed: {str(e)}")

    def analyze_document(self, text: str, document_type: str) -> Dict[str, Any]:
        if not text or len(text.strip()) < 10:
            return {
                'valid': False,
                'analysis': 'Document appears to be empty or too short',
                'extracted_info': {},
                'confidence': 0.0
            }

        prompt = f"Analyze this {document_type} and extract relevant information:\n\n{text}"
        response = self.model.generate_content(prompt)
        
        analysis = {
            'valid': True,
            'confidence': 0.8,
            'analysis': f"{document_type} document analyzed using Gemini",
            'extracted_info': {},
            'red_flags': [],
            'verification_notes': ""
        }

        if document_type == "resume":
            name_prompt = "Extract the full name from this text:\n" + text
            contact_prompt = "Extract all contact information (email and phone) from this text:\n" + text
            skills_prompt = "Extract a list of professional skills from this text:\n" + text
            education_prompt = "Extract education details from this text:\n" + text

            analysis["extracted_info"] = {
                "name": self.model.generate_content(name_prompt).text,
                "contact_info": self.model.generate_content(contact_prompt).text,
                "skills": self.model.generate_content(skills_prompt).text.split(','),
                "education": self.model.generate_content(education_prompt).text.split('\n'),
            }
        elif document_type == "portfolio":
            projects_prompt = "Extract a list of projects from this text:\n" + text
            tools_prompt = "Extract a list of tools and technologies used from this text:\n" + text

            analysis["extracted_info"] = {
                "projects": self.model.generate_content(projects_prompt).text.split('\n'),
                "tools": self.model.generate_content(tools_prompt).text.split(',')
            }

        return analysis

    def validate_document_authenticity(self, text: str, document_type: str) -> Dict[str, Any]:
        prompt = f"Analyze this {document_type} for authenticity. Look for signs of fraud or suspicious content:\n\n{text}"
        response = self.model.generate_content(prompt)
        
        authenticity_analysis = response.text
        score = 0.8 if "authentic" in authenticity_analysis.lower() else 0.5
        
        return {
            "authenticity_score": score,
            "fraud_indicators": [line for line in authenticity_analysis.split('\n') if 'suspicious' in line.lower()],
            "authenticity_factors": [line for line in authenticity_analysis.split('\n') if 'authentic' in line.lower()],
            "recommendation": "Review" if score < 0.6 else "Likely authentic",
            "manual_review_required": score < 0.6
        }

    def extract_skills_from_documents(self, documents_text: str) -> List[str]:
        prompt = "Extract a comprehensive list of professional skills from this text:\n" + documents_text
        response = self.model.generate_content(prompt)
        return [skill.strip() for skill in response.text.split(',')]