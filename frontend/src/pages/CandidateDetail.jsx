import { useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, Download, FileText, Play, RefreshCw, Scale, UserCheck, XCircle, HelpCircle, Code2 } from "lucide-react";
import { downloadResume, getCandidate, getDecisionStatus, getJobs, runFullGraph, runScreenResume, submitDecision } from "../services/api";
import AuditTimeline from "../components/AuditTimeline";
import ResumeDocument from "../components/ResumeDocument";
import { fmtP, fmtRatio } from "../lib/format";
import {
  Alert, Badge, BiasBadge, BIAS, Card, DECISIONS, EmptyState, ErrorState, Field, PageHeader, PageLoading, RecommendationBadge,
  ScoreBar, Spinner, StageBadge, Tabs, fmtDateTime, fmtScore, latest, useAsync, useToast,
} from "../components/ui";

const CHECK_LABELS = {
  decision_rationale_language: "Rationale language",
  selection_rate_ai_recommendation: "AI recommendations",
  selection_rate_human_decision: "Final human decisions",
  outcome_based_fairness: "Post-hire outcomes",
  threshold_consistency: "Score thresholds",
};

export default function CandidateDetail({ candidateId, onDecision }) {
  const toast = useToast();
  const [tab, setTab] = useState("overview");
  const [running, setRunning] = useState(null);
  const { data, loading, error, reload } = useAsync(
    () => Promise.all([getCandidate(candidateId), getJobs(), getDecisionStatus(candidateId)]), [candidateId]);

  const view = useMemo(() => {
    if (!data) return null;
    const [c, jobs, decision] = data;
    const assessments = c.assessments || [];
    return {
      c, decision,
      job: jobs.find((j) => j.jd_id === c.target_jd_id),
      screening: latest(c.screening_results),
      tech: latest(assessments.filter((a) => a.test_type === "TECHNICAL")),
      beh: latest(assessments.filter((a) => a.test_type === "BEHAVIORAL")),
      panel: latest(c.panel_decisions),
      bias: latest(c.bias_checks),
      reviews: c.human_reviews || [],
      audit: [...(c.audit_logs || [])].sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0) || new Date(a.timestamp) - new Date(b.timestamp)),
    };
  }, [data]);

  if (loading && !data) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const { c, job, screening, tech, beh, panel, bias, decision } = view;
  const decided = c.current_stage === "DECIDED";

  const run = async (kind) => {
    setRunning(kind);
    try {
      if (kind === "pipeline") {
        const result = await runFullGraph(c.candidate_id);
        toast(`Evaluation complete (round ${result.round_number}). Ready for your decision.`);
        setTab("overview");
      } else {
        await runScreenResume(c.candidate_id);
        toast("Resume re-screened against the current rubric.");
      }
      await reload();
      onDecision?.();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setRunning(null);
    }
  };

  const saveResume = async () => {
    try {
      const blob = await downloadResume(c.candidate_id);
      const url = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement("a"), { href: url, download: c.resume_original_filename || "resume" });
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const awaiting = decision.can_decide;
  return (
    <div className="page">
      <PageHeader
        back={<a className="breadcrumb" href="#/candidates"><ArrowLeft size={13} />Candidates</a>}
        title={<span className="row wrap" style={{ gap: 10 }}>{c.name}<StageBadge stage={c.current_stage} />{c.source === "dataset_import" && <Badge tone="outline">Kaggle dataset</Badge>}</span>}
        subtitle={`${job ? job.title : "No application"} · ${c.source === "dataset_import" ? `dataset row ${c.external_id}` : c.email}${c.experience_years ? ` · ${c.experience_years} yrs experience` : ""}`}
        actions={!decided && (
          <>
            <button className="btn btn-secondary" disabled={!!running || !c.target_jd_id} onClick={() => run("screen")}>
              {running === "screen" ? <Spinner /> : <RefreshCw size={14} />}Re-screen resume
            </button>
            <button className="btn btn-primary" disabled={!!running || !c.target_jd_id} onClick={() => run("pipeline")}
              title="Runs resume, skill and behavioral agents, the panel and the bias check">
              {running === "pipeline" ? <Spinner /> : <Play size={14} />}{panel ? "Re-run evaluation" : "Run evaluation"}
            </button>
          </>
        )}
      />

      {awaiting && (
        <div className="mb-16">
          <Alert tone="warning" title="Waiting for a human decision"
            action={tab !== "decision" && <button className="btn btn-secondary btn-sm" onClick={() => setTab("decision")}>Review and decide</button>}>
            {decision.requires_two_reviewers ? "This decision needs two different reviewers who agree. " : ""}
            The panel recommendation and its bias check are ready.
          </Alert>
        </div>
      )}
      {c.current_stage === "INFO_REQUESTED" && <div className="mb-16"><Alert tone="info" title="More information requested">Re-run the evaluation once the new evidence (for example a follow-up assessment) is in.</Alert></div>}
      {c.current_stage === "MANUAL_REVIEW_REQUIRED" && <div className="mb-16"><Alert tone="danger" title="Resume needs manual review">Text extraction confidence was low. Check the resume before screening.</Alert></div>}

      <Tabs active={tab} onChange={setTab} tabs={[
        { id: "overview", label: "Overview" },
        { id: "resume", label: "Resume" },
        { id: "assessments", label: "Assessments" },
        { id: "panel", label: "Panel & bias check" },
        { id: "decision", label: "Decision", badge: awaiting ? "Action" : null, badgeTone: "warning" },
        { id: "history", label: "History" },
      ]} />

      {tab === "overview" && <Overview {...{ c, screening, tech, beh, panel, bias, decision, setTab }} />}
      {tab === "resume" && <ResumeTab c={c} screening={screening} onDownload={saveResume} />}
      {tab === "assessments" && <AssessmentsTab tech={tech} beh={beh} />}
      {tab === "panel" && <PanelTab panel={panel} bias={bias} />}
      {tab === "decision" && <DecisionTab c={c} panel={panel} bias={bias} status={decision} reviews={view.reviews}
        onDone={async () => { await reload(); onDecision?.(); }} />}
      {tab === "history" && <Card title="History" subtitle="Every agent output and human action recorded in the tamper-evident audit log."><AuditTimeline entries={view.audit} /></Card>}
    </div>
  );
}

