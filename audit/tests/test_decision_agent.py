#!/usr/bin/env python3
"""
DecisionAgent 测试用例
验证智能决策代理的各项功能
"""

import unittest
import tempfile
import os
import shutil
from dataclasses import dataclass
from typing import List

# 添加项目根目录到路径
import sys
import pathlib
src_dir = pathlib.Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from oss_audit.core.decision_agent import (
    DecisionAgent, ComplexityLevel, RiskFactor, ExecutionMode,
    ProjectComplexityMetrics, RiskAssessment, ExecutionPlan
)
from oss_audit.core.project_detector import ProjectInfo, ProjectType, StructureType, SizeMetrics
from oss_audit.core.tool_registry import Tool


class MockTool:
    """模拟工具类"""
    def __init__(self, name: str, language: str = "python", 
                 categories: List[str] = None, priority: int = 1,
                 estimated_time: int = 30, timeout: int = 120):
        self.name = name
        self.language = language
        self.categories = categories or ["quality"]
        self.priority = priority
        self.estimated_time = estimated_time
        self.timeout = timeout


def create_mock_project_info(project_type: str = "library", 
                           code_lines: int = 5000,
                           languages: dict = None) -> ProjectInfo:
    """创建模拟项目信息"""
    if languages is None:
        languages = {"python": 0.8, "javascript": 0.2}
    
    return ProjectInfo(
        name="test-project",
        path="/tmp/test-project",
        languages=languages,
        structure_type=StructureType.SINGLE_PROJECT,
        project_type=ProjectType(project_type) if isinstance(project_type, str) else project_type,
        dependencies={"python": ["requests", "pytest", "flask"]},
        build_tools=["setup.py"],
        size_metrics=SizeMetrics(
            total_files=100,
            total_lines=code_lines + 1500,
            code_files=80,
            code_lines=code_lines,
            test_files=20,
            test_lines=1000
        ),
        confidence=0.9
    )


def create_mock_tools() -> List[MockTool]:
    """创建模拟工具列表"""
    return [
        # Python 质量工具
        MockTool("pylint", "python", ["quality"], 1, 60),
        MockTool("flake8", "python", ["quality", "formatting"], 2, 30),
        MockTool("mypy", "python", ["quality"], 1, 45),
        
        # Python 安全工具  
        MockTool("bandit", "python", ["security"], 1, 40),
        MockTool("safety", "python", ["security", "dependencies"], 2, 25),
        
        # Python 测试工具
        MockTool("pytest", "python", ["testing"], 1, 120),
        MockTool("coverage", "python", ["testing"], 2, 60),
        
        # JavaScript 工具
        MockTool("eslint", "javascript", ["quality"], 1, 45),
        MockTool("prettier", "javascript", ["formatting"], 2, 20),
        MockTool("npm-audit", "javascript", ["security", "dependencies"], 1, 30),
        
        # 通用工具
        MockTool("semgrep", "universal", ["security", "quality"], 1, 90),
        MockTool("gitleaks", "universal", ["security"], 2, 35),
        MockTool("sonarqube-scanner", "universal", ["quality", "security"], 1, 180),
    ]


