"""
Placeholders for higher-level rendering orchestration (draft).
Split responsibilities from exporters if/when needed.
"""

from __future__ import annotations

from typing import Optional
from .exporters import export_html, export_json
from ..models import AuditReport


def render_html_report(report: AuditReport, output_path: str, template_str: Optional[str] = None) -> str:
    return export_html(report, output_path, template_str)


def render_json_report(report: AuditReport, output_path: str) -> str:
    return export_json(report, output_path)

