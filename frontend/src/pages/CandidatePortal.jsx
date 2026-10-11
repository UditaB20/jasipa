import { useState } from "react";
import { Briefcase, CheckCircle2, FileText, Play, Send, Upload } from "lucide-react";
import {
  applyCandidateJob, getCandidateAssessments, getCandidateJobs, getCandidateProfile, getCandidateTimeline,
  runSampleTests, submitCandidateBehavioral, submitCandidateTechnical, updateCandidateProfile, uploadCandidateResume,
} from "../services/api";
import { Alert, Badge, Card, EmptyState, ErrorState, Field, PageHeader, PageLoading, Spinner, useAsync, useToast } from "../components/ui";
import { ResumeDropzone, validateResumeFile } from "./CandidatesList";

export default function CandidatePortal({ section }) {
  const { data, loading, error, reload } = useAsync(
    () => Promise.all([getCandidateProfile(), getCandidateTimeline(), getCandidateJobs()]), []);
  if (loading && !data) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const [profile, timeline, jobs] = data;
  const job = jobs.find((j) => j.jd_id === profile.target_jd_id);

  if (section === "jobs") return <JobsSection profile={profile} jobs={jobs} onChange={reload} />;
  if (section === "assessments") return <AssessmentsSection onChange={reload} />;
  if (section === "profile") return <ProfileSection profile={profile} onChange={reload} />;
  return <Overview profile={profile} timeline={timeline} job={job} />;
}

function Overview({ profile, timeline, job }) {
  const first = profile.name.split(" ")[0];
  const steps = timeline.timeline;
  const next = !profile.has_resume ? { text: "Upload your resume so we can match you to roles.", href: "#/profile", cta: "Upload resume" }
    : !job ? { text: "Browse open roles and apply to the one that fits you.", href: "#/jobs", cta: "Browse roles" }
    : ["APPLIED", "RESUME_SCREENED", "TECHNICAL_ASSESSED"].includes(profile.current_stage) ? { text: "Complete your assessments so the hiring team can review your application.", href: "#/assessments", cta: "Open assessments" }
    : null;
  return (
    <div className="page page-narrow">
      <PageHeader title={`Hello, ${first}`} subtitle={job ? `Your application for ${job.title}` : "You have not applied to a role yet."} />
      {next && <div className="mb-16"><Alert tone="info" title="Next step" action={<a className="btn btn-primary btn-sm" href={next.href}>{next.cta}</a>}>{next.text}</Alert></div>}
      {timeline.info_requested && <div className="mb-16"><Alert tone="warning" title="The hiring team asked for more information">A recruiter will contact you about the next step.</Alert></div>}
      {job && (
        <Card title="Application progress">
          <div className="steps">
            {steps.map((s) => (
              <div key={s.stage} className={`step ${s.status === "COMPLETED" ? "done" : s.status === "CURRENT" ? "current" : ""}`}>
                <div className="step-bar" /><span>{s.label}</span>
              </div>
            ))}
          </div>
          <p className="xs dim mt-16">Automated scoring helps the hiring team compare applications, but a person reviews every application and makes the decision.</p>
        </Card>
      )}
    </div>
  );
}

