# JASIPA engineering notes

Companion to the project report. Every statement here refers to code in this repository at the commit that adds this file.

## 1. Bias detection and cohort analysis — requirement status

Status reflects what was in the repository before this round of changes, and what was changed.

| Requirement | Before | Now | Where |
|---|---|---|---|
| Document how cohorts are defined and assigned | Partial: `cohort_tag` existed, but its meaning was not documented and Kaggle imports used the job category as a cohort | Implemented: HR-recorded monitoring label, never inferred from resume text, never sent to agents; missing/legacy values excluded and counted; Kaggle records have no cohort | `COHORT_DEFINITION` in `backend/app/services/bias_service.py`; `is_missing_cohort` in `fairness_stats.py`; returned by `GET /api/bias/analytics`; shown on the Bias monitor page |
| A selection-rate difference alone is not sufficient evidence | Not met: a significant rate difference within the four-fifths screen was still flagged as an indicator | Changed: only the four-fifths screen (ratio < 0.80, n ≥ 5 per cohort, valid reference) raises a warning; significance is reported as a note | `compare_groups` in `backend/app/services/fairness_stats.py` |
| Warn only when a defined screening criterion is triggered | Partial | Implemented: the screen above for selection rates; > 10-point score-floor gap with n ≥ 10 for thresholds; demographic/proxy terms for rationale language | `compare_groups`, `check_threshold_bias`, `check_decision_language` |
| Distinguish Disparity detected / No indicator detected / Insufficient data | Partial: four internal statuses, inconsistent labels | Implemented: `DISPLAY_STATUS` maps to the three states; significance is a separate qualifier ("statistically significant" / "not statistically significant") | `DISPLAY_STATUS`, `significance_label` in `fairness_stats.py`; `biasPresentation` in `frontend/src/lib/format.js` |
| Communicate sample-size limits and uncertainty | Implemented (min group size 5, Wilson intervals, fragility flag, power note under n = 30) | Kept | `compare_groups`, `wilson_interval` |
| Insufficient data never presented as fairness; non-significance never as absence of bias | Implemented in notes | Kept and stated in summaries and UI footers | `compare_groups` summaries; `BiasCheckCard` in `frontend/src/pages/CandidateDetail.jsx` |
| Auditability and human oversight; no automatic approve/reject | Implemented | Kept and tested (`test_bias_check_never_changes_scores_or_routing`) | `node_check_bias` in `backend/app/orchestration/workflow.py`; `submit_human_decision` in `backend/app/api/reviews.py` |

UI changes: the pool-wide summary used to be appended to every per-check reason, which caused the repeated explanations across AI recommendations, human decisions and post-hire outcomes. Reasons are now short and metric-based (`check_selection_rate`), and the Panel & Bias card shows one row per check with cohort, n, impact ratio and Fisher p, plus a single pool summary (`BiasCheckCard`).

## 2. How the agents learn — an honest assessment

**JASIPA does not learn.** No model is trained, fine-tuned or updated, and no reviewer decision, assessment result or hiring outcome changes how any agent behaves later.

What the repository actually contains:

