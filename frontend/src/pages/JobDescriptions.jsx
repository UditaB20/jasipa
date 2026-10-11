import { useEffect, useState } from "react";
import { Briefcase, Plus, RefreshCw, Trash2 } from "lucide-react";
import { createJob, getJobRubric, getJobs, getQuestionSet, getRubricVersions, regenerateQuestionSet, updateJobRubric } from "../services/api";
import { Alert, Badge, Card, Drawer, EmptyState, ErrorState, Field, LoadingBlock, PageHeader, PageLoading, Spinner, Tabs, fmtDate, fmtDateTime, useAsync, useToast } from "../components/ui";

export default function JobDescriptions() {
  const { data: jobs, loading, error, reload } = useAsync(getJobs, []);
  const [chosen, setSelected] = useState(null);
  const [creating, setCreating] = useState(false);
  const selected = jobs?.some((j) => j.jd_id === chosen) ? chosen : jobs?.[0]?.jd_id;

  if (loading && !jobs) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const job = jobs.find((j) => j.jd_id === selected);

  return (
    <div className="page">
      <PageHeader title="Jobs" subtitle="Each job has a versioned scoring rubric and a generated assessment that every applicant receives."
        actions={<button className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={15} />New job</button>} />
      {jobs.length === 0 ? (
        <Card><EmptyState icon={Briefcase} title="No jobs yet" action={<button className="btn btn-primary" onClick={() => setCreating(true)}>Create a job</button>}>
          Creating a job generates its scoring rubric automatically.
        </EmptyState></Card>
      ) : (
        <div className="master-detail">
          <Card pad={false}>
            {jobs.map((j) => (
              <div key={j.jd_id} className={`list-item clickable ${j.jd_id === selected ? "selected" : ""}`} onClick={() => setSelected(j.jd_id)}
                role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && setSelected(j.jd_id)}>
                <div><div className="cell-title">{j.title}</div><div className="cell-sub">{j.department} · rubric v{j.rubric_version}</div></div>
              </div>
            ))}
          </Card>
          {job && <JobDetail key={job.jd_id} job={job} onChanged={reload} />}
        </div>
      )}
      {creating && <CreateJobDrawer onClose={() => setCreating(false)} onCreated={async (j) => { setCreating(false); await reload(); setSelected(j.jd_id); }} />}
    </div>
  );
}

function JobDetail({ job, onChanged }) {
  const [tab, setTab] = useState("overview");
  return (
    <div>
      <Card>
        <h2 style={{ fontSize: 18 }}>{job.title}</h2>
        <p className="small dim mt-4">{job.department} · {job.min_experience}+ years · created {fmtDate(job.created_at)}</p>
      </Card>
      <div className="mt-16">
        <Tabs active={tab} onChange={setTab} tabs={[{ id: "overview", label: "Overview" }, { id: "rubric", label: "Scoring rubric" }, { id: "assessment", label: "Assessment" }]} />
        {tab === "overview" && (
          <Card>
            <p className="small" style={{ whiteSpace: "pre-wrap" }}>{job.description}</p>
            <hr className="divider" />
            <dl className="kv">
              <dt>Required skills</dt><dd><div className="chips">{job.required_skills.map((s) => <span key={s} className="chip">{s}</span>)}</div></dd>
              <dt>Preferred skills</dt><dd><div className="chips">{(job.preferred_skills || []).map((s) => <span key={s} className="chip">{s}</span>)}{!job.preferred_skills?.length && <span className="dim">None</span>}</div></dd>
              <dt>Education</dt><dd>{job.education_requirement || "—"}</dd>
            </dl>
          </Card>
        )}
        {tab === "rubric" && <RubricEditor job={job} onSaved={onChanged} />}
        {tab === "assessment" && <AssessmentPreview job={job} />}
      </div>
    </div>
  );
}

