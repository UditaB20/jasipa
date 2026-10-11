"""Shared test data and file builders."""
import io

STRONG_RESUME = """Jordan Rivera
Summary
Backend engineer with 6 years of experience building Python services and SQL data models.
Experience
Senior Software Engineer, Northwind (Jan 2021 - Present)
Built Python APIs, designed SQL schemas and implemented algorithms for billing.
Software Engineer, Contoso (2018 - 2020)
Education
B.Tech in Computer Science, National Institute of Technology, 2018
Projects
Payments reconciliation service processing 2M transactions per day.
Skills
Python, SQL, Algorithms, Docker, Git
"""

WEAK_RESUME = """Sam Lee
Summary
Retail associate with 1 year of experience in customer service.
Experience
Store Associate, Corner Shop (2023 - 2024)
Skills
Customer Service, Communication
"""


def make_pdf(text: str) -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 560, 800), text, fontsize=9)
    data = doc.tobytes()
    doc.close()
    return data


def make_docx(text: str) -> bytes:
    import docx
    document = docx.Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def answers_for(questions, quality, db, jd_id, test_type):
    """Builds answers through the public question list; coding answers use the stored reference solution."""
    from app.database.models import QuestionSet
    full = {q["question_id"]: q for qs in db.query(QuestionSet).filter(QuestionSet.jd_id == jd_id).all()
            for q in (qs.technical_questions or []) + (qs.behavioral_questions or [])}
    out = []
    for q in questions:
        key = full.get(q["question_id"], {})
        if q["type"] == "mcq":
            text = key.get("correct_option", "A") if quality == "strong" else ("D" if key.get("correct_option") != "D" else "A")
        elif q["type"] == "coding":
            text = key["coding"]["reference_solution"] if quality == "strong" else f"def {q['coding']['function_name']}(*a):\n    return None\n"
        elif q["type"] == "behavioral":
            text = ("Situation: during a release at my previous role the team missed a deadline. Task: I was responsible for recovery. "
                    "Action: I analyzed the root cause, I proposed a plan and I communicated trade-offs. Result: we delivered and reduced defects by 30%."
                    if quality in ("strong", "mixed") else "We worked it out.")
        else:
            text = ("My approach: clarify requirements, design the schema and services, compare two options and explain the trade-off, "
                    "then validate with tests, query plans and a review before rollout." if quality == "strong" else "I would do it.")
        out.append({"question_id": q["question_id"], "answer_text": text})
    return out
