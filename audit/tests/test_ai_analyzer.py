import sys
import os
import pytest
import tempfile
import pathlib
from unittest.mock import patch, MagicMock

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from oss_audit.utils.ai_analyzer import AIAnalyzer

class TestAIAnalyzer:
    """AI分析器测试类"""

    def test_analyzer_initialization(self):
        """测试AI分析器初始化"""
        analyzer = AIAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, 'analysis_rules')
        assert hasattr(analyzer, 'maturity_patterns')
        assert hasattr(analyzer, 'config')

    def test_load_config(self):
        """测试配置文件加载"""
        analyzer = AIAnalyzer()
        config = analyzer._load_config()
        assert isinstance(config, dict)

    @patch('os.environ.get')
    def test_openai_initialization(self, mock_env_get):
        """测试OpenAI初始化"""
        mock_env_get.return_value = "test_openai_key"

        with patch('openai.OpenAI'):
            analyzer = AIAnalyzer()
            # 由于API密钥无效，不会初始化openai_client
            assert hasattr(analyzer, 'use_openai')

    @patch('os.environ.get')
    def test_gemini_initialization(self, mock_env_get):
        """测试Gemini初始化"""
        mock_env_get.return_value = "test_gemini_key"

        with patch('google.generativeai.configure'):
            analyzer = AIAnalyzer()
            # 验证Gemini是否被正确初始化
            assert hasattr(analyzer, 'gemini_model')

    def test_determine_ai_method(self):
        """测试AI方法确定"""
        analyzer = AIAnalyzer()
        method = analyzer._determine_ai_method()
        assert method in ['openai', 'gemini', 'rules']

    def test_analyze_dimension_with_rules(self):
        """测试基于规则的维度分析"""
        analyzer = AIAnalyzer()

        # 模拟维度数据
        dimension_data = {
            'score': 75,
            'status': 'PASS',
            'details': 'Test details'
        }

        result = analyzer.analyze_dimension_with_rules('test_dimension', dimension_data)
        assert isinstance(result, dict)
        assert 'quality_level' in result
        assert 'suggestions' in result
        assert 'improvement_path' in result
        assert 'ai_confidence' in result

    def test_analyze_project_maturity(self):
        """测试项目成熟度分析"""
        analyzer = AIAnalyzer()

        # 模拟项目数据
        project_data = {
            'dimensions': [
                {'name': 'test1', 'score': 80},
                {'name': 'test2', 'score': 75}
            ],
            'average_score': 77.5
        }

        result = analyzer.analyze_project_maturity(project_data)
        assert isinstance(result, dict)
        assert 'maturity_level' in result
        assert 'ai_confidence' in result  # 修正属性名

    @patch('openai.OpenAI')
    def test_openai_analysis(self, mock_openai):
        """测试OpenAI分析"""
        # 模拟OpenAI客户端
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"analysis": "test"}'
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        analyzer = AIAnalyzer(openai_api_key="test_key")
        analyzer.use_openai = True
        analyzer.openai_client = mock_client

        # 使用正确的方法名
        result = analyzer.analyze_dimension_with_openai("test_dimension", {"score": 75})
        assert isinstance(result, dict)

    @patch('google.generativeai.GenerativeModel')
    def test_gemini_analysis(self, mock_generative_model):
        """测试Gemini分析"""
        # 模拟Gemini响应
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"analysis": "test"}'
        mock_model.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model

        analyzer = AIAnalyzer(gemini_api_key="test_key")
        analyzer.use_gemini = True
        analyzer.gemini_model = mock_model

        # 使用正确的方法名
        result = analyzer.analyze_dimension_with_gemini("test_dimension", {"score": 75})
        assert isinstance(result, dict)

class TestAIAnalyzerIntegration:
    """AI分析器集成测试"""

    def test_full_analysis_workflow(self):
        """测试完整分析工作流"""
        analyzer = AIAnalyzer()

        # 模拟完整的项目数据
        project_data = {
            'name': 'test_project',
            'dimensions': [
                {
                    'name': '代码结构与可维护性',
                    'score': 80,
                    'status': 'PASS',
                    'details': 'Good code structure'
                },
                {
                    'name': '测试覆盖与质量保障',
                    'score': 75,
                    'status': 'PASS',
                    'details': 'Adequate test coverage'
                }
            ],
            'average_score': 77.5
        }

        # 测试维度分析
        for dimension in project_data['dimensions']:
            result = analyzer.analyze_dimension(dimension['name'], dimension)
            assert isinstance(result, dict)

        # 测试项目成熟度分析
        maturity_result = analyzer.analyze_project_maturity(project_data)
        assert isinstance(maturity_result, dict)

if __name__ == "__main__":
    pytest.main([__file__])
