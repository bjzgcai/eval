"""
Lightweight domain models for OSS Audit (draft).
Dataclasses are used to avoid new runtime deps; can be upgraded to pydantic later.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Literal, Any
from datetime import datetime, timezone


Severity = Literal["info", "low", "medium", "high", "critical"]
RunStatus = Literal["success", "failed"]


@dataclass
class ToolSpec:
    name: str
    version: Optional[str] = None
    runner: Optional[str] = None  # e.g., "local", "docker", "podman"
    args: List[str] = field(default_factory=list)


@dataclass
class Finding:
    id: str
    title: str
    severity: Severity = "info"
    description: str = ""
    file: Optional[str] = None
    line: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolRun:
    tool: ToolSpec
    status: RunStatus
    duration_s: float
    findings: List[Finding] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    stdout_path: Optional[str] = None
    stderr_path: Optional[str] = None


@dataclass
class AuditPlan:
    project_path: str
    tools: List[ToolSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportMeta:
    project_name: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = "1.0.0"
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    meta: ReportMeta
    summary: Dict[str, float] = field(default_factory=dict)  # e.g., {"quality": 78.5}
    tool_runs: List[ToolRun] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

