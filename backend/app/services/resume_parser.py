import fitz # PyMuPDF
import re
from typing import Dict, Any, List

COMMON_TECH_SKILLS = [
    "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "React", "Node.js",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes", "AWS",
    "Azure", "GCP", "FastAPI", "Django", "Flask", "Spring Boot", "Git", "CI/CD",
    "REST API", "GraphQL", "Data Structures", "Algorithms", "Machine Learning",
    "Deep Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-Learn",
    "Microservices", "System Design", "Agile", "Scrum", "HTML5", "CSS3", "Tailwind"
]

def extract_text_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts plain text from PDF bytes using PyMuPDF.
    Calculates confidence score based on character density and structure.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_content = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_content.append(page.get_text())
        
        full_text = "\n".join(text_content).strip()
        doc.close()
        
        if not full_text or len(full_text) < 50:
            return {
                "success": False,
                "text": full_text,
                "confidence": 0.0,
                "status": "MANUAL_REVIEW_REQUIRED",
                "message": "Extracted text is empty or too short. Low extraction confidence."
            }
        
        # Calculate heuristic confidence (presence of alphabetic density)
        alpha_count = sum(1 for c in full_text if c.isalnum() or c.isspace())
        total_count = len(full_text)
        confidence = round(min(1.0, alpha_count / total_count), 2) if total_count > 0 else 0.0

        if confidence < 0.65:
            return {
                "success": True,
                "text": full_text,
                "confidence": confidence,
                "status": "MANUAL_REVIEW_REQUIRED",
                "message": "Low OCR/text extraction confidence. Manual review required."
            }

        return {
            "success": True,
            "text": full_text,
            "confidence": confidence,
            "status": "PARSED",
            "message": "Text extracted successfully."
        }
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "confidence": 0.0,
            "status": "MANUAL_REVIEW_REQUIRED",
            "message": f"Error parsing PDF: {str(e)}"
        }

def extract_preliminary_metadata(text: str) -> Dict[str, Any]:
    """
    Extracts preliminary skills, email, and experience estimate from resume text without hallucination.
    """
    text_lower = text.lower()
    
    # 1. Matched skills
    detected_skills = []
    for skill in COMMON_TECH_SKILLS:
        # Match as whole word / boundary
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            detected_skills.append(skill)
            
    # 2. Email extraction
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else None
    
    # 3. Experience years extraction
    exp_pattern = re.findall(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience', text_lower)
    experience_years = 0.0
    if exp_pattern:
        try:
            experience_years = max([float(x) for x in exp_pattern])
        except ValueError:
            experience_years = 0.0
            
    # 4. Education extraction
    education = "Not Specified"
    if "ph.d" in text_lower or "phd" in text_lower:
        education = "Ph.D."
    elif "master" in text_lower or "m.s." in text_lower or "msc" in text_lower or "m.tech" in text_lower:
        education = "Master's Degree"
    elif "bachelor" in text_lower or "b.s." in text_lower or "bsc" in text_lower or "b.tech" in text_lower or "b.e." in text_lower:
        education = "Bachelor's Degree"

    return {
        "skills": detected_skills,
        "email": email,
        "experience_years": experience_years,
        "education": education
    }
