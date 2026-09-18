from typing import List, Dict, Any
from app.database.models import JobDescription

def generate_technical_questions_for_jd(jd: JobDescription) -> List[Dict[str, Any]]:
    """
    Generates a standardized technical assessment based on the JD's required skills.
    Question types: Multiple Choice (MCQ), Short Answer, and Coding Problem.
    """
    skills = jd.required_skills or ["Python", "SQL", "Data Structures"]
    questions = []
    
    # 1. Multiple Choice Questions
    if "Python" in skills or "FastAPI" in skills:
        questions.append({
            "question_id": "TECH_Q1",
            "type": "mcq",
            "competency_or_skill": "Python",
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
    elif "Java" in skills:
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
            "competency_or_skill": skills[0] if skills else "General CS",
            "prompt": f"Which of the following best describes memory management and execution in {skills[0] if skills else 'modern backend systems'}?",
            "options": [
                "A) Garbage collection runs deterministically at set clock cycles",
                "B) Stack memory is used for dynamic heap objects",
                "C) Stack handles local primitive variables and call frames, while Heap handles dynamically allocated objects",
                "D) Memory leaks cannot occur in managed runtimes"
            ],
            "correct_option": "C",
            "rubric_guideline": "Identifies Stack vs Heap memory allocation correctly."
        })

    # 2. Database / SQL Question
    if "SQL" in skills or "PostgreSQL" in skills or "Database" in jd.description:
        questions.append({
            "question_id": "TECH_Q2",
            "type": "short_answer",
            "competency_or_skill": "SQL / PostgreSQL",
            "prompt": "Write a SQL query to find the 2nd highest salary from an `employees` table, handling ties properly.",
            "rubric_guideline": "Expects DENSE_RANK() OVER (ORDER BY salary DESC) or `SELECT DISTINCT salary ... ORDER BY salary DESC LIMIT 1 OFFSET 1`."
        })
    else:
        questions.append({
            "question_id": "TECH_Q2",
            "type": "short_answer",
            "competency_or_skill": "API / Backend Architecture",
            "prompt": "Explain the difference between idempotent and non-idempotent HTTP methods, giving examples of each.",
            "rubric_guideline": "Defines idempotency (repeated identical requests yield same state). GET/PUT/DELETE are idempotent, POST is not."
        })

    # 3. Coding / Algorithmic Problem
    questions.append({
        "question_id": "TECH_Q3",
        "type": "coding",
        "competency_or_skill": "Data Structures & Algorithms",
        "prompt": "Write a clean function to detect if a directed graph contains a cycle. Explain its time complexity.",
        "rubric_guideline": "Implements DFS with 3-color states (unvisited, visiting/in-stack, visited) or Kahn's algorithm (Topological sort with in-degrees). Time complexity: O(V + E)."
    })

    return questions

def generate_behavioral_questions_for_jd() -> List[Dict[str, Any]]:
    """
    Generates standardized behavioral assessment questions targeting key workplace competencies.
    Does NOT infer personality from resumes; requires concrete candidate responses (STAR method).
    """
    return [
        {
            "question_id": "BEH_Q1",
            "type": "behavioral",
            "competency_or_skill": "Team Collaboration & Conflict Resolution",
            "prompt": "Describe a specific situation where you had a technical disagreement with a team member or stakeholder. How did you approach the discussion, and what was the outcome?",
            "rubric_guideline": "Looks for active listening, objective data-driven argumentation, empathy, collaborative resolution, and alignment on shared goals."
        },
        {
            "question_id": "BEH_Q2",
            "type": "behavioral",
            "competency_or_skill": "Problem Solving & Ambiguity",
            "prompt": "Tell us about a complex, ambiguous problem you faced in a project where requirements were incomplete. What steps did you take to decompose and solve it?",
            "rubric_guideline": "Evaluates structured reasoning, proactive requirement discovery, breaking problems down, and delivering iterative progress."
        },
        {
            "question_id": "BEH_Q3",
            "type": "behavioral",
            "competency_or_skill": "Adaptability & Continuous Learning",
            "prompt": "Describe a scenario where you had to quickly learn a completely new framework, technology, or domain under a tight deadline. How did you manage your time and ensure quality?",
            "rubric_guideline": "Examines rapid acquisition of skills, resilience, pragmatic prioritization, and verification of quality."
        },
        {
            "question_id": "BEH_Q4",
            "type": "behavioral",
            "competency_or_skill": "Technical Communication",
            "prompt": "Describe a project where you needed to communicate a complex architectural concept or technical tradeoff to non-technical stakeholders. How did you ensure clarity?",
            "rubric_guideline": "Focuses on empathy, removing jargon, using analogies or diagrams, and confirming understanding and buy-in."
        }
    ]
