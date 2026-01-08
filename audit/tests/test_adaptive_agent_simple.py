#!/usr/bin/env python3
"""
AdaptiveAgent 简化测试用例 - 基于实际API的测试
"""

import pytest
import unittest
import tempfile
import pathlib
import os
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
import sys
src_dir = pathlib.Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from oss_audit.core.adaptive_agent import AdaptiveAgent, ScoringModel, OptimizationActions
from oss_audit.core.project_detector import ProjectInfo, ProjectType, StructureType, SizeMetrics


def create_mock_project_info() -> ProjectInfo:
    """Create mock project info for testing"""
    return ProjectInfo(
        name="adaptive-test-project",
        path="/tmp/adaptive-test-project",
        languages={"python": 0.7, "javascript": 0.3},
        structure_type=StructureType.SINGLE_PROJECT,
        project_type=ProjectType.WEB_APPLICATION,
        dependencies={"python": ["flask", "requests"], "javascript": ["react"]},
        build_tools=["setup.py", "package.json"],
        size_metrics=SizeMetrics(150, 8000, 120, 6000, 25, 1500),
        confidence=0.90
    )


def create_mock_tool_results():
    """Create mock tool results"""
    return {
        "pylint": {
            "success": True,
            "score": 75,
            "issues_found": [{"severity": "medium", "count": 5}]
        },
        "bandit": {
            "success": True,
            "score": 85,
            "issues_found": [{"severity": "low", "count": 2}]
        },
        "pytest": {
            "success": True,
            "score": 80,
            "coverage": 78.5
        }
    }


class TestAdaptiveAgent(unittest.TestCase):
    """Simplified AdaptiveAgent test suite"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
        
        self.project_info = create_mock_project_info()
        self.tool_results = create_mock_tool_results()
        
        self.agent = AdaptiveAgent()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_adaptive_agent_initialization(self):
        """Test AdaptiveAgent initializes correctly"""
        self.assertIsNotNone(self.agent)
        self.assertTrue(hasattr(self.agent, 'adapt_scoring_model'))
        self.assertTrue(hasattr(self.agent, 'optimize_analysis_process'))
    
    def test_adapt_scoring_model(self):
        """Test basic scoring model adaptation"""
        scoring_model = self.agent.adapt_scoring_model(
            project_info=self.project_info,
            tool_results=self.tool_results
        )
        
        self.assertIsInstance(scoring_model, ScoringModel)
        self.assertIsInstance(scoring_model.weights, dict)
        self.assertGreater(len(scoring_model.weights), 0)
        
        # Weights should be reasonable
        for weight in scoring_model.weights.values():
            self.assertGreaterEqual(weight, 0)
            self.assertLessEqual(weight, 1)
        
        # Confidence should be in valid range
        self.assertGreaterEqual(scoring_model.confidence_level, 0)
        self.assertLessEqual(scoring_model.confidence_level, 1)
    
    def test_optimize_analysis_process(self):
        """Test analysis process optimization"""
        optimization = self.agent.optimize_analysis_process(
            current_results=self.tool_results,
            project_info=self.project_info
        )
        
        self.assertIsInstance(optimization, OptimizationActions)
        self.assertIsInstance(optimization.additional_tools, list)
        self.assertIsInstance(optimization.supplementary_analysis, list)
    
    def test_different_project_types(self):
        """Test adaptation with different project types"""
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
            
            scoring_model = self.agent.adapt_scoring_model(
                project_info=test_project,
                tool_results=self.tool_results
            )
            
            self.assertIsInstance(scoring_model, ScoringModel)
            self.assertGreater(len(scoring_model.weights), 0)
    
    def test_edge_cases(self):
        """Test edge case handling"""
        # Test with empty tool results
        empty_results = {}
        scoring_model = self.agent.adapt_scoring_model(
            project_info=self.project_info,
            tool_results=empty_results
        )
        
        self.assertIsInstance(scoring_model, ScoringModel)
        
        # Test with minimal project
        minimal_project = ProjectInfo(
            name="minimal",
            path="/tmp/minimal",
            languages={"python": 1.0},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            dependencies={},
            build_tools=[],
            size_metrics=SizeMetrics(1, 10, 1, 5, 0, 0),
            confidence=0.5
        )
        
        minimal_model = self.agent.adapt_scoring_model(
            project_info=minimal_project,
            tool_results=self.tool_results
        )
        
        self.assertIsInstance(minimal_model, ScoringModel)
    
    def test_get_adaptation_stats(self):
        """Test adaptation statistics"""
        # Run some adaptations first
        self.agent.adapt_scoring_model(
            project_info=self.project_info,
            tool_results=self.tool_results
        )
        
        stats = self.agent.get_adaptation_stats()
        
        self.assertIsInstance(stats, dict)
        # Should have some statistical information
        self.assertGreater(len(stats), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)