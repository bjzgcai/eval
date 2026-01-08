#!/usr/bin/env python3
"""
Test cases for OSS Audit 2.0 AuditRunner
"""

import unittest
import tempfile
import pathlib
from unittest.mock import Mock, patch

# Add src to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from oss_audit.core.audit_runner import AuditRunner
from oss_audit.core.project_detector import ProjectInfo


class TestAuditRunner(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = pathlib.Path(self.test_dir)
        self.runner = AuditRunner()
    
    def test_audit_runner_initialization(self):
        """Test AuditRunner initializes correctly"""
        runner = AuditRunner()
        self.assertIsNotNone(runner.project_detector)
        self.assertIsNotNone(runner.tool_executor)
        self.assertIsNotNone(runner.report_generator)
    
    def test_project_analysis_phase(self):
        """Test project analysis phase"""
        # Create a simple project structure
        (self.test_path / "README.md").write_text("# Test Project")
        (self.test_path / "src").mkdir()
        (self.test_path / "src" / "main.py").write_text("print('hello')")
        
        project_info = self.runner.project_detector.detect_project_info(str(self.test_path))
        
        self.assertIsInstance(project_info, ProjectInfo)
        self.assertEqual(project_info.name, self.test_path.name)
        self.assertIn('python', project_info.languages)
    
    @patch('oss_audit.core.audit_runner.AuditRunner._run_phase_1')
    @patch('oss_audit.core.audit_runner.AuditRunner._run_phase_2')
    def test_audit_execution(self, mock_phase2, mock_phase1):
        """Test audit execution phases"""
        # Mock the phases to return success
        mock_phase1.return_value = {'success': True, 'project_info': Mock()}
        mock_phase2.return_value = {'success': True, 'tools_executed': 5}
        
        result = self.runner.audit_project(str(self.test_path))
        
        self.assertTrue(result['success'])
        mock_phase1.assert_called_once()
        mock_phase2.assert_called_once()
    
    def test_configuration_loading(self):
        """Test configuration loading"""
        # Test that the runner can handle missing configuration gracefully
        runner = AuditRunner()
        # Should not raise an exception
        self.assertIsNotNone(runner.project_detector)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir)


if __name__ == '__main__':
    unittest.main()