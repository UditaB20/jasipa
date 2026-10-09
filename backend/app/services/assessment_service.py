from typing import List, Dict, Any, Optional
from app.database.models import JobDescription

def generate_technical_questions_for_jd(jd: Optional[JobDescription]) -> List[Dict[str, Any]]:
    """
    Generates a role-anchored technical/functional assessment based on the JD's department and skills.
    Covers Engineering, Finance/Accounting, HR/Operations, and Product/Sales.
    """
    dept = (jd.department or "").lower() if jd else ""
    title = (jd.title or "").lower() if jd else ""
    skills = [s.strip() for s in (jd.required_skills or [])] if jd else []
    skills_lower = [s.lower() for s in skills]
    desc = (jd.description or "").lower() if jd else ""
    questions = []

    # 1. HR & People Operations Roles
    if "human resource" in dept or "hr" in dept or "talent" in dept or "recruiting" in title or "people" in dept:
        questions.append({
            "question_id": "TECH_Q1",
            "type": "mcq",
            "competency_or_skill": "HR Governance & Compliance",
            "prompt": "Under the EEOC Uniform Guidelines on Employee Selection, what statistical metric establishes prima facie evidence of adverse impact?",
            "options": [
                "A) Selection rate for any protected group is less than 4/5ths (80%) of the rate for the group with highest rate",
                "B) Total applicant count differs by more than 10% between demographics",
                "C) Standard deviation of interview scores exceeds 2.5 points",
                "D) Average candidate tenure falls below 18 months"
            ],
            "correct_option": "A",
            "rubric_guideline": "Identifies the 4/5ths (80%) rule for adverse impact determination."
        })
        questions.append({
            "question_id": "TECH_Q2",
            "type": "short_answer",
            "competency_or_skill": "Structured Interview Design",
            "prompt": "Explain how anchoring behavioral interview questions to a scoring rubric reduces subjective interviewer bias compared to unstructured interviews.",
            "rubric_guideline": "Explains predefined scoring anchors, observable evidence criteria, mitigating halo/horns and similarity bias."
        })
        questions.append({
            "question_id": "TECH_Q3",
            "type": "case_analysis",
            "competency_or_skill": "Employee Relations & Mediation",
            "prompt": "A department manager demands to bypass standard interview scoring to hire a referral who scored below rubric threshold. How do you handle this while preserving compliance and trust?",
            "rubric_guideline": "Demonstrates diplomacy, reference to documented governance policy, audit trail integrity, and escalation pathways."
        })
        return questions

    # 2. Finance, Accounting & Banking Roles
    if "finance" in dept or "account" in dept or "banking" in title or "audit" in title:
        questions.append({
            "question_id": "TECH_Q1",
            "type": "mcq",
            "competency_or_skill": "Financial Accounting (GAAP / IFRS)",
            "prompt": "Under accrual accounting principles, when should revenue from a multi-year software service agreement be recognized?",
            "options": [
                "A) Immediately upon signing the contract",
                "B) Proportionately as performance obligations are satisfied over the service period",
                "C) Only after full cash payment is received and cleared",
                "D) At the conclusion of the final fiscal year"
            ],
            "correct_option": "B",
            "rubric_guideline": "Identifies ASC 606 / IFRS 15 revenue recognition upon satisfaction of performance obligations."
        })
        questions.append({
            "question_id": "TECH_Q2",
            "type": "short_answer",
            "competency_or_skill": "Financial Analysis & Variance",
            "prompt": "Describe the difference between operating cash flow and EBITDA. Why might a company report positive EBITDA but negative operating cash flow?",
            "rubric_guideline": "Explains non-cash working capital changes, inventory build-up, and timing of accounts receivable collections."
        })
        questions.append({
            "question_id": "TECH_Q3",
            "type": "case_analysis",
            "competency_or_skill": "Financial Modeling & Valuation",
            "prompt": "How do you determine the Weighted Average Cost of Capital (WACC) for a project, and how does capital structure affect the discount rate?",
            "rubric_guideline": "Formulates Cost of Equity (CAPM) and after-tax Cost of Debt weighted by enterprise value portions."
        })
        return questions

    # 3. Frontend & UI Engineering
    if any(s in skills_lower for s in ["react", "vue", "frontend", "ui", "javascript"]):
        questions.append({
            "question_id": "TECH_Q1",
            "type": "mcq",
            "competency_or_skill": "Modern Frontend Architecture",
            "prompt": "In React 18, what is the core architectural purpose of concurrent rendering transitions (`useTransition`)?",
            "options": [
                "A) To run CPU threads in Web Workers automatically",
                "B) To mark state updates as non-urgent so urgent user inputs remain responsive without stuttering",
                "C) To eliminate DOM diffing completely",
                "D) To execute network requests synchronously"
            ],
            "correct_option": "B",
            "rubric_guideline": "Understands concurrent rendering, interruptible transitions, and input prioritization."
        })
    # 4. Backend / Python / Java Engineering (Default)
    elif "java" in skills_lower:
        questions.append({
            "question_id": "TECH_Q1",
            "type": "mcq",
            "competency_or_skill": "Java",
            "prompt": "In Java, what is the key distinction between `Comparable` and `Comparator`?",
            "options": [
                "A) Comparable provides multiple sorting sequences, Comparator provides single",
                "B) Comparable is in java.util, Comparator is in java.lang",
                "C) Comparable modifies the class itself (compareTo), Comparator allows external custom sorting strategies (compare)",
                "D) There is no functional difference"
            ],
            "correct_option": "C",
            "rubric_guideline": "Distinguishes natural ordering (Comparable) vs external custom ordering (Comparator)."
        })
    else:
        questions.append({
            "question_id": "TECH_Q1",
            "type": "mcq",
            "competency_or_skill": skills[0] if skills else "Distributed Systems",
            "prompt": "What is the primary difference between Python's `asyncio` concurrency model and multi-threading?",
            "options": [
                "A) Asyncio uses OS threads while multi-threading is single-threaded",
                "B) Asyncio uses an event loop on a single thread with cooperative multitasking, bypassing GIL overhead for I/O",
                "C) Multi-threading in Python runs on all CPU cores simultaneously without any GIL locking",
                "D) Asyncio only works with file I/O, not network sockets"
            ],
            "correct_option": "B",
            "rubric_guideline": "Identifies cooperative single-threaded event loop vs OS threads."
        })

    # Technical Q2: Data / Architecture
    if any(s in skills_lower for s in ["sql", "postgresql", "database", "mysql"]) or "sql" in desc:
        questions.append({
            "question_id": "TECH_Q2",
            "type": "short_answer",
            "competency_or_skill": "SQL & Query Optimization",
            "prompt": "Write a SQL query to find the 2nd highest salary from an `employees` table, handling ties properly. Explain the index strategy needed for large tables.",
            "rubric_guideline": "Expects DENSE_RANK() OVER (ORDER BY salary DESC) or `SELECT DISTINCT salary ... ORDER BY salary DESC LIMIT 1 OFFSET 1` with index on salary."
        })
    else:
        questions.append({
            "question_id": "TECH_Q2",
            "type": "short_answer",
            "competency_or_skill": "System Architecture",
            "prompt": "Explain the difference between idempotent and non-idempotent HTTP methods, giving examples of each.",
            "rubric_guideline": "Defines idempotency (repeated identical requests yield same state). GET/PUT/DELETE are idempotent, POST is not."
        })

    # Technical Q3: Algorithms & Code
    questions.append({
        "question_id": "TECH_Q3",
        "type": "coding",
        "competency_or_skill": "Algorithms & Problem Solving",
        "prompt": "Write a clean function to detect if a directed graph contains a cycle. Explain its time and space complexity.",
        "rubric_guideline": "Implements DFS with 3-color states (unvisited, visiting/in-stack, visited) or Kahn's algorithm (Topological sort with in-degrees). Time complexity: O(V + E)."
    })

    return questions

