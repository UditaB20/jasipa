const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function describe(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: show the first readable message.
    const first = detail[0];
    const field = first?.loc?.slice(-1)[0];
    return first?.msg ? `${field ? `${field}: ` : ""}${first.msg.replace(/^Value error, /, "")}` : fallback;
  }
  return fallback;
}

export async function request(endpoint, { method = "GET", body, form } = {}) {
  const token = localStorage.getItem("token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers,
      body: form || (body !== undefined ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new ApiError("Cannot reach the server. Check your connection and try again.", 0);
  }
  if (res.status === 401 && token) {
    window.dispatchEvent(new Event("jasipa:session-expired"));
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(describe(data.detail, `Request failed (${res.status}).`), res.status);
  }
  const type = res.headers.get("content-type") || "";
  return type.includes("application/json") ? res.json() : res.blob();
}

const post = (endpoint, body) => request(endpoint, { method: "POST", body });

// Auth
export const login = (email, password) => post("/auth/login", { email, password });
export const register = (data) => post("/auth/register", data);
export const getMe = () => request("/auth/me");

// HR: dashboard, jobs, rubrics, questions
export const getDashboard = () => request("/dashboard/summary");
export const getJobs = () => request("/jobs/");
export const createJob = (data) => post("/jobs/", data);
export const getJobRubric = (id) => request(`/jobs/${id}/rubric`);
export const getRubricVersions = (id) => request(`/jobs/${id}/rubrics`);
export const updateJobRubric = (id, data) => request(`/jobs/${id}/rubric`, { method: "PUT", body: data });
export const getQuestionSet = (jdId) => request(`/assessments/questions/${jdId}`);
export const regenerateQuestionSet = (jdId) => post(`/assessments/questions/${jdId}/regenerate`);

// HR: candidates and evaluation
export const getCandidates = (stage, jdId) => {
  const params = new URLSearchParams();
  if (stage) params.append("stage", stage);
  if (jdId) params.append("jd_id", jdId);
  const q = params.toString();
  return request(`/candidates/${q ? `?${q}` : ""}`);
};
export const getCandidate = (id) => request(`/candidates/${id}`);
export const uploadResume = (formData) => request("/candidates/upload-resume", { method: "POST", form: formData });
export const downloadResume = (id) => request(`/candidates/${id}/resume`);
export const runScreenResume = (candidate_id) => post("/pipeline/run-screen-resume", { candidate_id });
export const runFullGraph = (candidate_id) => post("/pipeline/run-full-graph", { candidate_id });
export const getDecisionStatus = (id) => request(`/reviews/candidate/${id}`);
export const submitDecision = (data) => post("/reviews/decide", data);
export const getCohortAnalytics = () => request("/bias/analytics");

// HR: outcomes, audit, administration
export const recordHiringOutcome = (data) => post("/learning/outcomes", data);
export const getEligibleOutcomes = () => request("/learning/eligible");
export const getHiringLearningAnalytics = () => request("/learning/analytics");
export const getHiringOutcomeHistory = () => request("/learning/history");
export const getAuditLogs = (candidateId = null, limit = 200) =>
  request(`/audit/logs?limit=${limit}${candidateId ? `&candidate_id=${encodeURIComponent(candidateId)}` : ""}`);
export const verifyAuditChain = () => request("/audit/verify");
export const getMcpTools = () => request("/mcp/tools");
export const getPanelConfig = () => request("/admin/panel-coordinator-config");
export const updatePanelConfig = (data) => request("/admin/panel-coordinator-config", { method: "PATCH", body: data });
export const getStrategyEffectiveness = () => request("/admin/strategy-effectiveness");
export const getExpertTasks = (status = "PENDING") => request(`/admin/expert-tasks?status=${status}`);
export const updateExpertTask = (id, data) => request(`/admin/expert-tasks/${id}`, { method: "PATCH", body: data });

// Candidate portal (scoped to the signed-in candidate by the server)
export const getCandidateProfile = () => request("/candidate/me");
export const updateCandidateProfile = (data) => request("/candidate/profile", { method: "PUT", body: data });
export const uploadCandidateResume = (file) => {
  const form = new FormData();
  form.append("file", file);
  return request("/candidate/upload-resume", { method: "POST", form });
};
export const downloadMyResume = () => request("/candidate/resume");
export const getCandidateApplications = () => request("/candidate/applications");
export const getCandidateJobs = () => request("/candidate/jobs");
export const applyCandidateJob = (jd_id) => post("/candidate/apply", { jd_id });
export const getCandidateAssessments = () => request("/candidate/assessments");
export const runSampleTests = (question_id, code) => post("/candidate/assessments/run-code", { question_id, code });
export const submitCandidateTechnical = (answers) => post("/candidate/submit-technical", { answers });
export const submitCandidateBehavioral = (answers) => post("/candidate/submit-behavioral", { answers });
export const getCandidateTimeline = () => request("/candidate/timeline");