function JobsSection({ profile, jobs, onChange }) {
  const toast = useToast();
  const [applying, setApplying] = useState(null);
  const [open, setOpen] = useState(null);
  const locked = profile.target_jd_id && !["REGISTERED", "APPLIED", "MANUAL_REVIEW_REQUIRED"].includes(profile.current_stage);

  const apply = async (job) => {
    setApplying(job.jd_id);
    try {
      await applyCandidateJob(job.jd_id);
      toast(`Application submitted for ${job.title}.`);
      await onChange();
      window.location.hash = "/assessments";
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setApplying(null);
    }
  };

  return (
    <div className="page page-narrow">
      <PageHeader title="Open roles" subtitle="Applying uses the resume on your profile." />
      {!profile.has_resume && <div className="mb-16"><Alert tone="info" action={<a className="btn btn-secondary btn-sm" href="#/profile">Upload resume</a>}>Upload your resume before applying.</Alert></div>}
      {jobs.length === 0 ? <Card><EmptyState icon={Briefcase} title="No open roles right now">Check back soon.</EmptyState></Card> : (
        <div className="stack">
          {jobs.map((job) => {
            const current = job.jd_id === profile.target_jd_id;
            return (
              <Card key={job.jd_id} title={job.title} subtitle={`${job.department} · ${job.min_experience}+ years`}
                actions={current ? <Badge tone="success">Applied</Badge> : (
                  <button className="btn btn-primary btn-sm" disabled={!profile.has_resume || locked || applying} onClick={() => apply(job)}>
                    {applying === job.jd_id && <Spinner />}Apply
                  </button>)}>
                <p className="small muted" style={{ whiteSpace: "pre-wrap" }}>{open === job.jd_id ? job.description : job.description.split("\n")[0]}</p>
                <div className="chips mt-12">{job.required_skills.map((s) => <span key={s} className="chip">{s}</span>)}</div>
                {job.description.includes("\n") && <button className="link-btn small mt-8" onClick={() => setOpen(open === job.jd_id ? null : job.jd_id)}>{open === job.jd_id ? "Show less" : "Full description"}</button>}
              </Card>
            );
          })}
          {locked && <p className="xs dim">You already have an application in progress. Contact the recruiter to change roles.</p>}
        </div>
      )}
    </div>
  );
}

function AssessmentsSection({ onChange }) {
  const { data, loading, error, reload } = useAsync(getCandidateAssessments, []);
  if (loading && !data) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data.available) {
    return (
      <div className="page page-narrow">
        <PageHeader title="Assessments" />
        <Card><EmptyState icon={FileText} title="Apply to a role first" action={<a className="btn btn-primary" href="#/jobs">Browse roles</a>}>
          Your assessments are generated for the role you apply to.
        </EmptyState></Card>
      </div>
    );
  }
  const done = async () => { await reload(); await onChange(); };
  return (
    <div className="page page-narrow">
      <PageHeader title="Assessments" subtitle={`For ${data.job_title}. Every applicant to this role answers the same questions. Each part can be submitted once.`} />
      <div className="stack">
        <AssessmentForm kind="technical" title="Technical assessment" part={data.technical} onSubmitted={done} />
        <AssessmentForm kind="behavioral" title="Behavioral assessment" part={data.behavioral} onSubmitted={done} />
      </div>
    </div>
  );
}

