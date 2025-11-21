#!/usr/bin/env python3
"""
RCA Engine - AI-Powered Root Cause Analysis
============================================
Analyzes failure patterns using ML and LLM to identify root causes.

Features:
- Analyze failure patterns using ML
- Identify root causes from logs, metrics, traces
- Generate RCA reports
- Learn from past incidents
"""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

RCA_KNOWLEDGE_BASE_FILE = STATE / "rca_knowledge_base.json"
RCA_REPORTS_FILE = STATE / "rca_reports.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class RCAEngine:
    """Root Cause Analysis Engine."""

    def __init__(self):
        self.knowledge_base = self.load_knowledge_base()
        self.reports = []

    def load_knowledge_base(self) -> dict[str, Any]:
        """Load RCA knowledge base."""
        if RCA_KNOWLEDGE_BASE_FILE.exists():
            try:
                return json.loads(RCA_KNOWLEDGE_BASE_FILE.read_text())
            except Exception:
                return {"incidents": [], "patterns": {}}
        return {"incidents": [], "patterns": {}}

    def save_knowledge_base(self) -> None:
        """Save RCA knowledge base."""
        try:
            RCA_KNOWLEDGE_BASE_FILE.write_text(json.dumps(self.knowledge_base, indent=2))
        except Exception:
            pass

    def analyze_failure(
        self,
        agent_name: str,
        error_log: str,
        metrics: Optional[dict[str, Any]] = None,
        traces: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Analyze failure and identify root cause."""
        # First, check knowledge base for similar incidents
        similar_incidents = self._find_similar_incidents(agent_name, error_log)

        if similar_incidents:
            # Use known solution
            incident = similar_incidents[0]
            return {
                "root_cause": incident.get("root_cause", "unknown"),
                "confidence": 0.8,
                "solution": incident.get("solution", ""),
                "source": "knowledge_base",
                "similar_incidents": len(similar_incidents),
            }

        # Use LLM for analysis if available
        if ANTHROPIC_API_KEY or OPENAI_API_KEY:
            return self._llm_analyze(agent_name, error_log, metrics, traces)
        else:
            # Fallback: pattern-based analysis
            return self._pattern_analyze(agent_name, error_log)

    def _find_similar_incidents(self, agent_name: str, error_log: str) -> list[dict[str, Any]]:
        """Find similar incidents in knowledge base."""
        incidents = self.knowledge_base.get("incidents", [])
        similar = []

        # Extract error keywords
        error_keywords = set(re.findall(r"\w+Error|\w+Exception", error_log))

        for incident in incidents:
            if incident.get("agent") == agent_name:
                incident_keywords = set(incident.get("error_keywords", []))
                # Simple similarity: check if error types match
                if error_keywords & incident_keywords:
                    similar.append(incident)

        return similar[:5]  # Return top 5 similar

    def _pattern_analyze(self, agent_name: str, error_log: str) -> dict[str, Any]:
        """Pattern-based root cause analysis."""
        root_cause = "unknown"
        confidence = 0.5

        # Pattern matching
        if re.search(r"ImportError|ModuleNotFoundError", error_log):
            root_cause = "missing_dependency"
            confidence = 0.9
        elif re.search(r"ConnectionError|Connection refused", error_log):
            root_cause = "network_issue"
            confidence = 0.8
        elif re.search(r"MemoryError|Out of memory", error_log):
            root_cause = "resource_exhaustion"
            confidence = 0.9
        elif re.search(r"FileNotFoundError", error_log):
            root_cause = "missing_file"
            confidence = 0.8
        elif re.search(r"TimeoutError|timeout", error_log, re.IGNORECASE):
            root_cause = "timeout"
            confidence = 0.7
        elif re.search(r"localhost|127\.0\.0\.1", error_log):
            root_cause = "localhost_dependency"
            confidence = 0.9

        return {
            "root_cause": root_cause,
            "confidence": confidence,
            "solution": self._get_solution(root_cause),
            "source": "pattern_analysis",
        }

    def _llm_analyze(
        self,
        agent_name: str,
        error_log: str,
        metrics: Optional[dict[str, Any]] = None,
        traces: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Use LLM for root cause analysis."""
        try:
            if ANTHROPIC_API_KEY:
                import anthropic

                client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

                prompt = f"""Analyze this failure and identify the root cause:

Agent: {agent_name}
Error Log:
{error_log[:2000]}

Metrics: {json.dumps(metrics or {}, indent=2)[:1000]}

Provide:
1. Root cause (one sentence)
2. Confidence (0-1)
3. Recommended solution (one sentence)
4. Error keywords (list)

Format as JSON:
{{
    "root_cause": "...",
    "confidence": 0.0,
    "solution": "...",
    "error_keywords": ["..."]
}}"""

                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                )

                result_text = response.content[0].text
                # Extract JSON from response
                json_match = re.search(r"\{[^}]+\}", result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    result["source"] = "llm_anthropic"
                    return result

            elif OPENAI_API_KEY:
                import openai

                client = openai.OpenAI(api_key=OPENAI_API_KEY)

                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a root cause analysis expert. Analyze failures and provide JSON responses.",
                        },
                        {
                            "role": "user",
                            "content": f"Analyze failure for agent {agent_name}:\n\n{error_log[:2000]}",
                        },
                    ],
                    response_format={"type": "json_object"},
                )

                result = json.loads(response.choices[0].message.content)
                result["source"] = "llm_openai"
                return result

        except Exception as e:
            print(f"[rca_engine] LLM analysis failed: {e}", flush=True)

        # Fallback to pattern analysis
        return self._pattern_analyze(agent_name, error_log)

    def _get_solution(self, root_cause: str) -> str:
        """Get solution for root cause."""
        solutions = {
            "missing_dependency": "Install missing module via pip",
            "network_issue": "Check network connectivity, retry with backoff",
            "resource_exhaustion": "Restart agent, reduce workload, or scale resources",
            "missing_file": "Create missing file or directory",
            "timeout": "Increase timeout or optimize slow operations",
            "localhost_dependency": "Remove localhost dependency, use RENDER_MODE detection",
        }
        return solutions.get(root_cause, "Investigate and fix manually")

    def record_incident(
        self,
        agent_name: str,
        root_cause: str,
        solution: str,
        success: bool,
        error_log: str,
    ) -> None:
        """Record incident in knowledge base."""
        error_keywords = list(set(re.findall(r"\w+Error|\w+Exception", error_log)))

        incident = {
            "agent": agent_name,
            "root_cause": root_cause,
            "solution": solution,
            "success": success,
            "error_keywords": error_keywords,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self.knowledge_base.setdefault("incidents", []).append(incident)

        # Keep only last 1000 incidents
        if len(self.knowledge_base["incidents"]) > 1000:
            self.knowledge_base["incidents"] = self.knowledge_base["incidents"][-1000:]

        # Update patterns
        if root_cause not in self.knowledge_base.get("patterns", {}):
            self.knowledge_base.setdefault("patterns", {})[root_cause] = {
                "count": 0,
                "successful_solutions": [],
            }

        pattern = self.knowledge_base["patterns"][root_cause]
        pattern["count"] += 1
        if success and solution not in pattern["successful_solutions"]:
            pattern["successful_solutions"].append(solution)

        self.save_knowledge_base()

    def generate_report(self, agent_name: str, analysis: dict[str, Any]) -> dict[str, Any]:
        """Generate RCA report."""
        report = {
            "agent": agent_name,
            "timestamp": datetime.now(UTC).isoformat(),
            "analysis": analysis,
            "recommendations": self._generate_recommendations(analysis),
        }

        self.reports.append(report)

        # Keep only last 500 reports
        if len(self.reports) > 500:
            self.reports = self.reports[-500:]

        # Save reports
        try:
            RCA_REPORTS_FILE.write_text(json.dumps(self.reports, indent=2))
        except Exception:
            pass

        return report

    def _generate_recommendations(self, analysis: dict[str, Any]) -> list[str]:
        """Generate recommendations from analysis."""
        recommendations = []

        root_cause = analysis.get("root_cause", "")
        solution = analysis.get("solution", "")

        if solution:
            recommendations.append(f"Immediate fix: {solution}")

        if root_cause == "missing_dependency":
            recommendations.append("Add dependency to requirements.txt")
            recommendations.append("Consider dependency validation on startup")

        elif root_cause == "resource_exhaustion":
            recommendations.append("Monitor resource usage proactively")
            recommendations.append("Implement resource limits")

        elif root_cause == "network_issue":
            recommendations.append("Implement retry logic with exponential backoff")
            recommendations.append("Add circuit breaker pattern")

        return recommendations


def analyze_agent_failure(agent_name: str, error_log: str) -> dict[str, Any]:
    """Analyze agent failure and return RCA."""
    engine = RCAEngine()
    analysis = engine.analyze_failure(agent_name, error_log)
    report = engine.generate_report(agent_name, analysis)
    return report


def main() -> None:
    """Main RCA engine (typically called by self-healing agent)."""
    print(
        f"[rca_engine] 🔍 RCA Engine ready @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )


if __name__ == "__main__":
    main()

