import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.mcp.tools import ATSTools

# MCP Tool Specifications following Model Context Protocol standard
MCP_TOOL_DEFINITIONS = [
    {
        "name": "get_candidate",
        "description": "Fetch complete ATS profile and extracted resume metadata for a candidate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidate_id": {"type": "string", "description": "Unique candidate identifier"}
            },
            "required": ["candidate_id"]
        }
    },
    {
        "name": "get_job_description",
        "description": "Retrieve Job Description criteria, required skills, and rubric version.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "jd_id": {"type": "string", "description": "Job description ID"}
            },
            "required": ["jd_id"]
        }
    },
    {
        "name": "get_candidate_pipeline_status",
        "description": "Retrieve the real-time stage of a candidate in the hiring pipeline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidate_id": {"type": "string"}
            },
            "required": ["candidate_id"]
        }
    },
    {
        "name": "save_screening_result",
        "description": "Save structured resume screening score and evidence into ATS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidate_id": {"type": "string"},
                "jd_id": {"type": "string"},
                "score": {"type": "number"},
                "matched_requirements": {"type": "array", "items": {"type": "string"}},
                "missing_requirements": {"type": "array", "items": {"type": "string"}},
                "experience_match": {"type": "boolean"},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "rubric_version": {"type": "string"}
            },
            "required": ["candidate_id", "jd_id", "score"]
        }
    },
    {
        "name": "save_assessment_result",
        "description": "Save technical or behavioral assessment evaluation into ATS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidate_id": {"type": "string"},
                "jd_id": {"type": "string"},
                "test_type": {"type": "string", "enum": ["TECHNICAL", "BEHAVIORAL"]},
                "score": {"type": "number"},
                "skill_breakdown": {"type": "object"},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string"}
            },
            "required": ["candidate_id", "jd_id", "test_type", "score"]
        }
    },
    {
        "name": "save_panel_decision",
        "description": "Save multi-agent panel synthesis recommendation into ATS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidate_id": {"type": "string"},
                "jd_id": {"type": "string"},
                "resume_score": {"type": "number"},
                "skill_score": {"type": "number"},
                "culture_score": {"type": "number"},
                "merged_score": {"type": "number"},
                "recommendation": {"type": "string"},
                "strengths": {"type": "array"},
                "gaps": {"type": "array"}
            },
            "required": ["candidate_id", "jd_id", "merged_score", "recommendation"]
        }
    },
    {
        "name": "save_bias_check",
        "description": "Save statistical bias/cohort disparity check into ATS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision_id": {"type": "string"},
                "candidate_id": {"type": "string"},
                "flag_status": {"type": "string"},
                "reason": {"type": "string"}
            },
            "required": ["decision_id", "candidate_id", "flag_status"]
        }
    },
    {
        "name": "get_candidate_history",
        "description": "Fetch immutable timeline audit history for a candidate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidate_id": {"type": "string"}
            },
            "required": ["candidate_id"]
        }
    }
]

class MCPServer:
    """
    Executes ATS tools requested by agents via Model Context Protocol.
    """
    
    @staticmethod
    def list_tools() -> List[Dict[str, Any]]:
        return MCP_TOOL_DEFINITIONS

    @staticmethod
    def execute_tool(db: Session, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "get_candidate":
            return ATSTools.get_candidate(db, arguments.get("candidate_id"))
        elif name == "get_job_description":
            return ATSTools.get_job_description(db, arguments.get("jd_id"))
        elif name == "get_candidate_pipeline_status":
            return ATSTools.get_candidate_pipeline_status(db, arguments.get("candidate_id"))
        elif name == "save_screening_result":
            return ATSTools.save_screening_result(
                db,
                candidate_id=arguments["candidate_id"],
                jd_id=arguments["jd_id"],
                score=arguments["score"],
                matched_requirements=arguments.get("matched_requirements", []),
                missing_requirements=arguments.get("missing_requirements", []),
                experience_match=arguments.get("experience_match", True),
                evidence=arguments.get("evidence", []),
                rubric_version=arguments.get("rubric_version", "1.0"),
                status=arguments.get("status", "COMPLETED")
            )
        elif name == "save_assessment_result":
            return ATSTools.save_assessment_result(
                db,
                candidate_id=arguments["candidate_id"],
                jd_id=arguments["jd_id"],
                test_type=arguments["test_type"],
                questions=arguments.get("questions", []),
                answers=arguments.get("answers", []),
                score=arguments["score"],
                skill_breakdown=arguments.get("skill_breakdown", {}),
                evidence=arguments.get("evidence", []),
                confidence=arguments.get("confidence", 1.0),
                status=arguments.get("status", "COMPLETED")
            )
        elif name == "save_panel_decision":
            return ATSTools.save_panel_decision(
                db,
                candidate_id=arguments["candidate_id"],
                jd_id=arguments["jd_id"],
                resume_score=arguments.get("resume_score", 0.0),
                skill_score=arguments.get("skill_score", 0.0),
                culture_score=arguments.get("culture_score", 0.0),
                merged_score=arguments["merged_score"],
                recommendation=arguments["recommendation"],
                strengths=arguments.get("strengths", []),
                gaps=arguments.get("gaps", []),
                disagreements=arguments.get("disagreements", []),
                evidence=arguments.get("evidence", []),
                rubric_version=arguments.get("rubric_version", "1.0")
            )
        elif name == "save_bias_check":
            return ATSTools.save_bias_check(
                db,
                decision_id=arguments["decision_id"],
                candidate_id=arguments["candidate_id"],
                flag_status=arguments["flag_status"],
                reason=arguments.get("reason", ""),
                cohort_breakdown=arguments.get("cohort_breakdown", {}),
                requires_human_review=arguments.get("requires_human_review", True)
            )
        elif name == "get_candidate_history":
            return ATSTools.get_candidate_history(db, arguments.get("candidate_id"))
        else:
            raise ValueError(f"Unknown MCP tool: {name}")