function AssessmentForm({ kind, title, part, onSubmitted }) {
  const toast = useToast();
  const [answers, setAnswers] = useState(() => Object.fromEntries(part.questions.map((q) => [q.question_id, q.coding?.starter_code || ""])));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (id, value) => setAnswers((a) => ({ ...a, [id]: value }));

  if (part.completed) {
    return <Card title={title} actions={<Badge tone="success"><CheckCircle2 size={12} />Submitted</Badge>}><p className="muted small">Your answers were received. The hiring team reviews them together with your resume.</p></Card>;
  }

  const unanswered = part.questions.filter((q) => !String(answers[q.question_id] || "").trim() || answers[q.question_id] === q.coding?.starter_code).length;
  const submit = async () => {
    if (unanswered && !window.confirm(`${unanswered} question(s) are unanswered. Submit anyway? You cannot change answers afterwards.`)) return;
    setBusy(true);
    setError(null);
    const payload = part.questions.map((q) => ({ question_id: q.question_id, answer_text: answers[q.question_id] || "" }));
    try {
      await (kind === "technical" ? submitCandidateTechnical(payload) : submitCandidateBehavioral(payload));
      toast(`${title} submitted.`);
      await onSubmitted();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={title} subtitle={kind === "behavioral" ? "Describe real situations: the Situation, your Task, the Actions you took and the Result." : `${part.questions.length} questions`}>
      <div className="stack">
        {part.questions.map((q, i) => (
          <div key={q.question_id} className="inset">
            <div className="row-between wrap mb-16" style={{ marginBottom: 8 }}>
              <span className="xs dim">Question {i + 1} of {part.questions.length} · {q.competency_or_skill}</span>
              <Badge>{q.type === "mcq" ? "Choose one" : q.type === "coding" ? "Python" : q.type === "behavioral" ? "STAR answer" : "Written answer"}</Badge>
            </div>
            {q.title && <div style={{ fontWeight: 600 }} className="mb-4">{q.title}</div>}
            <p className="small" style={{ whiteSpace: "pre-wrap" }}>{q.prompt}</p>
            <div className="mt-12">
              {q.type === "mcq" ? (
                <div className="stack-sm" role="radiogroup">
                  {q.options.map((opt) => {
                    const letter = opt.slice(0, 1);
                    return (
                      <label key={opt} className={`option ${answers[q.question_id] === letter ? "selected" : ""}`}>
                        <input type="radio" name={q.question_id} checked={answers[q.question_id] === letter} onChange={() => set(q.question_id, letter)} />
                        <span className="small">{opt}</span>
                      </label>
                    );
                  })}
                </div>
              ) : q.type === "coding" ? (
                <CodingQuestion q={q} value={answers[q.question_id]} onChange={(v) => set(q.question_id, v)} />
              ) : (
                <textarea className="textarea" rows={kind === "behavioral" ? 7 : 5} value={answers[q.question_id]} maxLength={20000}
                  onChange={(e) => set(q.question_id, e.target.value)} aria-label={`Answer to question ${i + 1}`}
                  placeholder={kind === "behavioral" ? "Situation… Task… Action… Result…" : ""} />
              )}
            </div>
          </div>
        ))}
        {error && <Alert tone="danger">{error}</Alert>}
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <span className="xs dim">{unanswered ? `${unanswered} unanswered` : "All questions answered"}</span>
          <button className="btn btn-primary" onClick={submit} disabled={busy}>{busy ? <Spinner /> : <Send size={14} />}Submit {kind} assessment</button>
        </div>
      </div>
    </Card>
  );
}

function CodingQuestion({ q, value, onChange }) {
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const run = async () => {
    setRunning(true);
    try {
      setResult(await runSampleTests(q.question_id, value));
    } catch (err) {
      setResult({ status: "ERROR", error: err.message, tests: [] });
    } finally {
      setRunning(false);
    }
  };
  const onKeyDown = (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const { selectionStart: s, selectionEnd: end } = e.target;
      onChange(value.slice(0, s) + "    " + value.slice(end));
      requestAnimationFrame(() => { e.target.selectionStart = e.target.selectionEnd = s + 4; });
    }
  };
  return (
    <div className="stack-sm">
      <div className="xs dim">Examples</div>
      {q.coding.examples.map((ex, i) => (
        <div key={i} className="mono xs muted">{q.coding.function_name}({ex.args.map((a) => JSON.stringify(a)).join(", ")}) → {JSON.stringify(ex.expected)}</div>
      ))}
      <textarea className="textarea code-editor" value={value} onChange={(e) => onChange(e.target.value)} onKeyDown={onKeyDown}
        spellCheck={false} aria-label="Code editor" />
      <div className="row-between wrap">
        <span className="xs dim">Your code also runs against {q.coding.hidden_test_count} hidden tests when you submit. Standard library only; no file or network access.</span>
        <button className="btn btn-secondary btn-sm" onClick={run} disabled={running}>{running ? <Spinner /> : <Play size={13} />}Run examples</button>
      </div>
      {result && (
        result.status === "OK" ? (
          <Alert tone={result.passed === result.total ? "success" : "warning"} title={`${result.passed} of ${result.total} examples passed`}>
            {result.tests.filter((t) => !t.passed).map((t) => (
              <div key={t.index} className="mono xs">Example {t.index + 1}: {t.error}{t.actual !== undefined ? ` (returned ${JSON.stringify(t.actual)})` : ""}</div>
            ))}
            {result.runs_remaining != null && <div className="xs dim mt-4">{result.runs_remaining} practice runs left</div>}
          </Alert>
        ) : <Alert tone="danger" title={result.status === "COMPILE_ERROR" ? "Syntax error" : "Could not run"}>{result.compile_error || result.error}</Alert>
      )}
    </div>
  );
}

