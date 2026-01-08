#!/usr/bin/env python3
"""
Simplified test cases for ReportGenerator - basic functionality tests
"""

import pytest
import unittest
import tempfile
import pathlib
import json
import os
import shutil
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports  
import sys
src_dir = pathlib.Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from oss_audit.core.report_generator import ReportGenerator, DimensionReport, AuditReport
from oss_audit.core.project_detector import ProjectInfo, ProjectType, StructureType, SizeMetrics


def create_mock_project_info() -> ProjectInfo:
    """Create mock project info for testing"""
    return ProjectInfo(
        name="test-project",
        path="/tmp/test-project",
        languages={"python": 0.7, "javascript": 0.3},
        structure_type=StructureType.SINGLE_PROJECT,
        project_type=ProjectType.WEB_APPLICATION,
        dependencies={"python": ["flask", "requests"], "javascript": ["react", "axios"]},
        build_tools=["setup.py", "package.json"],
        size_metrics=SizeMetrics(
            total_files=150,
            total_lines=8500,
            code_files=120,
            code_lines=6000,
            test_files=25,
            test_lines=2000
        ),
        confidence=0.92
    )


class TestReportGenerator(unittest.TestCase):
    """Simplified ReportGenerator test suite"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
        
        self.project_info = create_mock_project_info()
        self.generator = ReportGenerator()
        
        # Mock tool results
        self.tool_results = {
            "tool1": {
                "success": True,
                "score": 85,
                "issues_found": []
            },
            "tool2": {
                "success": True, 
                "score": 90,
                "issues_found": []
            }
        }
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generator_initialization(self):
        """Test ReportGenerator initializes correctly"""
        self.assertIsNotNone(self.generator)
    
    def test_analyze_dimensions_basic(self):
        """Test basic dimension analysis"""
        dimensions = self.generator.analyze_dimensions(
            tool_results=self.tool_results,
            project_info=self.project_info
        )
        
        self.assertIsInstance(dimensions, list)
        self.assertGreater(len(dimensions), 0)
        
        for dim in dimensions:
            self.assertIsInstance(dim, DimensionReport)
            self.assertIsInstance(dim.score, (int, float))
            self.assertGreaterEqual(dim.score, 0)
            self.assertLessEqual(dim.score, 100)
    
    def test_generate_audit_report(self):
        """Test audit report generation"""
        dimensions = self.generator.analyze_dimensions(
            tool_results=self.tool_results,
            project_info=self.project_info
        )
        
        audit_report = self.generator.generate_audit_report(
            project_info=self.project_info,
            tool_results=self.tool_results,
            dimensions=dimensions,
            output_dir=str(self.temp_path)
        )
        
        self.assertIsInstance(audit_report, AuditReport)
        self.assertIsInstance(audit_report.overall_score, (int, float))
        self.assertGreaterEqual(audit_report.overall_score, 0)
        self.assertLessEqual(audit_report.overall_score, 100)
    
    def test_html_generation_basic(self):
        """Test basic HTML report generation"""
        dimensions = self.generator.analyze_dimensions(
            tool_results=self.tool_results,
            project_info=self.project_info
        )
        
        audit_report = self.generator.generate_audit_report(
            project_info=self.project_info,
            tool_results=self.tool_results,
            dimensions=dimensions,
            output_dir=str(self.temp_path)
        )
        
        # Check if HTML files are generated
        html_files = list(self.temp_path.glob("*.html"))
        self.assertGreater(len(html_files), 0)
    
    def test_json_report_generation(self):
        """Test JSON report generation"""
        dimensions = self.generator.analyze_dimensions(
            tool_results=self.tool_results,
            project_info=self.project_info
        )
        
        audit_report = self.generator.generate_audit_report(
            project_info=self.project_info,
            tool_results=self.tool_results,
            dimensions=dimensions,
            output_dir=str(self.temp_path)
        )
        
        # Check if JSON report is generated
        json_files = list(self.temp_path.glob("*.json"))
        self.assertGreater(len(json_files), 0)
        
        # Verify JSON content
        json_file = json_files[0]
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            
        self.assertIn('project_info', json_data)
        self.assertIn('audit_summary', json_data)


if __name__ == '__main__':
    unittest.main(verbosity=2)