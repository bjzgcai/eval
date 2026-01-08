import pytest
import tempfile
import pathlib
import shutil
import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@pytest.fixture
def temp_project_dir():
    """创建临时项目目录的fixture"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)

        # 创建基本的项目结构
        (temp_path / "README.md").write_text("# Test Project\n\nThis is a test project.")
        (temp_path / "LICENSE").write_text("MIT License")
        (temp_path / "requirements.txt").write_text("pytest==8.2.1\nflask==3.0.3")
        (temp_path / "setup.py").write_text("from setuptools import setup\nsetup(name='test-project')")
        (temp_path / "Dockerfile").write_text("FROM python:3.9\nCOPY . .\nCMD ['python', 'main.py']")

        # 创建测试目录
        (temp_path / "tests").mkdir()
        (temp_path / "tests" / "test_sample.py").write_text("def test_sample():\n    assert True")

        # 创建文档目录
        (temp_path / "docs").mkdir()
        (temp_path / "docs" / "README.md").write_text("# Documentation")

        # 创建源代码目录
        (temp_path / "src").mkdir()
        (temp_path / "src" / "main.py").write_text("def main():\n    return 'Hello, World!'")

        yield temp_path

@pytest.fixture
def sample_config():
    """提供示例配置的fixture"""
    return {
        'ai': {
            'priority': ['openai', 'gemini', 'rules'],
            'openai': {
                'api_key': 'test_openai_key',
                'base_url': 'https://api.openai.com/v1',
                'stream': False
            },
            'gemini': {
                'api_key': 'test_gemini_key'
            },
            'rules': {
                'enabled': True,
                'fallback': True
            }
        },
        'tools': {
            'pylint': {
                'enabled': True,
                'max_line_length': 120
            },
            'coverage': {
                'enabled': True,
                'min_coverage': 70
            },
            'security': {
                'bandit': {
                    'enabled': True,
                    'severity_level': 'medium'
                },
                'gitleaks': {
                    'enabled': True
                }
            }
        },
        'reports': {
            'formats': ['html', 'json'],
            'output_dir': 'reports',
            'detailed': True,
            'include_ai_analysis': True
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'oss_audit.log'
        }
    }

@pytest.fixture
def mock_environment():
    """模拟环境变量的fixture"""
    original_env = os.environ.copy()

    # 设置测试环境变量
    os.environ['OPENAI_API_KEY'] = 'test_openai_key'
    os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
    os.environ['PROJECT_PATH'] = '/test/project/path'

    yield

    # 恢复原始环境变量
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def sample_dimension_data():
    """提供示例维度数据的fixture"""
    return {
        'score': 75,
        'status': 'PASS',
        'details': 'This is a test dimension with good performance',
        'tools_used': ['pylint', 'coverage'],
        'issues_found': [],
        'recommendations': ['Add more tests', 'Improve documentation']
    }

@pytest.fixture
def sample_project_data():
    """提供示例项目数据的fixture"""
    return {
        'name': 'test-project',
        'path': '/test/project/path',
        'dimensions': [
            {
                'name': '代码结构与可维护性',
                'score': 80,
                'status': 'PASS',
                'details': 'Good code structure and maintainability'
            },
            {
                'name': '测试覆盖与质量保障',
                'score': 75,
                'status': 'PASS',
                'details': 'Adequate test coverage'
            },
            {
                'name': '构建与工程可重复性',
                'score': 70,
                'status': 'WARN',
                'details': 'Build process needs improvement'
            }
        ],
        'average_score': 75.0,
        'total_dimensions': 3,
        'passed_dimensions': 2
    }

# pytest配置
def pytest_configure(config):
    """pytest配置"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )

def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    for item in items:
        # 为没有标记的测试添加unit标记
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)
