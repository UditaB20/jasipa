import { useMemo, useRef, useState } from "react";
import { FileUp, Search, UserPlus, Users } from "lucide-react";
import { getCandidates, getJobs, uploadResume } from "../services/api";
import { Alert, Card, Drawer, EmptyState, ErrorState, Field, PageHeader, PageLoading, Spinner, StageBadge, fmtDate, useAsync, useToast } from "../components/ui";

const FILTERS = [
  { id: "", label: "All stages" },
  { id: "awaiting", label: "Awaiting decision", stages: ["PANEL_EVALUATED", "BIAS_CHECKED", "HUMAN_REVIEW_PENDING"] },
  { id: "in_progress", label: "In progress", stages: ["APPLIED", "RESUME_SCREENED", "TECHNICAL_ASSESSED", "BEHAVIORAL_ASSESSED", "INFO_REQUESTED", "MANUAL_REVIEW_REQUIRED"] },
  { id: "decided", label: "Decided", stages: ["DECIDED"] },
];
const SOURCES = [["", "All sources"], ["dataset_import", "Kaggle dataset"], ["candidate_portal", "Candidate portal"], ["hr_upload", "HR upload"]];
const ACCEPTED = [".pdf", ".docx"];
const MAX_MB = 5;

export default function CandidatesList({ initialFilter = "" }) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState(FILTERS.some((f) => f.id === initialFilter) ? initialFilter : "");
  const [jobFilter, setJobFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [adding, setAdding] = useState(false);
  const { data, loading, error, reload } = useAsync(() => Promise.all([getCandidates(), getJobs()]), []);

  const [candidates, jobs] = data || [[], []];
  const jobTitle = useMemo(() => Object.fromEntries(jobs.map((j) => [j.jd_id, j.title])), [jobs]);
  const visible = useMemo(() => {
    const stages = FILTERS.find((f) => f.id === filter)?.stages;
    const q = search.trim().toLowerCase();
    return candidates.filter((c) =>
      (!stages || stages.includes(c.current_stage)) &&
      (!jobFilter || c.target_jd_id === jobFilter) &&
      (!sourceFilter || (c.source || "hr_entry") === sourceFilter) &&
      (!q || c.name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q) || (c.skills_extracted || []).some((s) => s.toLowerCase().includes(q))));
  }, [candidates, filter, jobFilter, sourceFilter, search]);

  if (loading && !data) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <div className="page">
      <PageHeader title="Candidates" subtitle="Kaggle dataset records, applicants from the candidate portal, and resumes uploaded by your team."
        actions={<button className="btn btn-primary" onClick={() => setAdding(true)}><UserPlus size={15} />Add candidate</button>} />

      <div className="row wrap mb-16">
        <div className="input-icon" style={{ flex: "1 1 260px" }}>
          <Search size={15} />
          <input className="input" placeholder="Search name, email or skill" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search candidates" />
        </div>
        <select className="select" style={{ width: 190 }} value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter by stage">
          {FILTERS.map((f) => <option key={f.id} value={f.id}>{f.label}</option>)}
        </select>
        <select className="select" style={{ width: 170 }} value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} aria-label="Filter by source">
          {SOURCES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
        <select className="select" style={{ width: 230 }} value={jobFilter} onChange={(e) => setJobFilter(e.target.value)} aria-label="Filter by job">
          <option value="">All jobs</option>
          {jobs.map((j) => <option key={j.jd_id} value={j.jd_id}>{j.title}</option>)}
        </select>
      </div>

      <Card pad={false}>
        {visible.length === 0 ? (
          <EmptyState icon={Users} title={candidates.length ? "No candidates match these filters" : "No candidates yet"}
            action={!candidates.length && <button className="btn btn-primary" onClick={() => setAdding(true)}>Add candidate</button>}>
            {candidates.length ? "Try a different stage, job or search term." : "Upload a resume to add the first candidate."}
          </EmptyState>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Candidate</th><th className="hide-sm">Job</th><th className="hide-sm">Experience</th><th>Stage</th><th className="hide-sm">Added</th></tr></thead>
              <tbody>
                {visible.map((c) => (
                  <tr key={c.candidate_id} className="clickable" onClick={() => { window.location.hash = `/candidates/${c.candidate_id}`; }}>
                    <td>
                      <a className="cell-title" style={{ color: "var(--text)" }} href={`#/candidates/${c.candidate_id}`}>{c.name}</a>
                      <div className="cell-sub">{c.source === "dataset_import" ? `Kaggle dataset · ${c.dataset_category}` : c.email}</div>
                    </td>
                    <td className="hide-sm muted">{jobTitle[c.target_jd_id] || "No application"}</td>
                    <td className="hide-sm num muted">{c.experience_years ? `${c.experience_years} yrs` : "—"}</td>
                    <td><StageBadge stage={c.current_stage} /></td>
                    <td className="hide-sm muted">{fmtDate(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <p className="xs dim mt-12">{visible.length} of {candidates.length} candidates</p>

      {adding && <AddCandidateDrawer jobs={jobs} onClose={() => setAdding(false)} onCreated={(c) => { setAdding(false); window.location.hash = `/candidates/${c.candidate_id}`; }} />}
    </div>
  );
}

export function validateResumeFile(file) {
  if (!file) return "Choose a resume file.";
  if (!ACCEPTED.some((ext) => file.name.toLowerCase().endsWith(ext))) return "Upload a PDF or Word (.docx) file.";
  if (file.size > MAX_MB * 1024 * 1024) return `The file is larger than ${MAX_MB} MB.`;
  if (file.size === 0) return "The file is empty.";
  return null;
}

export function ResumeDropzone({ file, onFile, disabled }) {
  const input = useRef(null);
  const [drag, setDrag] = useState(false);
  return (
    <div className={`dropzone ${drag ? "drag" : ""}`} role="button" tabIndex={0} aria-disabled={disabled}
      onClick={() => !disabled && input.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); if (!disabled && e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]); }}>
      <FileUp size={22} color="var(--text-3)" />
      <div className="title">{file ? file.name : "Drop a resume here or click to browse"}</div>
      <div className="xs dim mt-4">{file ? `${(file.size / 1024).toFixed(0)} KB` : `PDF or DOCX, up to ${MAX_MB} MB`}</div>
      <input ref={input} type="file" accept=".pdf,.docx" hidden onChange={(e) => e.target.files[0] && onFile(e.target.files[0])} />
    </div>
  );
}

function AddCandidateDrawer({ jobs, onClose, onCreated }) {
  const toast = useToast();
  const [form, setForm] = useState({ name: "", email: "", phone: "", target_jd_id: jobs[0]?.jd_id || "", cohort_tag: "" });
  const [file, setFile] = useState(null);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e?.preventDefault();
    const next = {};
    if (form.name.trim().length < 2) next.name = "Enter the candidate's full name.";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) next.email = "Enter a valid email address.";
    const fileError = validateResumeFile(file);
    if (fileError) next.file = fileError;
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    setServerError(null);
    const data = new FormData();
    Object.entries(form).forEach(([k, v]) => v && data.append(k, v.trim()));
    data.append("file", file);
    try {
      const candidate = await uploadResume(data);
      toast(`${candidate.name} added. Resume parsed${candidate.target_jd_id ? " and screened" : ""}.`);
      onCreated(candidate);
    } catch (err) {
      setServerError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Drawer title="Add candidate" onClose={onClose}
      footer={<>
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" onClick={submit} disabled={busy}>{busy && <Spinner />}{busy ? "Uploading" : "Add and screen"}</button>
      </>}>
      <form onSubmit={submit} className="stack">
        {serverError && <Alert tone="danger" title="Upload failed">{serverError}</Alert>}
        <div>
          <ResumeDropzone file={file} onFile={(f) => { setFile(f); setErrors({ ...errors, file: validateResumeFile(f) }); }} disabled={busy} />
          {errors.file && <div className="field-error mt-4">{errors.file}</div>}
        </div>
        <p className="xs dim">Skills, education, experience and projects are extracted from the file. If this email already exists, the candidate's resume is replaced.</p>
        <div className="form-grid">
          <Field label="Full name" error={errors.name}><input className={`input ${errors.name ? "invalid" : ""}`} value={form.name} onChange={set("name")} /></Field>
          <Field label="Email" error={errors.email}><input className={`input ${errors.email ? "invalid" : ""}`} type="email" value={form.email} onChange={set("email")} /></Field>
          <Field label="Phone (optional)"><input className="input" value={form.phone} onChange={set("phone")} /></Field>
          <Field label="Job">
            <select className="select" value={form.target_jd_id} onChange={set("target_jd_id")}>
              <option value="">No application yet</option>
              {jobs.map((j) => <option key={j.jd_id} value={j.jd_id}>{j.title}</option>)}
            </select>
          </Field>
          <Field className="span-2" label="Monitoring cohort (optional)" hint="Used only for aggregate bias monitoring. Never shown to evaluation agents.">
            <input className="input" value={form.cohort_tag} onChange={set("cohort_tag")} placeholder="e.g. Cohort_Alpha" />
          </Field>
        </div>
      </form>
    </Drawer>
  );
}
