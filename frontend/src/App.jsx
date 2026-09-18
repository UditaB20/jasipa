import React, { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import JobDescriptions from "./pages/JobDescriptions";
import CandidatesList from "./pages/CandidatesList";
import CandidateDetail from "./pages/CandidateDetail";
import AssessmentRoom from "./pages/AssessmentRoom";
import HumanReviewPage from "./pages/HumanReviewPage";
import BiasAnalytics from "./pages/BiasAnalytics";
import McpToolsView from "./pages/McpToolsView";
import DemoRunner from "./pages/DemoRunner";
import StudentPortal from "./pages/StudentPortal";
import { getPendingReviews } from "./services/api";

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [selectedCandidateId, setSelectedCandidateId] = useState("CAND-001-ELENA");
  const [currentRole, setCurrentRole] = useState("HR_ADMIN"); // "HR_ADMIN", "REVIEWER", "STUDENT"
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    async function checkPending() {
      try {
        const list = await getPendingReviews();
        setPendingCount(list.length);
      } catch (err) {
        console.error("Error checking pending reviews:", err);
      }
    }
    checkPending();
    const interval = setInterval(checkPending, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Top Navigation with 3-Way Role Switcher */}
      <Navbar
        currentRole={currentRole}
        setCurrentRole={setCurrentRole}
        activePage={activePage}
        setActivePage={setActivePage}
      />

      {/* Main Layout: Dynamic Sidebar + Page Container */}
      <div style={{ display: "flex", flex: 1 }}>
        <Sidebar
          activePage={activePage}
          setActivePage={setActivePage}
          currentRole={currentRole}
          pendingReviewCount={pendingCount}
        />

        <main style={{ flex: 1, overflowY: "auto", background: "rgba(9, 13, 22, 0.5)" }}>
          {/* Student / Candidate Portal */}
          {(activePage === "student-portal" || (currentRole === "STUDENT" && activePage !== "assessments")) && (
            <StudentPortal
              selectedCandidateId={selectedCandidateId}
              setSelectedCandidateId={setSelectedCandidateId}
            />
          )}

          {activePage === "dashboard" && currentRole !== "STUDENT" && (
            <Dashboard
              setActivePage={setActivePage}
              setSelectedCandidateId={setSelectedCandidateId}
            />
          )}

          {activePage === "jobs" && <JobDescriptions />}

          {activePage === "candidates" && (
            <CandidatesList
              setActivePage={setActivePage}
              setSelectedCandidateId={setSelectedCandidateId}
            />
          )}

          {activePage === "candidate-detail" && (
            <CandidateDetail
              candidateId={selectedCandidateId}
              setActivePage={setActivePage}
              setSelectedCandidateId={setSelectedCandidateId}
            />
          )}

          {activePage === "assessments" && (
            <AssessmentRoom
              selectedCandidateId={selectedCandidateId}
              setSelectedCandidateId={setSelectedCandidateId}
              setActivePage={setActivePage}
            />
          )}

          {activePage === "reviews" && (
            <HumanReviewPage
              currentRole={currentRole}
              selectedCandidateId={selectedCandidateId}
              setSelectedCandidateId={setSelectedCandidateId}
            />
          )}

          {activePage === "bias" && <BiasAnalytics />}

          {activePage === "audit" && (
            <CandidateDetail
              candidateId={selectedCandidateId}
              setActivePage={setActivePage}
              setSelectedCandidateId={setSelectedCandidateId}
            />
          )}

          {activePage === "mcp" && <McpToolsView />}

          {activePage === "demo-runner" && (
            <DemoRunner
              setActivePage={setActivePage}
              setSelectedCandidateId={setSelectedCandidateId}
            />
          )}
        </main>
      </div>
    </div>
  );
}
