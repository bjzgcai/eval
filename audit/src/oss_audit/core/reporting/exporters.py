"""
Exporters for AuditReport (JSON/HTML). Minimal, non-invasive draft.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from jinja2 import Template

from ..models import AuditReport


def export_json(report: AuditReport, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


DEFAULT_HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>OSS Audit Report</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; }
      h1 { margin-top: 0; }
      table { border-collapse: collapse; width: 100%; }
      th, td { border: 1px solid #ddd; padding: 8px; }
      th { background: #f6f8fa; text-align: left; }
      .sev-high { color: #b22222; }
      .sev-medium { color: #b36b00; }
      .sev-low { color: #777; }
    </style>
  </head>
  <body>
    <h1>OSS Audit Report</h1>
    <p>Project: {{ meta.project_name }} | Generated: {{ meta.generated_at }} | Schema: {{ meta.schema_version }}</p>
    <h2>Summary</h2>
    <ul>
      {% for k, v in summary.items() %}<li>{{ k }}: {{ '%.2f'|format(v) }}</li>{% endfor %}
    </ul>
    <h2>Tool Runs</h2>
    {% for run in tool_runs %}
      <h3>{{ run.tool.name }} ({{ run.status }}) - {{ '%.2f'|format(run.duration_s) }}s</h3>
      {% if run.findings %}
        <table>
          <thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Location</th></tr></thead>
          <tbody>
            {% for f in run.findings %}
              <tr>
                <td>{{ f.id }}</td>
                <td>{{ f.title }}</td>
                <td class="sev-{{ f.severity }}">{{ f.severity }}</td>
                <td>{{ f.file }}{% if f.line %}:{{ f.line }}{% endif %}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      {% else %}
        <p>No findings.</p>
      {% endif %}
    {% endfor %}
    {% if recommendations %}
      <h2>Recommendations</h2>
      <ul>{% for r in recommendations %}<li>{{ r }}</li>{% endfor %}</ul>
    {% endif %}
  </body>
  </html>
"""


def export_html(report: AuditReport, output_path: str, template_str: Optional[str] = None) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tpl = Template(template_str or DEFAULT_HTML_TEMPLATE)
    html = tpl.render(**report.to_dict())
    path.write_text(html, encoding="utf-8")
    return str(path)

