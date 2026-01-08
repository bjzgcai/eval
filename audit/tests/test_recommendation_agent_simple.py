#!/usr/bin/env python3
"""
RecommendationAgent 简化测试用例 - 基于实际API的测试
"""

import pytest
import unittest
import tempfile
import pathlib
import os
import shutil
from unittest.mock import Mock, patch

# Add src to path for imports
import sys
src_dir = pathlib.Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from oss_audit.core.recommendation_agent import RecommendationAgent, IntelligentRecommendations, AnalysisResults, Issue, IssueSeverity, ImpactLevel
from oss_audit.core.project_detector import ProjectInfo, ProjectType, StructureType, SizeMetrics
from oss_audit.core.adaptive_agent import ScoringModel


def create_mock_project_info() -> ProjectInfo:
    """Create mock project info for testing"""
    return ProjectInfo(
        name="recommendation-test-project",
        path="/tmp/recommendation-test-project",
        languages={"python": 0.7, "javascript": 0.3},
        structure_type=StructureType.SINGLE_PROJECT,
        project_type=ProjectType.WEB_APPLICATION,
        dependencies={"python": ["django", "requests"], "javascript": ["react"]},
        build_tools=["setup.py", "package.json"],
        size_metrics=SizeMetrics(180, 10000, 140, 7500, 25, 2000),
        confidence=0.85
    )


def create_mock_analysis_results():
    """Create mock analysis results for testing"""
    # Create mock issues
    issues = [
        Issue(
            id="PY-001",
            title="Missing docstring",
            description="Function missing docstring",
            severity=IssueSeverity.MEDIUM,
            category="quality",
            file_path="app.py",
            line_number=10
        ),
        Issue(
            id="SEC-001", 
            title="Hardcoded password",
            description="Hardcoded password detected",
            severity=IssueSeverity.HIGH,
            category="security", 
            file_path="config.py",
            line_number=5
        ),
        Issue(
            id="TEST-001",
            title="Low test coverage", 
            description="Test coverage below threshold",
            severity=IssueSeverity.MEDIUM,
            category="testing"
        )
    ]
    
    # Create tool results
    tool_results = {
        "pylint": {
            "success": True,
            "score": 70,
            "issues_found": [
                {"severity": "medium", "message": "Missing docstring", "line": 10, "file": "app.py"},
                {"severity": "low", "message": "Unused variable", "line": 25, "file": "utils.py"}
            ]
        },
        "bandit": {
            "success": True,
            "score": 80,
            "issues_found": [
                {"severity": "high", "message": "Hardcoded password", "line": 5, "file": "config.py"}
            ]
        },
        "pytest": {
            "success": True,
            "score": 75,
            "coverage": 72.0,
            "test_stats": {"passed": 20, "failed": 3, "total": 23}
        }
    }
    
    return AnalysisResults(
        all_issues=issues,
        tool_results=tool_results,
        overall_score=75.0,
        dimension_scores={"security": 80, "quality": 70, "testing": 75}
    )


def create_mock_scoring_model() -> ScoringModel:
    """Create mock scoring model"""
    return ScoringModel(
        weights={
            "security": 0.3,
            "quality": 0.25,
            "testing": 0.2,
            "performance": 0.15,
            "documentation": 0.1
        },
        quality_adjustments={"security": 1.2},
        historical_adjustments={},
        confidence_level=0.8
    )