function ProfileSection({ profile, onChange }) {
  const toast = useToast();
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [contact, setContact] = useState({ name: profile.name, phone: profile.phone || "" });
  const [saving, setSaving] = useState(false);
  const p = profile.resume_profile || {};
  const locked = ["PANEL_EVALUATED", "BIAS_CHECKED", "HUMAN_REVIEW_PENDING", "INFO_REQUESTED", "DECIDED"].includes(profile.current_stage);

  const upload = async () => {
    const problem = validateResumeFile(file);
    if (problem) return setFileError(problem);
    setUploading(true);
    setFileError(null);
    try {
      const res = await uploadCandidateResume(file);
      toast(res.parse_status === "PARSED" ? "Resume uploaded and read." : "Resume uploaded. Some text was hard to read, so a recruiter will check it.");
      setFile(null);
      await onChange();
    } catch (err) {
      setFileError(err.message);
    } finally {
      setUploading(false);
    }
  };
  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateCandidateProfile(contact);
      toast("Contact details saved.");
      await onChange();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page page-narrow">
      <PageHeader title="Profile & resume" />
      <div className="stack">
        <Card title="Resume" subtitle={profile.resume_filename ? `Current file: ${profile.resume_filename}` : "No resume uploaded yet"}>
          {locked ? <Alert tone="info">Your application is under review, so your resume can no longer be changed. Contact the recruiter if something is wrong.</Alert> : (
            <div className="stack">
              <ResumeDropzone file={file} onFile={(f) => { setFile(f); setFileError(validateResumeFile(f)); }} disabled={uploading} />
              {fileError && <div className="field-error">{fileError}</div>}
              <div className="row" style={{ justifyContent: "flex-end" }}>
                <button className="btn btn-primary" onClick={upload} disabled={!file || uploading}>{uploading ? <Spinner /> : <Upload size={14} />}{profile.has_resume ? "Replace resume" : "Upload resume"}</button>
              </div>
            </div>
          )}
          {profile.has_resume && (
            <>
              <hr className="divider" />
              <div className="section-title">What we read from your resume</div>
              <dl className="kv">
                <dt>Skills</dt><dd><div className="chips">{(profile.skills_extracted || []).map((s) => <span key={s} className="chip">{s}</span>)}{!profile.skills_extracted?.length && <span className="dim">None recognised</span>}</div></dd>
                <dt>Experience</dt><dd>{p.experience_years ? `${p.experience_years} years` : "Not found"}</dd>
                <dt>Education</dt><dd>{(p.education || []).join("; ") || profile.education || "Not found"}</dd>
                <dt>Projects</dt><dd>{(p.projects || []).length ? <ul className="list">{p.projects.map((x, i) => <li key={i}>{x}</li>)}</ul> : "None listed"}</dd>
              </dl>
              <p className="xs dim mt-12">If something is missing, update your resume and upload it again. Contact details are not used in scoring.</p>
            </>
          )}
        </Card>
        <Card title="Contact details">
          <form onSubmit={save} className="stack">
            <div className="form-grid">
              <Field label="Full name"><input className="input" value={contact.name} onChange={(e) => setContact({ ...contact, name: e.target.value })} required minLength={2} /></Field>
              <Field label="Phone"><input className="input" value={contact.phone} onChange={(e) => setContact({ ...contact, phone: e.target.value })} /></Field>
              <Field label="Email" hint="Contact the recruiter to change your email."><input className="input" value={profile.email} disabled /></Field>
            </div>
            <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn btn-secondary" disabled={saving}>{saving && <Spinner />}Save</button></div>
          </form>
        </Card>
      </div>
    </div>
  );
}