| Mechanism | Present? | Details |
|---|---|---|
| Fixed rules / rubric-based scoring | Yes, the default | `RegexStrategy` (resume scoring with the rubric's anchored weights), answer-key MCQ scoring and sandboxed test execution in `SkillAssessorAgent`, `HeuristicStrategy` keyword rubric, `STARFrameworkStrategy`, deterministic weighted merge and routing in `PanelCoordinatorAgent`, and statistical checks in `fairness_stats.py` |
| LLM inference | Optional | `LLMService.call_llm` (`backend/app/agents/llm_factory.py`, Gemini over HTTPS, temperature 0.2) used by `LLMStrategy` for resume screening, open-ended technical answers, behavioral answers, question generation and the panel summary. Without `GEMINI_API_KEY` the LLM is skipped entirely. The LLM cannot change MCQ/coding scores, routing or bias results |
| Stored evaluation history | Yes, as records | Screening results, assessments, panel decisions, bias checks, human reviews, hiring outcomes and the hash-chained audit log |
| Memory used at run time | Limited | Previous panel rounds for the same candidate are passed to the Panel Coordinator (`history` in `run_candidate_pipeline` → `PanelCoordinatorAgent.synthesize`) and reported as context ("Previous round 1: merged score …"). They do not change scores or routing. Question sets and screening results are cached and reused |
| Retrieval | No | There is no vector store or retrieval of past cases |
| Feedback loop / training | No | Hiring outcomes (`/api/learning/*`) are descriptive analytics only. The UI and API state that they never modify rubrics, weights or decisions. Rubric changes are manual HR edits that create new versions |

**Why this architecture.** Hiring decisions require repeatability, explainability and protection from automated adverse decisions. Scores that decide routing are therefore produced by deterministic, inspectable code anchored to a versioned rubric, and LLM output is confined to tasks where language understanding helps (open answers, question drafting, summaries). Learning from past hiring outcomes would risk encoding historical bias and needs a validated, audited process; the stored outcome data is the foundation for that, but no such loop exists today.

**How a decision is produced.** Resume-Screener, Skill-Assessor and Culture-Fit run as parallel LangGraph nodes. The Panel Coordinator merges their scores with the rubric weights and routes to one of three labels, all of which go to a human reviewer. The bias checker records statistics against that panel decision. An HR reviewer, or two reviewers when the panel escalates, records the final decision through `/api/reviews/decide`, which is not exposed to any agent or MCP tool.

## 3. Assessment regeneration — root cause and fix

- **Symptom:** clicking *Regenerate* on a job's Assessment tab appeared to do nothing.
- **Root cause:** without an LLM, `build_template_questions` was fully deterministic. `POST /api/assessments/questions/{jd_id}/regenerate` saved a new `QuestionSet` with the same questions, and the UI reported success while nothing visibly changed.
- **Fix, backend:**
  - Generation now takes a `variant` (rotating skills, MCQ items, coding challenges and phrasing templates). With an LLM configured, it is also told not to repeat the current prompts.
  - `get_or_create_question_set(force_new=True)` saves only a set whose fingerprint differs from the current one; otherwise it raises `QuestionRegenerationError`.
  - The endpoint returns 409 when no different set exists and 502 when generation fails, keeping the current set in both cases. It also returns `changed_questions` and logs an audit event.
- **Fix, frontend:** `AssessmentPreview` in `frontend/src/pages/JobDescriptions.jsx` shows the returned set, reports "N of M questions changed", and shows an error with the old questions kept on failure.
- **Tests:** `test_regenerate_endpoint_returns_and_persists_a_different_set`, `test_regenerate_reports_failure_instead_of_false_success`, `test_applicants_keep_their_pinned_questions_after_regeneration`, three Vitest cases, and E2E-004.

## 4. Dataset

- **Source:** Kaggle Resume Dataset (`Resume.csv`, 2,484 rows; columns `ID`, `Resume_str`, `Resume_html`, `Category`; 24 categories). It contains no names, contact details, demographics or assessment answers.
- **Import:** `backend/app/services/dataset_import.py` loads six categories that have authored job descriptions, rebuilding section structure from `Resume_html`. Each record gets `source=dataset_import`, `external_id`, `dataset_category`, no cohort and a non-deliverable `@dataset.invalid` email.
- **Seed:** `scripts/seed_data.py` imports only these records and screens them. No synthetic candidates, answers, decisions or outcomes are created.
- **Consequence for demos:** dataset records have no assessments, so a full pipeline run on them returns `ADDITIONAL_INFORMATION_REQUIRED`. With no cohort labels, bias analyses report insufficient data. Both are accurate, not errors.

## 5. Demonstration readiness

**Start the system:**

```bash
cd backend && .venv/bin/python scripts/seed_data.py --demo-accounts && LLM_PROVIDER=mock .venv/bin/uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

**Suggested walkthrough (about 10 minutes):**

1. Sign in as `hr@jasipa.ai` / `admin123`; the dashboard shows 48 Kaggle records.
2. Open a dataset candidate: the Resume tab shows sections; *Run evaluation* gives "Incomplete evidence" (no assessments in the dataset); the Panel & bias tab shows the per-check table.
3. *Jobs → New job*: create a programming role (for example Python, SQL, Algorithms) so its assessment includes a sandboxed coding challenge. Use *Regenerate* to show a new set.
4. In a private window, register as a candidate (or use `student@jasipa.ai` / `student123`), upload a PDF or DOCX resume, apply to the new job, run the code examples, and submit both assessments.
5. As HR, run the evaluation for that candidate, review Assessments (hidden test results) and Panel & bias, then record a decision. If two reviewers are required, sign in as `reviewer@jasipa.ai` / `reviewer123` for the second sign-off.
6. *Audit log → Verify integrity*.

**Known constraints:**

| Item | Impact | Mitigation |
|---|---|---|
| No `GEMINI_API_KEY` | All agents run their deterministic strategies; questions come from the template generator | Expected for an offline demo; set the key and `LLM_PROVIDER=gemini` to show LLM paths |
| Python ≥ 3.10 and Node ≥ 18 required; Node 25 needs the in-memory storage shim already in `src/test/setup.js` for tests | Tests only | none needed |
| Port 5173 in use | Vite fails to start | `npx vite --port 5174` and add the origin to `CORS_ORIGINS` |
| `SECRET_KEY` unset | A random key per process: restarting the backend signs everyone out | Set `SECRET_KEY` in `.env` before the demo |
| Seed resets the database | Demo data created live is lost on reseed | Seed once before the demo |
| Subprocess sandbox | Defense in depth, not a hardened boundary | `SANDBOX_BACKEND=docker` with Docker running |
| No cohort labels in the dataset | Bias monitor shows "Insufficient data" | Expected; HR can enter cohort labels when uploading resumes |
| Playwright browsers | Needed only for `npm run test:e2e` | `npx playwright install chromium` |
