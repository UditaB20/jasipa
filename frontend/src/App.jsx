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
import SettingsPage from "./pages/SettingsPage";
import CandidatePortal from "./pages/CandidatePortal";
import LoginPage from "./pages/LoginPage";
import LearningPage from "./pages/LearningPage";
import { getPendingReviews } from "./services/api";

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem("user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [activePage, setActivePage] = useState("dashboard");
  const [selectedCandidateId, setSelectedCandidateId] = useState("CAND-001-ELENA");
  const [pendingCount, setPendingCount] = useState(0);

  // Poll for pending reviews only if HR
  useEffect(() => {
    if (!currentUser || currentUser.role !== "HR") return;

    async function checkPending() {
      try {
        const list = await getPendingReviews();
        setPendingCount(list?.length || 0);
      } catch (err) {
        // Ignored or logged
      }
    }

    checkPending();
    const interval = setInterval(checkPending, 8000);
    return () => clearInterval(interval);
  }, [currentUser]);

  const handleLoginSuccess = (user) => {
    setCurrentUser(user);
    if (user.role === "HR") {
      setActivePage("dashboard");
    } else {
      setActivePage("candidate-portal");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setCurrentUser(null);
    setActivePage("login");
  };

  // If not authenticated, render Login Page
  if (!currentUser) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  // Candidate View (Strict Candidate Portal & Isolation)
  if (currentUser.role === "CANDIDATE") {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0b1120" }}>
        <Navbar currentUser={currentUser} onLogout={handleLogout} />
        <CandidatePortal currentUser={currentUser} onLogout={handleLogout} />
      </div>
    );
  }

  // HR Admin View
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0b1120" }}>
      {/* Top Navbar */}
      <Navbar currentUser={currentUser} onLogout={handleLogout} />

      {/* Main HR Layout: Sidebar + Page Content */}
      <div style={{ display: "flex", flex: 1 }}>
        <Sidebar
          activePage={activePage}
          setActivePage={setActivePage}
          pendingReviewCount={pendingCount}
        />

        <main style={{ flex: 1, overflowY: "auto", background: "#0b1120" }}>
          {activePage === "dashboard" && (
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
              currentRole="HR"
              selectedCandidateId={selectedCandidateId}
              setSelectedCandidateId={setSelectedCandidateId}
            />
          )}

          {activePage === "bias" && <BiasAnalytics />}
          {activePage === "learning" && <LearningPage currentUser={currentUser} />}

          {activePage === "audit" && (
            <CandidateDetail
              candidateId={selectedCandidateId}
              setActivePage={setActivePage}
              setSelectedCandidateId={setSelectedCandidateId}
            />
          )}

          {activePage === "settings" && (
            <SettingsPage currentUser={currentUser} onUserUpdate={setCurrentUser} />
          )}
        </main>
      </div>
    </div>
  );
}