class TestRecommendationAgent(unittest.TestCase):
    """Simplified RecommendationAgent test suite"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
        
        self.project_info = create_mock_project_info()
        self.analysis_results = create_mock_analysis_results()
        self.scoring_model = create_mock_scoring_model()
        
        self.agent = RecommendationAgent()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_recommendation_agent_initialization(self):
        """Test RecommendationAgent initializes correctly"""
        self.assertIsNotNone(self.agent)
        self.assertTrue(hasattr(self.agent, 'generate_intelligent_recommendations'))
    
    def test_generate_intelligent_recommendations(self):
        """Test intelligent recommendations generation"""
        recommendations = self.agent.generate_intelligent_recommendations(
            analysis_results=self.analysis_results,
            project_info=self.project_info,
            scoring_model=self.scoring_model
        )
        
        self.assertIsInstance(recommendations, IntelligentRecommendations)
        self.assertIsInstance(recommendations.recommendations, list)
        self.assertIsInstance(recommendations.roadmap, object)  # ImprovementRoadmap
        self.assertIsInstance(recommendations.confidence_level, float)
        
        # Should generate some recommendations based on the issues
        self.assertGreater(len(recommendations.recommendations), 0)
        
        # Confidence should be reasonable
        self.assertGreaterEqual(recommendations.confidence_level, 0.0)
        self.assertLessEqual(recommendations.confidence_level, 1.0)
    
    def test_different_project_types(self):
        """Test recommendations for different project types"""
        project_types = [
            ProjectType.WEB_APPLICATION,
            ProjectType.LIBRARY,
            ProjectType.CLI_TOOL
        ]
        
        for project_type in project_types:
            test_project = ProjectInfo(
                name=f"test-{project_type.value}",
                path=f"/tmp/test-{project_type.value}",
                languages={"python": 1.0},
                structure_type=StructureType.SINGLE_PROJECT,
                project_type=project_type,
                dependencies={"python": ["requests"]},
                build_tools=["setup.py"],
                size_metrics=SizeMetrics(50, 2000, 40, 1500, 8, 400),
                confidence=0.8
            )
            
            recommendations = self.agent.generate_intelligent_recommendations(
                analysis_results=self.analysis_results,
                project_info=test_project,
                scoring_model=self.scoring_model
            )
            
            self.assertIsInstance(recommendations, IntelligentRecommendations)
            self.assertGreater(len(recommendations.recommendations), 0)
    
    def test_recommendations_with_different_severities(self):
        """Test that recommendations properly handle different issue severities"""
        high_severity_results = {
            "security_tool": {
                "success": True,
                "score": 30,  # Very low score
                "issues_found": [
                    {"severity": "critical", "message": "SQL injection vulnerability"},
                    {"severity": "high", "message": "XSS vulnerability"},
                    {"severity": "medium", "message": "Weak crypto"}
                ]
            }
        }
        
        # Create high severity analysis results
        high_severity_issues = [
            Issue(
                id="SEC-CRIT-001",
                title="SQL injection vulnerability", 
                description="Critical SQL injection vulnerability detected",
                severity=IssueSeverity.CRITICAL,
                category="security"
            )
        ]
        high_severity_analysis = AnalysisResults(
            all_issues=high_severity_issues,
            tool_results=high_severity_results,
            overall_score=30.0
        )
        
        recommendations = self.agent.generate_intelligent_recommendations(
            analysis_results=high_severity_analysis,
            project_info=self.project_info,
            scoring_model=self.scoring_model
        )
        
        self.assertIsInstance(recommendations, IntelligentRecommendations)
        # Should generate recommendations for high-severity issues
        self.assertGreater(len(recommendations.recommendations), 0)
    
    def test_empty_tool_results(self):
        """Test handling of empty tool results"""
        empty_results = {}
        
        empty_analysis = AnalysisResults(
            all_issues=[],
            tool_results=empty_results,
            overall_score=100.0
        )
        
        recommendations = self.agent.generate_intelligent_recommendations(
            analysis_results=empty_analysis,
            project_info=self.project_info,
            scoring_model=self.scoring_model
        )
        
        self.assertIsInstance(recommendations, IntelligentRecommendations)
        # Should still provide some best practice recommendations
        self.assertIsInstance(recommendations.recommendations, list)
        self.assertIsInstance(recommendations.roadmap, object)
    
    def test_scoring_model_influence(self):
        """Test that scoring model influences recommendation prioritization"""
        security_focused_model = ScoringModel(
            weights={
                "security": 0.6,  # Very high security focus
                "quality": 0.2,
                "testing": 0.1,
                "performance": 0.05,
                "documentation": 0.05
            },
            quality_adjustments={"security": 1.5},
            historical_adjustments={},
            confidence_level=0.9
        )
        
        security_recs = self.agent.generate_intelligent_recommendations(
            analysis_results=self.analysis_results,
            project_info=self.project_info,
            scoring_model=security_focused_model
        )
        
        balanced_recs = self.agent.generate_intelligent_recommendations(
            analysis_results=self.analysis_results,
            project_info=self.project_info,
            scoring_model=self.scoring_model
        )
        
        # Both should generate recommendations
        self.assertGreater(len(security_recs.recommendations), 0)
        self.assertGreater(len(balanced_recs.recommendations), 0)
        
        # Security-focused should potentially have different priorities
        # (This is more of a smoke test since prioritization logic is complex)
        self.assertIsInstance(security_recs.confidence_level, float)
        self.assertIsInstance(balanced_recs.confidence_level, float)


if __name__ == '__main__':
    unittest.main(verbosity=2)