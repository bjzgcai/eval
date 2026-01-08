#!/usr/bin/env python3
"""
Simplified test cases for AI Analyzer - basic functionality tests
"""

import pytest
import unittest
import tempfile
import pathlib
import json
import os
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
import sys
src_dir = pathlib.Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from oss_audit.utils.ai_analyzer import AIAnalyzer
from oss_audit.core.project_detector import ProjectInfo, ProjectType, StructureType, SizeMetrics


class TestAIAnalyzer(unittest.TestCase):
    """Simplified AI Analyzer test suite"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_analyzer_initialization(self):
        """Test AI Analyzer basic initialization"""
        analyzer = AIAnalyzer()
        
        self.assertIsNotNone(analyzer.analysis_rules)
        self.assertIsNotNone(analyzer.maturity_patterns)
        self.assertIsInstance(analyzer.ai_enabled, bool)
    
    def test_analyzer_with_config_file(self):
        """Test AI Analyzer initialization with config"""
        config_content = {
            'ai': {
                'enabled': False,
                'priority': ['rules']
            }
        }
        
        config_file = self.temp_path / "config.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        
        analyzer = AIAnalyzer(config_path=str(config_file))
        
        self.assertFalse(analyzer.ai_enabled)
        self.assertEqual(analyzer.ai_priority, ['rules'])
    
    def test_load_analysis_rules(self):
        """Test loading analysis rules"""
        analyzer = AIAnalyzer()
        
        self.assertIsInstance(analyzer.analysis_rules, dict)
        self.assertGreater(len(analyzer.analysis_rules), 0)
    
    def test_load_maturity_patterns(self):
        """Test loading maturity patterns"""  
        analyzer = AIAnalyzer()
        
        self.assertIsInstance(analyzer.maturity_patterns, dict)
        self.assertGreater(len(analyzer.maturity_patterns), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)