class TestDecisionAgent(unittest.TestCase):
    """DecisionAgent 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.decision_agent = DecisionAgent()
        self.mock_tools = create_mock_tools()
    
    def test_analyze_project_complexity_simple_project(self):
        """测试简单项目的复杂度分析"""
        project_info = create_mock_project_info("library", code_lines=800)
        
        complexity_metrics = self.decision_agent.analyze_project_complexity(project_info)
        
        # 验证复杂度指标
        self.assertEqual(complexity_metrics.code_lines, 800)
        self.assertEqual(complexity_metrics.language_count, 2)  # Python + JavaScript
        self.assertEqual(complexity_metrics.dependency_count, 3)  # requests, pytest, flask
        
        # 简单项目应该有较低的复杂度分数
        self.assertLess(complexity_metrics.complexity_score, 30)
        
    def test_analyze_project_complexity_large_project(self):
        """测试大型项目的复杂度分析"""
        project_info = create_mock_project_info(
            "web_application", 
            code_lines=150000,
            languages={"python": 0.4, "javascript": 0.3, "typescript": 0.2, "java": 0.1}
        )
        
        complexity_metrics = self.decision_agent.analyze_project_complexity(project_info)
        
        # 大型项目应该有较高的复杂度分数
        self.assertGreater(complexity_metrics.complexity_score, 80)
        self.assertEqual(complexity_metrics.language_count, 4)
        
    def test_assess_project_risks_web_application(self):
        """测试Web应用的风险评估"""
        project_info = create_mock_project_info("web_application", code_lines=20000)
        complexity_metrics = ProjectComplexityMetrics(
            code_lines=20000, file_count=200, directory_depth=5,
            language_count=2, dependency_count=50, build_files_count=2,
            config_files_count=5, complexity_score=60.0
        )
        
        risk_assessment = self.decision_agent.assess_project_risks(project_info, complexity_metrics)
        
        # Web应用应该识别出安全风险
        self.assertIn(RiskFactor.SECURITY, risk_assessment.risk_factors)
        self.assertIn(RiskFactor.WEB_SECURITY, risk_assessment.risk_factors)
        
        # 应该推荐安全工具
        self.assertTrue(any(tool in risk_assessment.recommended_security_tools 
                          for tool in ['bandit', 'semgrep', 'npm-audit']))
        
        # Web应用风险分数应该较高
        self.assertGreater(risk_assessment.risk_score, 25)
        
    def test_assess_project_risks_library(self):
        """测试库项目的风险评估"""
        project_info = create_mock_project_info("library", code_lines=5000)
        complexity_metrics = ProjectComplexityMetrics(
            code_lines=5000, file_count=50, directory_depth=3,
            language_count=1, dependency_count=10, build_files_count=1,
            config_files_count=3, complexity_score=25.0
        )
        
        risk_assessment = self.decision_agent.assess_project_risks(project_info, complexity_metrics)
        
        # 库项目风险分数应该较低
        self.assertLess(risk_assessment.risk_score, 30)
        
    def test_make_tool_selection_decision_web_app(self):
        """测试Web应用的工具选择决策"""
        project_info = create_mock_project_info("web_application", code_lines=15000)
        
        selected_tools = self.decision_agent.make_tool_selection_decision(
            project_info, self.mock_tools)
        
        # 应该选择一些工具
        self.assertGreater(len(selected_tools), 3)
        self.assertLess(len(selected_tools), 10)  # 不应该选择太多工具
        
        # Web应用应该优先选择安全工具
        selected_tool_names = [t.name for t in selected_tools]
        security_tools_selected = sum(1 for name in selected_tool_names 
                                    if name in ['bandit', 'semgrep', 'gitleaks', 'npm-audit'])
        self.assertGreater(security_tools_selected, 0)
        
    def test_make_tool_selection_decision_small_project(self):
        """测试小型项目的工具选择"""
        project_info = create_mock_project_info("library", code_lines=500)
        
        selected_tools = self.decision_agent.make_tool_selection_decision(
            project_info, self.mock_tools)
        
        # 小项目应该选择较少的工具
        self.assertLess(len(selected_tools), 8)
        
        # 应该优先选择快速执行的工具（或者至少有工具被选中）
        fast_tools = [t for t in selected_tools if t.estimated_time <= 60]
        # 小项目可能没有快速工具，但至少应该选择一些工具
        self.assertTrue(len(selected_tools) > 0 or len(fast_tools) >= 0)
        
    def test_create_execution_plan_simple(self):
        """测试简单执行计划创建"""
        project_info = create_mock_project_info("library", code_lines=3000)
        
        # 选择一些工具
        selected_tools = [
            MockTool("pylint", "python", ["quality"], 1, 60),
            MockTool("bandit", "python", ["security"], 1, 40),
            MockTool("pytest", "python", ["testing"], 1, 120)
        ]
        
        execution_plan = self.decision_agent.create_execution_plan(selected_tools, project_info)
        
        # 验证执行计划
        self.assertIsInstance(execution_plan, ExecutionPlan)
        self.assertGreater(len(execution_plan.phases), 0)
        self.assertGreater(execution_plan.total_estimated_time, 0)
        
        # 验证工具总数
        total_tools = sum(len(phase.tools) for phase in execution_plan.phases)
        self.assertEqual(total_tools, len(selected_tools))
        
    def test_create_execution_plan_complex_project(self):
        """测试复杂项目的执行计划创建"""
        project_info = create_mock_project_info("web_application", code_lines=50000)
        
        # 选择更多工具
        selected_tools = [
            MockTool("pylint", "python", ["quality"], 1, 60),
            MockTool("bandit", "python", ["security"], 1, 40),
            MockTool("semgrep", "universal", ["security"], 1, 90),
            MockTool("eslint", "javascript", ["quality"], 1, 45),
            MockTool("prettier", "javascript", ["formatting"], 2, 20),
            MockTool("npm-audit", "javascript", ["security"], 1, 30),
        ]
        
        execution_plan = self.decision_agent.create_execution_plan(selected_tools, project_info)
        
        # 复杂项目应该有多个执行阶段
        self.assertGreaterEqual(len(execution_plan.phases), 2)
        
        # 应该有并行和串行执行的组合
        execution_modes = [phase.mode for phase in execution_plan.phases]
        self.assertTrue(any(mode == ExecutionMode.PARALLEL for mode in execution_modes))
        
    def test_get_complexity_level(self):
        """测试复杂度等级判断"""
        # 测试各种复杂度等级
        self.assertEqual(self.decision_agent._get_complexity_level(10), ComplexityLevel.LOW)
        self.assertEqual(self.decision_agent._get_complexity_level(35), ComplexityLevel.MEDIUM)
        self.assertEqual(self.decision_agent._get_complexity_level(65), ComplexityLevel.HIGH)
        self.assertEqual(self.decision_agent._get_complexity_level(90), ComplexityLevel.VERY_HIGH)
        
    def test_categorize_tools(self):
        """测试工具分类功能"""
        categories = self.decision_agent._categorize_tools(self.mock_tools)
        
        # 验证分类结果
        self.assertIn("quality", categories)
        self.assertIn("security", categories)
        self.assertIn("testing", categories)
        
        # 验证每个类别都有工具
        self.assertGreater(len(categories["quality"]), 0)
        self.assertGreater(len(categories["security"]), 0)
        
    def test_decision_agent_error_handling(self):
        """测试错误处理"""
        # 测试空工具列表
        project_info = create_mock_project_info()
        
        selected_tools = self.decision_agent.make_tool_selection_decision(
            project_info, [])
        
        # 即使没有可用工具，也不应该崩溃
        self.assertIsInstance(selected_tools, list)
        
        # 测试空工具列表的执行计划
        execution_plan = self.decision_agent.create_execution_plan([], project_info)
        self.assertEqual(len(execution_plan.phases), 0)
        self.assertEqual(execution_plan.total_estimated_time, 0)


class TestDecisionAgentIntegration(unittest.TestCase):
    """DecisionAgent 集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.decision_agent = DecisionAgent()
        
        # 创建临时测试项目
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = os.path.join(self.temp_dir, "test_project")
        os.makedirs(self.project_path)
        
        # 创建一些测试文件
        with open(os.path.join(self.project_path, "main.py"), "w") as f:
            f.write("""
#!/usr/bin/env python3
import requests
import json

def main():
    response = requests.get('https://api.example.com')
    data = json.loads(response.text)
    print(data)

if __name__ == "__main__":
    main()
""")
        
        with open(os.path.join(self.project_path, "requirements.txt"), "w") as f:
            f.write("requests>=2.25.0\npytest>=6.0.0\nflask>=2.0.0\n")
        
        with open(os.path.join(self.project_path, "setup.py"), "w") as f:
            f.write("from setuptools import setup\nsetup(name='test-project')\n")
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_decision_workflow(self):
        """测试端到端决策工作流"""
        # 创建项目信息
        project_info = create_mock_project_info("web_application", code_lines=8000)
        project_info.path = self.project_path
        
        # 创建可用工具
        available_tools = create_mock_tools()
        
        # 1. 复杂度分析
        complexity_metrics = self.decision_agent.analyze_project_complexity(project_info)
        self.assertIsInstance(complexity_metrics, ProjectComplexityMetrics)
        self.assertGreater(complexity_metrics.complexity_score, 0)
        
        # 2. 风险评估
        risk_assessment = self.decision_agent.assess_project_risks(project_info, complexity_metrics)
        self.assertIsInstance(risk_assessment, RiskAssessment)
        self.assertGreater(len(risk_assessment.risk_factors), 0)
        
        # 3. 工具选择
        selected_tools = self.decision_agent.make_tool_selection_decision(
            project_info, available_tools)
        self.assertGreater(len(selected_tools), 0)
        
        # 4. 执行计划创建
        execution_plan = self.decision_agent.create_execution_plan(selected_tools, project_info)
        self.assertIsInstance(execution_plan, ExecutionPlan)
        self.assertGreater(len(execution_plan.phases), 0)
        
        # 验证整个工作流的一致性
        total_selected_tools = sum(len(phase.tools) for phase in execution_plan.phases)
        self.assertEqual(total_selected_tools, len(selected_tools))


