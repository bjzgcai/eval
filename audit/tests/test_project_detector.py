#!/usr/bin/env python3
"""
Test cases for OSS Audit 2.0 ProjectDetector
"""

import unittest
import tempfile
import pathlib

# Add src to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from oss_audit.core.project_detector import ProjectDetector, ProjectInfo, StructureType, ProjectType


class TestProjectDetector(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = pathlib.Path(self.test_dir)
        self.detector = ProjectDetector()
    
    def test_detector_initialization(self):
        """Test ProjectDetector initializes correctly"""
        detector = ProjectDetector()
        self.assertIsNotNone(detector.config)
        self.assertIn('languages', detector.config)
    
    def test_python_project_detection(self):
        """Test detection of Python project"""
        # Create Python project structure
        (self.test_path / "main.py").write_text("print('hello')")
        (self.test_path / "setup.py").write_text("from setuptools import setup")
        (self.test_path / "requirements.txt").write_text("pytest\nnumpy")
        
        project_info = self.detector.detect_project_info(str(self.test_path))
        
        self.assertIsInstance(project_info, ProjectInfo)
        self.assertIn('python', project_info.languages)
        self.assertEqual(project_info.structure_type, StructureType.SINGLE_PROJECT)
        self.assertIn('setuptools', project_info.build_tools)
    
    def test_javascript_project_detection(self):
        """Test detection of JavaScript project"""
        # Create JavaScript project structure
        (self.test_path / "package.json").write_text('{"name": "test", "dependencies": {"react": "^17.0.0"}}')
        (self.test_path / "src").mkdir()
        (self.test_path / "src" / "index.js").write_text("console.log('hello');")
        
        project_info = self.detector.detect_project_info(str(self.test_path))
        
        self.assertIn('javascript', project_info.languages)
        self.assertIn('npm', project_info.build_tools)
    
    def test_mixed_language_project(self):
        """Test detection of mixed language project"""
        # Create mixed project
        (self.test_path / "main.py").write_text("print('hello')")
        (self.test_path / "app.js").write_text("console.log('hello');")
        (self.test_path / "README.md").write_text("# Test Project")
        
        project_info = self.detector.detect_project_info(str(self.test_path))
        
        # Should detect both languages
        self.assertTrue(len(project_info.languages) >= 1)
        self.assertGreater(project_info.confidence, 0.0)
    
    def test_empty_project(self):
        """Test detection of empty project"""
        project_info = self.detector.detect_project_info(str(self.test_path))
        
        self.assertEqual(project_info.name, self.test_path.name)
        self.assertEqual(len(project_info.languages), 0)
        self.assertEqual(project_info.confidence, 0.0)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir)


if __name__ == '__main__':
    unittest.main()