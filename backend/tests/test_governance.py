import pytest
from app.agents.panel_coordinator import PanelCoordinatorAgent
from app.schemas.screening import ResumeScreeningOutput
from app.schemas.assessment import SkillAssessorOutput, CultureFitOutput
from app.mcp.server import MCPServer
from app.database.session import SessionLocal

def test_panel_coordinator_prohibits_auto_reject_or_auto_hire():
    screening = ResumeScreeningOutput(
        candidate_id="C_LOW",
        jd_id="JD001",
        score=20.0,
        matched_requirements=[],
        missing_requirements=["Python", "SQL"],
        experience_match=False,
        evidence=["Very low match"],
        status="COMPLETED"
    )
    technical = SkillAssessorOutput(
        candidate_id="C_LOW",
        jd_id="JD001",
        score=25.0,
        skill_breakdown={"Python": 25.0},
        evidence=["Poor coding test answers"],
        status="COMPLETED"
    )
    behavioral = CultureFitOutput(
        candidate_id="C_LOW",
        jd_id="JD001",
        score=30.0,
        breakdown={"teamwork": 30.0},
        evidence=["Weak answers"],
        status="COMPLETED"
    )
    
    panel_out = PanelCoordinatorAgent.synthesize(
        candidate_id="C_LOW",
        jd_data={"jd_id": "JD001"},
        rubric_data={"resume_weight": 0.4, "skill_weight": 0.4, "culture_weight": 0.2, "version": "1.0"},
        screening=screening,
        technical=technical,
        behavioral=behavioral
    )

    # Core Governance check: MUST NEVER AUTONOMOUSLY REJECT
    assert panel_out.recommendation != "AUTO_REJECT"
    assert panel_out.recommendation != "REJECT"
    assert panel_out.recommendation == "HUMAN_REVIEW_REQUIRED"
    assert panel_out.merged_score < 40.0

def test_mcp_tools_execution():
    db = SessionLocal()
    # Test MCP tool listing
    tools = MCPServer.list_tools()
    assert len(tools) >= 8
    tool_names = [t["name"] for t in tools]
    assert "get_candidate" in tool_names
    assert "get_job_description" in tool_names
    assert "save_human_review" in tool_names

    # Test get_candidate tool execution
    res = MCPServer.execute_tool(db, "get_candidate", {"candidate_id": "CAND-001-ELENA"})
    assert res is not None
    assert res["name"] == "Elena Rostova"
    db.close()