function RubricEditor({ job, onSaved }) {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => Promise.all([getJobRubric(job.jd_id), getRubricVersions(job.jd_id)]), [job.jd_id, job.rubric_version]);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => {
    if (!data) return;
    const [rubric] = data;
    const t = rubric.criteria?.technical_scoring || {};
    setForm({
      resume: Math.round(rubric.resume_weight * 100), skill: Math.round(rubric.skill_weight * 100), culture: Math.round(rubric.culture_weight * 100),
      mcq: t.mcq_weight ?? 30, coding: t.coding_weight ?? 40, short: t.short_answer_weight ?? 30, threshold: t.passing_threshold ?? 70,
      competencies: (rubric.criteria?.behavioral_scoring?.competencies || []).map((c) => ({ ...c })),
    });
  }, [data]);

  if (loading && !data) return <Card><LoadingBlock /></Card>;
  if (error) return <Alert tone="danger">{error.message}</Alert>;
  if (!form) return null;
  const [rubric, versions] = data;
  const topSum = form.resume + form.skill + form.culture;
  const techSum = form.mcq + form.coding + form.short;
  const compSum = form.competencies.reduce((s, c) => s + Number(c.max_points || 0), 0);
  const problems = [
    topSum !== 100 && `Stage weights add up to ${topSum}%, not 100%.`,
    techSum !== 100 && `Technical question weights add up to ${techSum}%, not 100%.`,
    Math.round(compSum) !== 100 && `Competency points add up to ${compSum}, not 100.`,
    form.competencies.some((c) => !c.competency?.trim()) && "Every competency needs a name.",
  ].filter(Boolean);
  const num = (key) => (e) => setForm({ ...form, [key]: Math.max(0, Math.min(100, Number(e.target.value) || 0)) });
  const setComp = (i, key, value) => setForm({ ...form, competencies: form.competencies.map((c, j) => (j === i ? { ...c, [key]: value } : c)) });

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    const criteria = { ...rubric.criteria,
      technical_scoring: { ...rubric.criteria.technical_scoring, mcq_weight: form.mcq, coding_weight: form.coding, short_answer_weight: form.short, passing_threshold: form.threshold },
      behavioral_scoring: { ...rubric.criteria.behavioral_scoring, competencies: form.competencies.map((c) => ({ ...c, competency: c.competency.trim(), max_points: Number(c.max_points) })) } };
    try {
      const saved = await updateJobRubric(job.jd_id, { resume_weight: form.resume / 100, skill_weight: form.skill / 100, culture_weight: form.culture / 100, criteria });
      toast(`Rubric saved as version ${saved.version}. New evaluations use it; past decisions keep their version.`);
      await onSaved();
      await reload();
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="stack">
      <Card title={`Rubric v${rubric.version}`} subtitle="Saving creates a new version. New applicants get an assessment generated for it; current applicants keep the questions they were given.">
        <div className="stack">
          <div>
            <div className="section-title">How stages combine into the panel score</div>
            <div className="grid grid-3">
              <Field label="Resume %"><input className="input num" type="number" value={form.resume} onChange={num("resume")} /></Field>
              <Field label="Technical %"><input className="input num" type="number" value={form.skill} onChange={num("skill")} /></Field>
              <Field label="Behavioral %"><input className="input num" type="number" value={form.culture} onChange={num("culture")} /></Field>
            </div>
          </div>
          <div>
            <div className="section-title">Technical assessment weighting</div>
            <div className="grid grid-4">
              <Field label="Multiple choice %"><input className="input num" type="number" value={form.mcq} onChange={num("mcq")} /></Field>
              <Field label="Coding %"><input className="input num" type="number" value={form.coding} onChange={num("coding")} /></Field>
              <Field label="Written %"><input className="input num" type="number" value={form.short} onChange={num("short")} /></Field>
              <Field label="Target score"><input className="input num" type="number" value={form.threshold} onChange={num("threshold")} /></Field>
            </div>
            <p className="xs dim mt-8">Weights are applied to the question types present in the assessment and rescaled if a type is absent.</p>
          </div>
          <div>
            <div className="row-between"><div className="section-title">Behavioral competencies (points)</div>
              <button className="btn btn-ghost btn-sm" onClick={() => setForm({ ...form, competencies: [...form.competencies, { competency: "", description: "", max_points: 0 }] })}><Plus size={13} />Add</button></div>
            <div className="stack-sm">
              {form.competencies.map((c, i) => (
                <div key={i} className="row wrap" style={{ alignItems: "flex-start" }}>
                  <input className="input" style={{ flex: "1 1 160px" }} value={c.competency} placeholder="Competency" onChange={(e) => setComp(i, "competency", e.target.value)} aria-label="Competency name" />
                  <input className="input" style={{ flex: "3 1 240px" }} value={c.description || ""} placeholder="What good evidence looks like" onChange={(e) => setComp(i, "description", e.target.value)} aria-label="Competency description" />
                  <input className="input num" style={{ width: 80 }} type="number" value={c.max_points} onChange={(e) => setComp(i, "max_points", Number(e.target.value) || 0)} aria-label="Points" />
                  <button className="btn btn-ghost btn-sm" style={{ height: 36 }} onClick={() => setForm({ ...form, competencies: form.competencies.filter((_, j) => j !== i) })} aria-label="Remove competency"><Trash2 size={14} /></button>
                </div>
              ))}
            </div>
          </div>
          {problems.length > 0 && <Alert tone="warning">{problems.join(" ")}</Alert>}
          {saveError && <Alert tone="danger">{saveError}</Alert>}
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn btn-primary" disabled={saving || problems.length > 0} onClick={save}>{saving && <Spinner />}Save as new version</button>
          </div>
        </div>
      </Card>
      <Card title="Version history" pad={false}>
        {versions.slice().reverse().map((v) => (
          <div key={v.rubric_id} className="list-item">
            <span className="small">v{v.version}{v.version === job.rubric_version && <Badge tone="accent">active</Badge>}</span>
            <span className="xs dim num">{Math.round(v.resume_weight * 100)} / {Math.round(v.skill_weight * 100)} / {Math.round(v.culture_weight * 100)} · {fmtDateTime(v.created_at)}</span>
          </div>
        ))}
      </Card>
    </div>
  );
}

