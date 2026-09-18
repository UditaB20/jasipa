import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from app.database.session import SessionLocal, Base, engine
from app.database.models import (
    Candidate, JobDescription, Rubric, ScreeningResult, 
    Assessment, PanelDecision, BiasCheck, HumanReview, AuditLog
)
from app.services.rubric_service import generate_rubric_for_jd

def seed_database():
    db = SessionLocal()
    print("Clearing existing data and initializing database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 1. Seed 2 Job Descriptions
    print("Seeding Job Descriptions & Anchored Rubrics...")
    jd1 = JobDescription(
        jd_id="JD-SWE-101",
        title="Senior Full Stack Engineer",
        department="Engineering",
        description="We are seeking a Senior Full Stack Engineer to architect and build scalable cloud-native microservices with Python/FastAPI, modern React user interfaces, and robust PostgreSQL/SQL data storage pipelines. Experience with Docker and CI/CD is preferred.",
        required_skills=["Python", "React", "SQL", "FastAPI", "Data Structures"],
        preferred_skills=["Docker", "Kubernetes", "AWS", "CI/CD"],
        min_experience=3.5,
        education_requirement="Bachelor's in Computer Science or equivalent technical field",
        rubric_version="1.0"
    )
    db.add(jd1)

    jd2 = JobDescription(
        jd_id="JD-MLE-202",
        title="Machine Learning & Data Science Engineer",
        department="AI Research",
        description="Looking for an ML Engineer to design end-to-end machine learning pipelines, fine-tune neural models, implement vector databases, and deploy inference APIs in Python with PyTorch, Scikit-Learn, and FastAPI.",
        required_skills=["Python", "Machine Learning", "PyTorch", "SQL", "Pandas"],
        preferred_skills=["Docker", "TensorFlow", "Deep Learning", "GCP"],
        min_experience=3.0,
        education_requirement="Master's or Bachelor's in CS, AI, or Data Science",
        rubric_version="1.0"
    )
    db.add(jd2)
    db.commit()

    # 2. Generate and store Anchored Rubrics for both JDs
    rubric1_crit = generate_rubric_for_jd(jd1, version="1.0")
    rubric1 = Rubric(
        rubric_id="RUBRIC-SWE-01",
        jd_id=jd1.jd_id,
        version="1.0",
        resume_weight=0.40,
        skill_weight=0.40,
        culture_weight=0.20,
        criteria=rubric1_crit
    )
    db.add(rubric1)

    rubric2_crit = generate_rubric_for_jd(jd2, version="1.0")
    rubric2 = Rubric(
        rubric_id="RUBRIC-MLE-01",
        jd_id=jd2.jd_id,
        version="1.0",
        resume_weight=0.40,
        skill_weight=0.40,
        culture_weight=0.20,
        criteria=rubric2_crit
    )
    db.add(rubric2)
    db.commit()

    # 3. Seed 10 Realistic Diverse Candidates
    print("Seeding 10 diverse candidates across all evaluation archetypes...")

    # Candidate 1: Elena Rostova (Fully Completed & Approved End-to-End Walkthrough)
    c1 = Candidate(
        candidate_id="CAND-001-ELENA",
        name="Elena Rostova",
        email="elena.rostova@example.com",
        phone="+1 (555) 234-5678",
        cohort_tag="Cohort_Alpha",
        resume_text="Senior Software Engineer with 5 years of experience architecting high-throughput FastAPI microservices and React frontends. Proficient in SQL, PostgreSQL, Python, Data Structures, Docker, AWS, and Agile workflows. Led migration to containerized microservices reducing latency by 40%.",
        skills_extracted=["Python", "React", "SQL", "FastAPI", "Data Structures", "Docker", "AWS"],
        experience_years=5.0,
        education="Bachelor's in Computer Science",
        target_jd_id=jd1.jd_id,
        current_stage="DECIDED"
    )
    db.add(c1)
    db.commit()

    # Assessments & Evaluations for C1
    sr1 = ScreeningResult(
        screening_id="SCR-001",
        candidate_id=c1.candidate_id,
        jd_id=jd1.jd_id,
        score=92.0,
        matched_requirements=["Python", "React", "SQL", "FastAPI", "Data Structures"],
        missing_requirements=[],
        experience_match=True,
        evidence=["5 years of experience meets 3.5 yr threshold", "Demonstrated Python & FastAPI microservices architecture", "Extensive React & PostgreSQL background"],
        rubric_version="1.0",
        status="COMPLETED"
    )
    db.add(sr1)

    t1 = Assessment(
        assessment_id="ASM-TECH-001",
        candidate_id=c1.candidate_id,
        jd_id=jd1.jd_id,
        test_type="TECHNICAL",
        questions=[{"qid": "TECH_Q1"}, {"qid": "TECH_Q2"}, {"qid": "TECH_Q3"}],
        answers=[
            {"question_id": "TECH_Q1", "answer_text": "Option B: Asyncio uses an event loop on a single thread with cooperative multitasking."},
            {"question_id": "TECH_Q2", "answer_text": "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1;"},
            {"question_id": "TECH_Q3", "answer_text": "def has_cycle(graph):\n  visited = set()\n  rec_stack = set()\n  for node in graph:\n    if dfs(node, visited, rec_stack): return True\n  return False\n# Time Complexity: O(V+E)"}
        ],
        score=94.0,
        skill_breakdown={"Python": 95, "SQL / PostgreSQL": 92, "Data Structures & Algorithms": 95},
        evidence=["Correctly selected asyncio cooperative event loop", "Optimal SQL query using offset and distinct", "Implements robust cycle detection with O(V+E) analysis"],
        confidence=0.98,
        status="COMPLETED"
    )
    db.add(t1)

    b1 = Assessment(
        assessment_id="ASM-BEH-001",
        candidate_id=c1.candidate_id,
        jd_id=jd1.jd_id,
        test_type="BEHAVIORAL",
        questions=[{"qid": "BEH_Q1"}, {"qid": "BEH_Q2"}, {"qid": "BEH_Q3"}, {"qid": "BEH_Q4"}],
        answers=[
            {"question_id": "BEH_Q1", "answer_text": "In my previous role, our team had a disagreement regarding caching strategies. I benchmarked Redis vs Memcached with realistic payloads, presented the latency metrics, and achieved unanimous consensus."},
            {"question_id": "BEH_Q2", "answer_text": "Faced with vague requirements for an event ingestion pipeline, I conducted stakeholder interviews, defined explicit latency SLAs, and shipped an MVP in 3 sprints."},
            {"question_id": "BEH_Q3", "answer_text": "When tasked with learning Kubernetes under a 2-week deadline, I set up a local Minikube environment and delivered production Helm charts on time."},
            {"question_id": "BEH_Q4", "answer_text": "I communicated architectural decoupling to executive stakeholders using business KPI impact diagrams rather than low-level code specifics."}
        ],
        score=88.0,
        skill_breakdown={"communication": 88, "teamwork": 90, "problem_solving": 88, "adaptability": 86},
        evidence=["Concrete STAR response resolving team disagreement with objective metrics", "Proactive requirement definition under ambiguous scope"],
        confidence=0.92,
        status="COMPLETED"
    )
    db.add(b1)

    pd1 = PanelDecision(
        decision_id="DEC-001",
        candidate_id=c1.candidate_id,
        jd_id=jd1.jd_id,
        resume_score=92.0,
        skill_score=94.0,
        culture_score=88.0,
        merged_score=92.0,
        recommendation="PROCEED_TO_HUMAN_REVIEW",
        strengths=["Exceptional technical test execution (94/100)", "Strong match on all required JD skills", "Clear STAR behavioral answers with teamwork orientation"],
        gaps=["No significant qualification gaps identified."],
        disagreements=["Agent perspectives are strongly aligned."],
        evidence=["Extracted 5+ yrs experience", "Demonstrated optimal cycle detection and SQL queries", "Data-backed conflict resolution"],
        rubric_version="1.0"
    )
    db.add(pd1)

    bc1 = BiasCheck(
        check_id="BIAS-001",
        decision_id=pd1.decision_id,
        candidate_id=c1.candidate_id,
        flag_status="NO_SIGNIFICANT_DISPARITY_DETECTED",
        reason="Candidate cohort performance is within standard statistical parity bounds.",
        cohort_breakdown={"cohort": "Cohort_Alpha", "disparity_ratio": 1.0},
        requires_human_review=True
    )
    db.add(bc1)

    hr1 = HumanReview(
        review_id="REV-001",
        candidate_id=c1.candidate_id,
        reviewer_id="USR_REV_01",
        reviewer_name="Dr. Alex HumanReviewer",
        decision="APPROVE",
        notes="Candidate demonstrated stellar engineering fundamentals across both the technical test and behavioral STAR responses. Strong endorsement for hire.",
        timestamp=datetime.utcnow() - timedelta(hours=2)
    )
    db.add(hr1)

    # Candidate 2: Marcus Vance (Awaiting Human Review - High Potential Junior)
    c2 = Candidate(
        candidate_id="CAND-002-MARCUS",
        name="Marcus Vance",
        email="marcus.vance@example.com",
        cohort_tag="Cohort_Alpha",
        resume_text="Junior Software Developer with 2 years experience building React web applications and REST APIs in Python. Built full-stack open source tools with SQL databases and FastAPI.",
        skills_extracted=["Python", "React", "SQL", "FastAPI"],
        experience_years=2.0,
        education="Bachelor's in Computer Science",
        target_jd_id=jd1.jd_id,
        current_stage="HUMAN_REVIEW_PENDING"
    )
    db.add(c2)
    db.commit()

    sr2 = ScreeningResult(
        screening_id="SCR-002",
        candidate_id=c2.candidate_id,
        jd_id=jd1.jd_id,
        score=78.0,
        matched_requirements=["Python", "React", "SQL", "FastAPI"],
        missing_requirements=["Data Structures"],
        experience_match=False,
        evidence=["2.0 years experience is below 3.5 yr target threshold", "Matches 4 out of 5 required skills"],
        rubric_version="1.0",
        status="COMPLETED"
    )
    db.add(sr2)

    t2 = Assessment(
        assessment_id="ASM-TECH-002",
        candidate_id=c2.candidate_id,
        jd_id=jd1.jd_id,
        test_type="TECHNICAL",
        questions=[],
        answers=[],
        score=92.0,
        skill_breakdown={"Python": 95, "SQL": 90, "Data Structures": 91},
        evidence=["Superb coding implementation; solved algorithmic cycle detection with clean recursion stack."],
        confidence=0.95,
        status="COMPLETED"
    )
    db.add(t2)

    b2 = Assessment(
        assessment_id="ASM-BEH-002",
        candidate_id=c2.candidate_id,
        jd_id=jd1.jd_id,
        test_type="BEHAVIORAL",
        questions=[],
        answers=[],
        score=84.0,
        skill_breakdown={"communication": 85, "teamwork": 82, "problem_solving": 88, "adaptability": 81},
        evidence=["Demonstrated fast learning ability and openness to peer code reviews."],
        confidence=0.88,
        status="COMPLETED"
    )
    db.add(b2)

    pd2 = PanelDecision(
        decision_id="DEC-002",
        candidate_id=c2.candidate_id,
        jd_id=jd1.jd_id,
        resume_score=78.0,
        skill_score=92.0,
        culture_score=84.0,
        merged_score=84.8,
        recommendation="PROCEED_TO_HUMAN_REVIEW",
        strengths=["Hidden Gem: Technical test score (92/100) significantly outperforms resume pedigree (78/100)."],
        gaps=["Years of experience (2.0 yrs) slightly lower than JD target (3.5 yrs)."],
        disagreements=["Positive divergence: Demonstrated hands-on technical skill exceeds resume seniority."],
        evidence=["Solid algorithm knowledge demonstrated live"],
        rubric_version="1.0"
    )
    db.add(pd2)

    bc2 = BiasCheck(
        check_id="BIAS-002",
        decision_id=pd2.decision_id,
        candidate_id=c2.candidate_id,
        flag_status="NO_SIGNIFICANT_DISPARITY_DETECTED",
        reason="No adverse cohort disparity detected.",
        cohort_breakdown={"cohort": "Cohort_Alpha", "disparity_ratio": 1.0},
        requires_human_review=True
    )
    db.add(bc2)

    # Candidate 3: Tariq Al-Mansoor (Triggers Cohort Bias Disparity Warning)
    c3 = Candidate(
        candidate_id="CAND-003-TARIQ",
        name="Tariq Al-Mansoor",
        email="tariq.mansoor@example.com",
        cohort_tag="Cohort_Beta",
        resume_text="Software Engineer with 4 years experience in Python, SQL, and FastAPI backend engineering. Developed enterprise APIs and relational databases.",
        skills_extracted=["Python", "SQL", "FastAPI"],
        experience_years=4.0,
        education="Bachelor's in Computer Engineering",
        target_jd_id=jd1.jd_id,
        current_stage="HUMAN_REVIEW_PENDING"
    )
    db.add(c3)
    db.commit()

    sr3 = ScreeningResult(
        screening_id="SCR-003",
        candidate_id=c3.candidate_id,
        jd_id=jd1.jd_id,
        score=82.0,
        matched_requirements=["Python", "SQL", "FastAPI"],
        missing_requirements=["React", "Data Structures"],
        experience_match=True,
        evidence=["4.0 years experience exceeds 3.5 yr target", "Solid Python backend experience"],
        rubric_version="1.0",
        status="COMPLETED"
    )
    db.add(sr3)

    t3 = Assessment(
        assessment_id="ASM-TECH-003",
        candidate_id=c3.candidate_id,
        jd_id=jd1.jd_id,
        test_type="TECHNICAL",
        questions=[],
        answers=[],
        score=76.0,
        skill_breakdown={"Python": 85, "SQL": 80, "Data Structures": 63},
        evidence=["Correct SQL queries; minor edge case bug in graph algorithm."],
        confidence=0.89,
        status="COMPLETED"
    )
    db.add(t3)

    b3 = Assessment(
        assessment_id="ASM-BEH-003",
        candidate_id=c3.candidate_id,
        jd_id=jd1.jd_id,
        test_type="BEHAVIORAL",
        questions=[],
        answers=[],
        score=78.0,
        skill_breakdown={"communication": 75, "teamwork": 80, "problem_solving": 78, "adaptability": 79},
        evidence=["Good teamwork examples; thoughtful answer on learning new frameworks."],
        confidence=0.85,
        status="COMPLETED"
    )
    db.add(b3)

    pd3 = PanelDecision(
        decision_id="DEC-003",
        candidate_id=c3.candidate_id,
        jd_id=jd1.jd_id,
        resume_score=82.0,
        skill_score=76.0,
        culture_score=78.0,
        merged_score=78.8,
        recommendation="HUMAN_REVIEW_REQUIRED",
        strengths=["Solid backend background and meeting experience requirement."],
        gaps=["Technical test score is moderate (76/100)."],
        disagreements=["No major disagreements."],
        evidence=["Meets core requirements"],
        rubric_version="1.0"
    )
    db.add(pd3)

    bc3 = BiasCheck(
        check_id="BIAS-003",
        decision_id=pd3.decision_id,
        candidate_id=c3.candidate_id,
        flag_status="FLAGGED",
        reason="Cohort 'Cohort_Beta' has an average progression rate below the 80% parity threshold compared to Cohort_Alpha. Reviewer attention requested.",
        cohort_breakdown={"cohort": "Cohort_Beta", "disparity_ratio": 0.65},
        requires_human_review=True
    )
    db.add(bc3)

    # Candidate 4: Chloe Bennett (Insufficient Behavioral Evidence)
    c4 = Candidate(
        candidate_id="CAND-004-CHLOE",
        name="Chloe Bennett",
        email="chloe.bennett@example.com",
        cohort_tag="Cohort_Alpha",
        resume_text="Full Stack Engineer with 4 years in Python, React, and SQL database design.",
        skills_extracted=["Python", "React", "SQL"],
        experience_years=4.0,
        education="B.S. in Information Systems",
        target_jd_id=jd1.jd_id,
        current_stage="HUMAN_REVIEW_PENDING"
    )
    db.add(c4)
    db.commit()

    sr4 = ScreeningResult(
        screening_id="SCR-004",
        candidate_id=c4.candidate_id,
        jd_id=jd1.jd_id,
        score=84.0,
        matched_requirements=["Python", "React", "SQL"],
        missing_requirements=["FastAPI", "Data Structures"],
        experience_match=True,
        evidence=["4 years experience verified"],
        rubric_version="1.0",
        status="COMPLETED"
    )
    db.add(sr4)

    t4 = Assessment(
        assessment_id="ASM-TECH-004",
        candidate_id=c4.candidate_id,
        jd_id=jd1.jd_id,
        test_type="TECHNICAL",
        questions=[],
        answers=[],
        score=85.0,
        skill_breakdown={"Python": 88, "SQL": 84, "Data Structures": 83},
        evidence=["Demonstrated solid coding fundamentals."],
        confidence=0.90,
        status="COMPLETED"
    )
    db.add(t4)

    b4 = Assessment(
        assessment_id="ASM-BEH-004",
        candidate_id=c4.candidate_id,
        jd_id=jd1.jd_id,
        test_type="BEHAVIORAL",
        questions=[],
        answers=[{"question_id": "BEH_Q1", "answer_text": "I agreed."}],
        score=0.0,
        skill_breakdown={},
        evidence=["Candidate provided 1-word answer. Status: INSUFFICIENT_EVIDENCE. Requires live interview inquiry."],
        confidence=0.20,
        status="INSUFFICIENT_EVIDENCE"
    )
    db.add(b4)

    pd4 = PanelDecision(
        decision_id="DEC-004",
        candidate_id=c4.candidate_id,
        jd_id=jd1.jd_id,
        resume_score=84.0,
        skill_score=85.0,
        culture_score=0.0,
        merged_score=67.6,
        recommendation="ADDITIONAL_INFORMATION_REQUIRED",
        strengths=["Strong technical score (85/100) and resume background."],
        gaps=["Behavioral assessment lacks sufficient evidence to score."],
        disagreements=["Incomplete behavioral data requires follow-up interview inquiry."],
        evidence=["Technical test passed", "Behavioral assessment incomplete"],
        rubric_version="1.0"
    )
    db.add(pd4)

    bc4 = BiasCheck(
        check_id="BIAS-004",
        decision_id=pd4.decision_id,
        candidate_id=c4.candidate_id,
        flag_status="NO_SIGNIFICANT_DISPARITY_DETECTED",
        reason="No cohort bias anomaly detected.",
        cohort_breakdown={"cohort": "Cohort_Alpha", "disparity_ratio": 1.0},
        requires_human_review=True
    )
    db.add(bc4)

    # Candidates 5 to 10: Candidates at various pipeline stages
    additional_candidates = [
        ("CAND-005-DAVID", "David Chen", "david.chen@example.com", "Cohort_Beta", "Machine learning researcher with 4 years in Python, PyTorch, SQL, and Pandas.", ["Python", "Machine Learning", "PyTorch", "SQL", "Pandas"], 4.0, jd2.jd_id, "PANEL_EVALUATED"),
        ("CAND-006-AISHA", "Aisha Khan", "aisha.khan@example.com", "Cohort_Gamma", "Data Scientist with 3.5 years in PyTorch, Pandas, Scikit-Learn, and Python.", ["Python", "Machine Learning", "Pandas"], 3.5, jd2.jd_id, "TECHNICAL_ASSESSED"),
        ("CAND-007-SAMUEL", "Samuel O'Connor", "samuel.oconnor@example.com", "Cohort_Alpha", "Full Stack Developer with 3 years in React, Python, and SQL.", ["Python", "React", "SQL"], 3.0, jd1.jd_id, "RESUME_SCREENED"),
        ("CAND-008-PRIYA", "Priya Sharma", "priya.sharma@example.com", "Cohort_Beta", "Python backend engineer with 5 years in FastAPI, PostgreSQL, and Docker.", ["Python", "SQL", "FastAPI", "Docker"], 5.0, jd1.jd_id, "APPLIED"),
        ("CAND-009-LUCAS", "Lucas Silva", "lucas.silva@example.com", "Cohort_Gamma", "Machine Learning Engineer with 3 years in Deep Learning, PyTorch, and Python.", ["Python", "Machine Learning", "PyTorch"], 3.0, jd2.jd_id, "APPLIED"),
        ("CAND-010-FATIMA", "Fatima Zahra", "fatima.zahra@example.com", "Cohort_Beta", "Senior Software Engineer with 6 years in Python, React, SQL, and System Design.", ["Python", "React", "SQL", "Data Structures"], 6.0, jd1.jd_id, "APPLIED")
    ]

    for cid, name, email, cohort, resume, skills, exp, target_jd, stage in additional_candidates:
        cand = Candidate(
            candidate_id=cid,
            name=name,
            email=email,
            cohort_tag=cohort,
            resume_text=resume,
            skills_extracted=skills,
            experience_years=exp,
            education="Bachelor's in Computer Science",
            target_jd_id=target_jd,
            current_stage=stage
        )
        db.add(cand)

    db.commit()

    # Seed Audit Log entries for initial dataset
    for c in [c1, c2, c3, c4]:
        log_entry = AuditLog(
            candidate_id=c.candidate_id,
            stage="APPLICATION_SEEDED",
            event=f"Candidate Application Seeded: {c.name}",
            agent="SYSTEM_SEEDER",
            input_reference={"target_jd_id": c.target_jd_id},
            output={"stage": c.current_stage},
            rubric_version="1.0"
        )
        db.add(log_entry)

    db.commit()
    db.close()
    print("Database seeding completed successfully with 10 candidates, 2 JDs, anchored rubrics, and full audit logs!")

if __name__ == "__main__":
    seed_database()
