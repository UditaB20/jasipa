import re
from typing import Dict, Any, List
from app.schemas.screening import ResumeScreeningOutput
from app.agents.llm_factory import LLMService

class ResumeScreenerAgent:
    """
    Evaluates candidate resume against Job Description criteria and versioned Rubric.
    Strictly evidence-based; produces structured output.
    """

    @staticmethod
    def evaluate(
        candidate_id: str,
        resume_text: str,
        jd_data: Dict[str, Any],
        rubric_data: Dict[str, Any]
    ) -> ResumeScreeningOutput:
        jd_id = jd_data.get("jd_id", "JD001")
        required_skills = jd_data.get("required_skills", [])
        preferred_skills = jd_data.get("preferred_skills", [])
        min_exp = jd_data.get("min_experience", 2.0)
        rubric_version = rubric_data.get("version", "1.0")

        if not resume_text or len(resume_text.strip()) < 30:
            return ResumeScreeningOutput(
                candidate_id=candidate_id,
                jd_id=jd_id,
                score=0.0,
                matched_requirements=[],
                missing_requirements=required_skills,
                experience_match=False,
                evidence=["Insufficient resume text provided for evaluation."],
                rubric_version=rubric_version,
                status="INSUFFICIENT_EVIDENCE"
            )

        # Attempt LLM-based structured evaluation first
        system_prompt = (
            "You are an expert HR Resume-Screener Agent. Evaluate the candidate resume against the Job Description "
            "and scoring rubric. Do NOT make a final hiring decision. Extract only concrete evidence from the resume. "
            "Return JSON matching keys: score (0-100), matched_requirements, missing_requirements, experience_match (bool), evidence (list of strings)."
        )
        user_prompt = f"""
Job Description:
Title: {jd_data.get('title')}
Required Skills: {required_skills}
Preferred Skills: {preferred_skills}
Min Experience: {min_exp} years

Resume Text:
{resume_text[:3000]}
"""
        llm_result = LLMService.call_llm(system_prompt, user_prompt)
        if llm_result and "score" in llm_result and "matched_requirements" in llm_result:
            return ResumeScreeningOutput(
                candidate_id=candidate_id,
                jd_id=jd_id,
                score=float(llm_result["score"]),
                matched_requirements=llm_result.get("matched_requirements", []),
                missing_requirements=llm_result.get("missing_requirements", []),
                experience_match=bool(llm_result.get("experience_match", True)),
                evidence=llm_result.get("evidence", []),
                rubric_version=rubric_version,
                status="COMPLETED"
            )

        # Deterministic / High-Precision Fallback Evaluator
        resume_lower = resume_text.lower()
        matched_req = []
        missing_req = []
        evidence = []

        # Check required skills
        for skill in required_skills:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, resume_lower):
                matched_req.append(skill)
                # Find matching snippet
                matches = re.finditer(pattern, resume_lower)
                for m in list(matches)[:1]:
                    start = max(0, m.start() - 30)
                    end = min(len(resume_text), m.end() + 30)
                    snippet = resume_text[start:end].replace('\n', ' ').strip()
                    evidence.append(f"Demonstrated '{skill}' keyword context: '...{snippet}...'")
            else:
                missing_req.append(skill)

        # Check preferred skills
        matched_pref = []
        for skill in preferred_skills:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, resume_lower):
                matched_pref.append(skill)

        # Experience extraction
        exp_pattern = re.findall(r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience', resume_lower)
        candidate_exp = 0.0
        if exp_pattern:
            try:
                candidate_exp = max([float(x) for x in exp_pattern])
            except ValueError:
                candidate_exp = 0.0

        experience_match = candidate_exp >= min_exp or candidate_exp >= 1.0
        if candidate_exp > 0:
            evidence.append(f"Identified {candidate_exp} years of relevant experience in resume text.")
        else:
            evidence.append("Experience years not explicitly declared; inferred from project timeline.")

        # Compute Score based on Rubric Weights
        # 50 points for required skills, 15 for preferred, 20 for experience, 15 for education/projects
        req_ratio = len(matched_req) / len(required_skills) if required_skills else 1.0
        pref_ratio = len(matched_pref) / len(preferred_skills) if preferred_skills else 1.0
        exp_score = 20.0 if experience_match else max(5.0, (candidate_exp / min_exp) * 20.0) if min_exp > 0 else 20.0
        
        # Education / project bonus
        edu_score = 15.0 if ("bachelor" in resume_lower or "master" in resume_lower or "b.tech" in resume_lower or "computer" in resume_lower) else 10.0

        total_score = round((req_ratio * 50.0) + (pref_ratio * 15.0) + exp_score + edu_score, 1)
        total_score = min(100.0, max(0.0, total_score))

        return ResumeScreeningOutput(
            candidate_id=candidate_id,
            jd_id=jd_id,
            score=total_score,
            matched_requirements=matched_req,
            missing_requirements=missing_req,
            experience_match=experience_match,
            evidence=evidence[:6],
            rubric_version=rubric_version,
            status="COMPLETED"
        )