function AssessmentPreview({ job }) {
  const toast = useToast();
  const { data: loaded, loading, error, reload } = useAsync(() => getQuestionSet(job.jd_id), [job.jd_id, job.rubric_version]);
  const [fresh, setFresh] = useState(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState(null);
  const data = fresh && loaded && fresh.question_set_id !== loaded.question_set_id && fresh.created_at >= loaded.created_at ? fresh : loaded;

  const regenerate = async () => {
    if (!window.confirm("Generate a new assessment for future applicants? Candidates who already started keep their original questions.")) return;
    setBusy(true);
    setFailure(null);
    try {
      const result = await regenerateQuestionSet(job.jd_id);
      setFresh(result);
      toast(`New assessment generated: ${result.changed_questions} of ${result.total_questions} questions changed.`);
      await reload();
    } catch (err) {
      // 409: no different questions available; 502: generation failed. The current set is kept either way.
      setFailure(err.message);
      toast("The assessment was not regenerated.", "error");
    } finally {
      setBusy(false);
    }
  };
  if (loading && !data) return <Card><LoadingBlock rows={6} /></Card>;
  if (error) return <Alert tone="danger">{error.message}</Alert>;
  return (
    <Card title="Generated assessment" subtitle={`${data.generator === "template" ? "Generated from the job's skills and rubric" : "Generated by the LLM and validated"} · ${fmtDateTime(data.created_at)}`}
      actions={<button className="btn btn-secondary btn-sm" onClick={regenerate} disabled={busy}>{busy ? <Spinner /> : <RefreshCw size={13} />}{busy ? "Generating" : "Regenerate"}</button>}>
      <div className="stack">
        {failure && <Alert tone="danger" title="Regeneration failed — the current assessment is unchanged">{failure}</Alert>}
        {data.generation_notes?.length > 0 && <Alert tone="info">{data.generation_notes.join(" ")}</Alert>}
        <div className="section-title">Technical ({data.technical_questions.length})</div>
        {data.technical_questions.map((q) => (
          <div key={`${data.question_set_id}-${q.question_id}`} className="inset">
            <div className="row wrap"><Badge>{q.type}</Badge><span className="small dim">{q.competency_or_skill} · {q.proficiency}</span></div>
            <p className="small mt-8">{q.prompt}</p>
            {q.options && <ul className="list mt-8" style={{ listStyle: "none", paddingLeft: 0 }}>{q.options.map((o) => <li key={o} className={o.startsWith(q.correct_option) ? "text-success" : undefined}>{o}</li>)}</ul>}
            {q.coding && <p className="xs dim mt-8">{q.coding.tests.length} tests ({q.coding.tests.filter((t) => t.hidden).length} hidden) · reference solution verified in the sandbox</p>}
            {q.rubric_guideline && <p className="xs dim mt-8">Scoring guide: {q.rubric_guideline}</p>}
          </div>
        ))}
        <div className="section-title mt-8">Behavioral ({data.behavioral_questions.length})</div>
        {data.behavioral_questions.map((q) => (
          <div key={`${data.question_set_id}-${q.question_id}`} className="inset"><span className="small dim">{q.competency_or_skill}</span><p className="small mt-4">{q.prompt}</p></div>
        ))}
        <p className="xs dim">Set {data.question_set_id.slice(0, 8)} · rubric v{data.rubric_version}</p>
      </div>
    </Card>
  );
}

function CreateJobDrawer({ onClose, onCreated }) {
  const toast = useToast();
  const [form, setForm] = useState({ title: "", department: "", description: "", required: "", preferred: "", min_experience: 2, education_requirement: "" });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const split = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);

  const submit = async () => {
    const next = {};
    if (form.title.trim().length < 3) next.title = "Enter a job title.";
    if (form.department.trim().length < 2) next.department = "Enter a department.";
    if (form.description.trim().length < 30) next.description = "Describe the responsibilities (at least 30 characters). Questions are generated from them.";
    if (!split(form.required).length) next.required = "List at least one required skill.";
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    setServerError(null);
    try {
      const job = await createJob({ title: form.title.trim(), department: form.department.trim(), description: form.description.trim(),
        required_skills: split(form.required), preferred_skills: split(form.preferred), min_experience: Number(form.min_experience) || 0,
        education_requirement: form.education_requirement.trim() || undefined });
      toast(`${job.title} created with rubric v${job.rubric_version}.`);
      onCreated(job);
    } catch (err) {
      setServerError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Drawer title="New job" onClose={onClose}
      footer={<><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" onClick={submit} disabled={busy}>{busy && <Spinner />}Create job</button></>}>
      <div className="stack">
        {serverError && <Alert tone="danger">{serverError}</Alert>}
        <div className="form-grid">
          <Field label="Title" error={errors.title}><input className="input" value={form.title} onChange={set("title")} /></Field>
          <Field label="Department" error={errors.department}><input className="input" value={form.department} onChange={set("department")} /></Field>
          <Field className="span-2" label="Responsibilities" error={errors.description} hint="One responsibility per line works best; scenario questions are built from these.">
            <textarea className="textarea" rows={6} value={form.description} onChange={set("description")} />
          </Field>
          <Field className="span-2" label="Required skills" error={errors.required} hint="Comma separated"><input className="input" value={form.required} onChange={set("required")} /></Field>
          <Field className="span-2" label="Preferred skills" hint="Comma separated, optional"><input className="input" value={form.preferred} onChange={set("preferred")} /></Field>
          <Field label="Minimum years of experience"><input className="input num" type="number" min={0} max={40} value={form.min_experience} onChange={set("min_experience")} /></Field>
          <Field label="Education (optional)"><input className="input" value={form.education_requirement} onChange={set("education_requirement")} /></Field>
        </div>
      </div>
    </Drawer>
  );
}