def generate_behavioral_questions_for_jd(jd: Optional[JobDescription] = None) -> List[Dict[str, Any]]:
    """
    Generates role-anchored behavioral assessment questions targeting key workplace competencies.
    Anchored to the job title and department requirements using the STAR method.
    """
    role_ctx = f"as {jd.title}" if (jd and jd.title) else "in your previous role"
    dept_ctx = f"{jd.department} projects" if (jd and jd.department) else "complex cross-functional initiatives"

    return [
        {
            "question_id": "BEH_Q1",
            "type": "behavioral",
            "competency_or_skill": "Stakeholder Collaboration & Conflict Resolution",
            "prompt": f"Describe a situation {role_ctx} where you experienced a serious professional disagreement with a colleague or stakeholder regarding priorities. How did you structure the dialogue and what was the outcome?",
            "rubric_guideline": "Evaluates active listening, data-driven reasoning, empathy, collaborative conflict resolution, and commitment to shared organizational goals."
        },
        {
            "question_id": "BEH_Q2",
            "type": "behavioral",
            "competency_or_skill": "Navigating Ambiguity & Strategic Problem Solving",
            "prompt": f"Tell us about a complex, ambiguous challenge you tackled in {dept_ctx} where guidelines or specifications were incomplete. What structured steps did you take to deliver?",
            "rubric_guideline": "Evaluates structured decomposition, proactive requirement discovery, hypothesis testing, and incremental delivery."
        },
        {
            "question_id": "BEH_Q3",
            "type": "behavioral",
            "competency_or_skill": "Adaptability & Rapid Upskilling",
            "prompt": f"Describe an instance {role_ctx} where you had to master an unfamiliar methodology, system, or regulatory standard under a demanding deadline. How did you ensure high quality?",
            "rubric_guideline": "Measures speed of learning, disciplined time allocation, resilience, and quality verification."
        },
        {
            "question_id": "BEH_Q4",
            "type": "behavioral",
            "competency_or_skill": "Technical & Domain Communication",
            "prompt": f"Describe a project in {dept_ctx} where you needed to present sophisticated domain trade-offs or technical decisions to non-expert decision makers. How did you guarantee clarity and buy-in?",
            "rubric_guideline": "Focuses on empathy for non-technical audiences, structured simplification without inaccuracy, and confirming stakeholder alignment."
        }
    ]

def sanitize_questions_for_candidate(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Strips internal scoring keys (correct_option, rubric_guideline) before questions
    are delivered to the candidate browser/portal. Prevents client-side cheating via DevTools inspection.
    """
    sanitized = []
    for q in questions:
        q_copy = dict(q)
        q_copy.pop("correct_option", None)
        q_copy.pop("rubric_guideline", None)
        sanitized.append(q_copy)
    return sanitized