function Overview({ c, screening, tech, beh, panel, bias, decision, setTab }) {
  const finalReview = decision.signoffs.filter((s) => s.is_final).at(-1);
  return (
    <div className="split">
      <div className="stack">
        <Card title="Evaluation summary" subtitle={panel ? `Round ${panel.round_number || 1} · rubric v${panel.rubric_version}` : "Not evaluated yet"}>
          {!panel && !screening ? (
            <EmptyState icon={Play} title="No evaluation yet">
              {c.target_jd_id ? "Run the evaluation to screen the resume and merge any submitted assessments." : "This candidate has not applied to a job."}
            </EmptyState>
          ) : (
            <div className="stack">
              {panel && (
                <div className="row-between wrap">
                  <div><div className="xs dim">Panel score</div><div className="score-big">{fmtScore(panel.merged_score)}</div></div>
                  <div className="row"><RecommendationBadge value={panel.recommendation} />{bias && <BiasBadge value={bias.flag_status} />}</div>
                </div>
              )}
              <div className="stack-sm">
                <ScoreBar label="Resume" value={panel?.resume_score ?? screening?.score} />
                <ScoreBar label="Technical" value={panel ? panel.skill_score : tech?.score} />
                <ScoreBar label="Behavioral" value={panel ? panel.culture_score : beh?.score} />
              </div>
              {panel?.natural_language_summary && <p className="muted small">{panel.natural_language_summary}</p>}
            </div>
          )}
        </Card>
        {panel && (
          <div className="grid grid-2">
            <Card title="Strengths"><ul className="list">{panel.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul></Card>
            <Card title="Gaps"><ul className="list">{panel.gaps.map((s, i) => <li key={i}>{s}</li>)}</ul></Card>
          </div>
        )}
        {panel?.disagreements?.length > 0 && (
          <Card title="Points for the reviewer"><ul className="list">{panel.disagreements.map((s, i) => <li key={i}>{s}</li>)}</ul></Card>
        )}
      </div>
      <div className="stack">
        <Card title="Decision">
          {finalReview ? (
            <div className="stack-sm">
              <Badge tone={DECISIONS[finalReview.decision]?.tone}>{DECISIONS[finalReview.decision]?.label}</Badge>
              <p className="small">{finalReview.notes}</p>
              <p className="xs dim">{finalReview.reviewer_name} · {fmtDateTime(finalReview.timestamp)}</p>
            </div>
          ) : (
            <div className="stack-sm">
              <p className="muted small">{decision.blocking_reason || "Ready for a decision."}</p>
              {decision.can_decide && <button className="btn btn-primary btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => setTab("decision")}><UserCheck size={14} />Review and decide</button>}
            </div>
          )}
        </Card>
        <Card title="Profile">
          <dl className="kv">
            <dt>Education</dt><dd>{c.education || "—"}</dd>
            <dt>Experience</dt><dd className="num">{c.experience_years ? `${c.experience_years} years` : "Not stated"}</dd>
            <dt>Skills found</dt><dd><div className="chips">{(c.skills_extracted || []).map((s) => <span key={s} className="chip">{s}</span>)}</div></dd>
            <dt>Monitoring cohort</dt><dd className="muted">{c.cohort_tag || "Not recorded"}</dd>
          </dl>
        </Card>
      </div>
    </div>
  );
}

function ResumeTab({ c, screening, onDownload }) {
  const p = c.resume_profile || {};
  if (!c.resume_text) return <Card><EmptyState icon={FileText} title="No resume on file">Ask the candidate to upload one in the portal, or add it from the candidates list.</EmptyState></Card>;
  const fromDataset = c.source === "dataset_import";
  const subtitle = fromDataset ? `Imported from the Kaggle Resume Dataset · row ${c.external_id} · category ${c.dataset_category}`
    : c.resume_original_filename ? `${c.resume_original_filename}${p.extraction_confidence != null ? ` · extraction confidence ${Math.round(p.extraction_confidence * 100)}%` : ""}`
    : "Entered as text";
  return (
    <div className="split">
      <Card title="Resume" subtitle={subtitle}
        actions={c.has_original_file && <button className="btn btn-secondary btn-sm" onClick={onDownload}><Download size={13} />Download original</button>}>
        <ResumeDocument sections={c.resume_sections} text={c.resume_text} />
        {fromDataset && <p className="xs dim mt-16">Dataset records have no uploaded file; the text is rebuilt from the dataset's HTML resume.</p>}
      </Card>
      <div className="stack">
        {screening && (
          <Card title="Screening against the job" subtitle={`Score ${fmtScore(screening.score)} · rubric v${screening.rubric_version}`}>
            <div className="stack-sm">
              <div className="xs dim">Required skills found</div>
              <div className="chips">{screening.matched_requirements.map((s) => <span key={s} className="chip chip-success">{s}</span>)}{!screening.matched_requirements.length && <span className="dim small">None</span>}</div>
              {screening.missing_requirements.length > 0 && <><div className="xs dim mt-8">Not evidenced</div>
                <div className="chips">{screening.missing_requirements.map((s) => <span key={s} className="chip chip-danger">{s}</span>)}</div></>}
              <ul className="list mt-8">{screening.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
            </div>
          </Card>
        )}
        <Card title="Extracted details">
          <dl className="kv">
            <dt>Experience</dt><dd>{p.experience_years ? `${p.experience_years} years (${p.experience_source === "stated" ? "stated" : "from dates"})` : "Not found"}</dd>
            <dt>Education</dt><dd>{(p.education || []).length ? <ul className="list">{p.education.map((e, i) => <li key={i}>{e}</li>)}</ul> : "—"}</dd>
            <dt>Projects</dt><dd>{(p.projects || []).length ? <ul className="list">{p.projects.map((e, i) => <li key={i}>{e}</li>)}</ul> : "—"}</dd>
          </dl>
        </Card>
      </div>
    </div>
  );
}

function AssessmentsTab({ tech, beh }) {
  if (!tech && !beh) return <Card><EmptyState icon={FileText} title="No assessments submitted">The candidate completes the technical and behavioral assessments in the portal.</EmptyState></Card>;
  return (
    <div className="stack">
      {tech && <AssessmentCard title="Technical assessment" a={tech} />}
      {beh && <AssessmentCard title="Behavioral assessment (STAR)" a={beh} />}
    </div>
  );
}

function AssessmentCard({ title, a }) {
  const answers = Object.fromEntries((a.answers || []).map((x) => [x.question_id, x.answer_text]));
  const exec = a.execution_results || {};
  return (
    <Card title={title} subtitle={`Submitted ${fmtDateTime(a.completed_date)} · scored by ${a.strategy_used || "agent"}`}
      actions={<div className="row"><span className="num" style={{ fontWeight: 600, fontSize: 18 }}>{fmtScore(a.score)}</span>
        {a.status !== "COMPLETED" && <Badge tone="warning">{a.status.replace(/_/g, " ").toLowerCase()}</Badge>}</div>}>
      <div className="stack">
        {Object.keys(a.skill_breakdown || {}).length > 0 && (
          <div className="stack-sm">{Object.entries(a.skill_breakdown).map(([k, v]) => <ScoreBar key={k} label={k.replace(/_/g, " ")} value={v} />)}</div>
        )}
        {(a.questions || []).map((q, i) => (
          <div key={q.question_id} className="inset">
            <div className="row-between wrap">
              <div className="row small"><Badge>{q.type === "mcq" ? "Multiple choice" : q.type === "coding" ? "Coding" : q.type === "behavioral" ? "STAR" : "Scenario"}</Badge><span className="dim">{q.competency_or_skill}</span></div>
              <span className="xs dim">Q{i + 1}</span>
            </div>
            <p className="small mt-8">{q.prompt}</p>
            {q.type === "mcq" && <p className="small mt-8">Answer: <strong>{answers[q.question_id] || "—"}</strong> · key {q.correct_option}</p>}
            {q.type === "coding" ? (
              <>
                <pre className="block mt-8">{answers[q.question_id] || "No code submitted"}</pre>
                {exec[q.question_id] && <ExecutionSummary result={exec[q.question_id]} />}
              </>
            ) : q.type !== "mcq" && <p className="small muted mt-8" style={{ whiteSpace: "pre-wrap" }}>{answers[q.question_id] || <em>Not answered</em>}</p>}
          </div>
        ))}
        {a.evidence?.length > 0 && <div><div className="section-title">Scoring evidence</div><ul className="list">{a.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
      </div>
    </Card>
  );
}

function ExecutionSummary({ result }) {
  const ok = result.status === "OK";
  return (
    <div className="mt-8 stack-sm">
      <div className="row small"><Code2 size={14} />
        {ok ? <span><strong className="num">{result.passed}/{result.total}</strong> sandboxed tests passed ({result.tests.filter((t) => t.hidden).length} hidden)</span>
          : <span className="text-danger">{result.status.replace(/_/g, " ").toLowerCase()}: {result.compile_error || result.error}</span>}
      </div>
      {ok && (
        <div className="chips">
          {result.tests.map((t) => (
            <span key={t.index} className={`chip ${t.passed ? "chip-success" : "chip-danger"}`} title={t.error || "passed"}>
              {t.passed ? <CheckCircle2 size={12} /> : <XCircle size={12} />}{t.hidden ? "hidden" : "example"} {t.index + 1}{t.error && t.error !== "Wrong answer" ? ` · ${t.error}` : ""}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function PanelTab({ panel, bias }) {
  if (!panel) return <Card><EmptyState icon={Scale} title="No panel evaluation yet">Run the evaluation to merge the three agents' scores and record a bias check.</EmptyState></Card>;
  return (
    <div className="stack">
      <Card title="Panel recommendation" subtitle={`Round ${panel.round_number || 1} · ${fmtDateTime(panel.created_at)}`}
        actions={<div className="row"><RecommendationBadge value={panel.recommendation} />{panel.requires_four_eyes_review && <Badge tone="warning">Two reviewers required</Badge>}</div>}>
        <div className="grid grid-2">
          <div className="stack-sm">
            <ScoreBar label="Resume" value={panel.resume_score} />
            <ScoreBar label="Technical" value={panel.skill_score} />
            <ScoreBar label="Behavioral" value={panel.culture_score} />
            <ScoreBar label="Merged" value={panel.merged_score} />
          </div>
          <div><div className="section-title">Evidence cited</div><ul className="list">{panel.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul></div>
        </div>
      </Card>
      <BiasCheckCard bias={bias} />
    </div>
  );
}

export function BiasCheckCard({ bias }) {
  if (!bias) return <Card title="Bias check"><p className="muted small">No bias check is recorded for this panel decision.</p></Card>;
  const breakdown = bias.cohort_breakdown || {};
  const checks = breakdown.checks || [];
  const pool = checks.find((c) => c.pool_summary && ["STATISTICALLY_SUPPORTED_DISPARITY", "POTENTIAL_DISPARITY_INDICATOR"].includes(c.pool_status));
  const cohort = breakdown.candidate_cohort;
  return (
    <Card title="Bias check for this decision" subtitle={`${fmtDateTime(bias.created_at)} · candidate cohort: ${cohort || "not recorded"}`}
      actions={<BiasBadge value={bias.flag_status} showQualifier />} pad={false}>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Check</th><th>Result</th><th>Cohort</th><th className="right">n</th><th className="right">Impact ratio</th><th className="right">Fisher p</th></tr></thead>
          <tbody>
            {checks.map((check) => {
              const g = check.group;
              return (
                <tr key={check.check_type} title={check.reason}>
                  <td className="cell-title">{CHECK_LABELS[check.check_type] || check.check_type}</td>
                  <td><BiasBadge value={check.flag_status} checkType={check.check_type} showQualifier /></td>
                  <td className="muted">{g?.cohort_name || "—"}</td>
                  <td className="right num">{g ? g.n : check.check_type === "decision_rationale_language" ? "—" : check.sample_size ?? "—"}</td>
                  <td className="right num">{fmtRatio(g?.impact_ratio)}</td>
                  <td className="right num">{fmtP(g?.fisher_p_value)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="card-body stack-sm" style={{ borderTop: "1px solid var(--border)" }}>
        {pool && <p className="small"><strong>Pool-wide:</strong> {pool.pool_summary}</p>}
        <p className="xs dim">A disparity is reported only when the four-fifths screen is triggered with at least the minimum cohort size; significance is shown as a qualifier. Insufficient data is not evidence of fairness. Bias checks never change scores, routing or decisions. Hover a row for its detail.</p>
      </div>
    </Card>
  );
}

function DecisionTab({ c, panel, bias, status, reviews, onDone }) {
  const toast = useToast();
  const [notes, setNotes] = useState("");
  const [choice, setChoice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const pending = status.signoffs.filter((s) => !s.is_final);

  const submit = async () => {
    if (!choice) return setError("Choose a decision.");
    if (notes.trim().length < 10) return setError("Explain the decision in at least 10 characters; the note is stored in the audit log.");
    setBusy(true);
    setError(null);
    try {
      const res = await submitDecision({ candidate_id: c.candidate_id, decision: choice, notes: notes.trim(), decision_id: status.decision_id });
      toast(res.outcome === "FINAL" ? "Decision recorded." : res.outcome === "AWAITING_SECOND_REVIEWER" ? "Sign-off recorded. A second reviewer must confirm." : "Sign-off recorded. Reviewers disagree; another reviewer must agree with one decision.");
      setNotes("");
      setChoice(null);
      await onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="split">
      <Card title="Record decision" subtitle="Approve or reject closes the application. Requesting information keeps it open.">
        {!status.can_decide ? (
          <Alert tone="info">{status.blocking_reason}</Alert>
        ) : (
          <div className="stack">
            {status.requires_two_reviewers && (
              <Alert tone="warning" title="Two reviewers required">
                The panel escalated this candidate. Approve or reject takes effect when two different HR reviewers agree.
                {pending.length > 0 && ` Current sign-offs: ${pending.map((s) => `${s.reviewer_name} (${DECISIONS[s.decision]?.label})`).join(", ")}.`}
              </Alert>
            )}
            {bias && (bias.flag_status === "POTENTIAL_DISPARITY_INDICATOR" || bias.flag_status === "STATISTICALLY_SUPPORTED_DISPARITY") && (
              <Alert tone={bias.flag_status === "STATISTICALLY_SUPPORTED_DISPARITY" ? "danger" : "warning"} title={`Bias check: ${BIAS[bias.flag_status].label.toLowerCase()}`}>
                {bias.reason}
              </Alert>
            )}
            <div className="grid grid-3" role="radiogroup" aria-label="Decision">
              {[["APPROVE", CheckCircle2, "Approve"], ["REJECT", XCircle, "Do not proceed"], ["REQUEST_MORE_INFORMATION", HelpCircle, "Request information"]].map(([value, Icon, label]) => (
                <label key={value} className={`option ${choice === value ? "selected" : ""}`}>
                  <input type="radio" name="decision" value={value} checked={choice === value} onChange={() => setChoice(value)} />
                  <span className="row small" style={{ fontWeight: 550 }}><Icon size={15} />{label}</span>
                </label>
              ))}
            </div>
            <Field label="Reason for the decision" hint="Refer to job-related evidence. Stored with the panel decision and bias check.">
              <textarea className="textarea" value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={4000} />
            </Field>
            {error && <div className="field-error">{error}</div>}
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button className="btn btn-primary" onClick={submit} disabled={busy}>{busy && <Spinner />}Record decision</button>
            </div>
          </div>
        )}
      </Card>
      <div className="stack">
        <Card title="What this decision is based on">
          {panel ? (
            <dl className="kv">
              <dt>Panel score</dt><dd className="num">{fmtScore(panel.merged_score)} (round {panel.round_number || 1})</dd>
              <dt>Recommendation</dt><dd><RecommendationBadge value={panel.recommendation} /></dd>
              <dt>Bias check</dt><dd><BiasBadge value={bias?.flag_status} /></dd>
            </dl>
          ) : <p className="muted small">No panel evaluation yet.</p>}
        </Card>
        <Card title="Sign-offs">
          {reviews.length === 0 ? <p className="muted small">No decisions recorded.</p> : (
            <div className="stack-sm">
              {reviews.slice().reverse().map((r) => (
                <div key={r.review_id} className="inset">
                  <div className="row-between"><Badge tone={DECISIONS[r.decision]?.tone}>{DECISIONS[r.decision]?.label}</Badge>{r.is_final === false && <span className="xs dim">first sign-off</span>}</div>
                  <p className="small mt-8">{r.notes}</p>
                  <p className="xs dim mt-4">{r.reviewer_name} · {fmtDateTime(r.timestamp)}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