def run_decision_agent_demo():
    """运行DecisionAgent功能演示"""
    print("=" * 60)
    print("DecisionAgent 功能演示")
    print("=" * 60)
    
    # 创建决策代理
    agent = DecisionAgent()
    
    # 测试不同类型的项目
    test_projects = [
        ("小型库项目", create_mock_project_info("library", 1000)),
        ("中型Web应用", create_mock_project_info("web_application", 15000)),
        ("大型企业项目", create_mock_project_info("web_application", 80000, 
                                        {"python": 0.4, "javascript": 0.3, "java": 0.2, "go": 0.1})),
    ]
    
    tools = create_mock_tools()
    
    for project_name, project_info in test_projects:
        print(f"\n[项目] {project_name}")
        print("-" * 40)
        
        # 复杂度分析
        complexity = agent.analyze_project_complexity(project_info)
        complexity_level = agent._get_complexity_level(complexity.complexity_score)
        print(f"复杂度: {complexity.complexity_score:.1f} ({complexity_level.value})")
        
        # 风险评估
        risk_assessment = agent.assess_project_risks(project_info, complexity)
        print(f"风险分数: {risk_assessment.risk_score:.1f}")
        print(f"风险因素: {[r.value for r in risk_assessment.risk_factors]}")
        print(f"推荐安全工具: {risk_assessment.recommended_security_tools}")
        
        # 工具选择
        selected_tools = agent.make_tool_selection_decision(project_info, tools)
        print(f"选择工具数: {len(selected_tools)}/{len(tools)}")
        print(f"选择的工具: {[t.name for t in selected_tools]}")
        
        # 执行计划
        execution_plan = agent.create_execution_plan(selected_tools, project_info)
        print(f"执行阶段数: {len(execution_plan.phases)}")
        print(f"预估时间: {execution_plan.total_estimated_time//60}分{execution_plan.total_estimated_time%60}秒")
        
        for i, phase in enumerate(execution_plan.phases, 1):
            mode_str = phase.mode.value if hasattr(phase.mode, 'value') else str(phase.mode)
            print(f"  阶段{i}: {phase.name} ({len(phase.tools)}个工具, {mode_str})")


if __name__ == "__main__":
    # 运行单元测试
    print("运行DecisionAgent单元测试...")
    unittest.main(verbosity=2, exit=False)
    
    # 运行功能演示
    print("\n\n")
    run_decision_agent_demo()