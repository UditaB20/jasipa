const API_BASE = "http://localhost:8000/api";

export async function fetchApi(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = localStorage.getItem("token");

  const headers = {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    ...options.headers,
  };

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      if (res.status === 401) {
        // Token expired or invalid
        console.warn("Session expired or unauthorized on", endpoint);
      }
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "API Request Failed");
    }
    return await res.json();
  } catch (err) {
    console.error(`API error on ${endpoint}:`, err);
    throw err;
  }
}

// Auth APIs
export const getMe = () => fetchApi("/auth/me");
export const login = (email, password) => 
  fetchApi("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });

// Job APIs (HR)
export const getJobs = () => fetchApi("/jobs/");
export const getJob = (id) => fetchApi(`/jobs/${id}`);
export const getJobRubric = (id) => fetchApi(`/jobs/${id}/rubric`);
export const createJob = (data) => 
  fetchApi("/jobs/", { method: "POST", body: JSON.stringify(data) });

// Candidate APIs (HR View)
export const getCandidates = (stage, jd_id) => {
  const params = new URLSearchParams();
  if (stage) params.append("stage", stage);
  if (jd_id) params.append("jd_id", jd_id);
  const q = params.toString() ? `?${params.toString()}` : "";
  return fetchApi(`/candidates/${q}`);
};

export const getCandidate = (id) => fetchApi(`/candidates/${id}`);
export const createCandidate = (data) => 
  fetchApi("/candidates/", { method: "POST", body: JSON.stringify(data) });

export const uploadResume = async (formData) => {
  const token = localStorage.getItem("token");
  const headers = token ? { "Authorization": `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE}/candidates/upload-resume`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return await res.json();
};

// Assessment APIs (HR / Evaluation)
export const getTechnicalQuestions = (jd_id) => fetchApi(`/assessments/questions/technical/${jd_id}`);
export const getBehavioralQuestions = (jd_id) => fetchApi(`/assessments/questions/behavioral/${jd_id}`);
export const submitTechnicalAssessment = (data) => 
  fetchApi("/assessments/submit/technical", { method: "POST", body: JSON.stringify(data) });
export const submitBehavioralAssessment = (data) => 
  fetchApi("/assessments/submit/behavioral", { method: "POST", body: JSON.stringify(data) });

// Pipeline APIs (HR)
export const runScreenResume = (candidate_id, jd_id) => 
  fetchApi("/pipeline/run-screen-resume", { method: "POST", body: JSON.stringify({ candidate_id, jd_id }) });
export const runPanelSynthesis = (candidate_id, jd_id) => 
  fetchApi("/pipeline/run-panel", { method: "POST", body: JSON.stringify({ candidate_id, jd_id }) });
export const runFullGraph = (candidate_id, jd_id) => 
  fetchApi("/pipeline/run-full-graph", { method: "POST", body: JSON.stringify({ candidate_id, jd_id }) });

// Review & Bias APIs (HR)
export const getPendingReviews = () => fetchApi("/reviews/pending");
export const submitHumanDecision = (data) => 
  fetchApi("/reviews/decide", { method: "POST", body: JSON.stringify(data) });
export const getCohortAnalytics = () => fetchApi("/bias/analytics");

// Audit & MCP APIs (HR / System)
export const getCandidateAuditTrail = (id) => fetchApi(`/audit/candidate/${id}`);
export const getRecentAuditLogs = (limit = 30) => fetchApi(`/audit/logs?limit=${limit}`);
export const getMcpTools = () => fetchApi("/mcp/tools");
export const executeMcpTool = (name, argumentsObj) => 
  fetchApi("/mcp/execute", { method: "POST", body: JSON.stringify({ name, arguments: argumentsObj }) });

// Candidate Portal APIs (Strict Candidate Data Isolation)
export const getCandidateProfile = () => fetchApi("/candidate/me");
export const getCandidateApplications = () => fetchApi("/candidate/applications");
export const getCandidateJobs = () => fetchApi("/candidate/jobs");
export const applyCandidateJob = (data) => 
  fetchApi("/candidate/apply", { method: "POST", body: JSON.stringify(data) });
export const getCandidateAssessments = () => fetchApi("/candidate/assessments");
export const submitCandidateTechnical = (data) => 
  fetchApi("/candidate/submit-technical", { method: "POST", body: JSON.stringify(data) });
export const submitCandidateBehavioral = (data) => 
  fetchApi("/candidate/submit-behavioral", { method: "POST", body: JSON.stringify(data) });
export const getCandidateTimeline = () => fetchApi("/candidate/timeline");
export const updateCandidateProfile = (data) => 
  fetchApi("/candidate/profile", { method: "PUT", body: JSON.stringify(data) });
export const updateHRProfile = (data) => 
  fetchApi("/auth/profile", { method: "PUT", body: JSON.stringify(data) });

