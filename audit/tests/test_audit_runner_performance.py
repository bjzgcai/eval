"""
测试AuditRunner集成性能监控功能
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from oss_audit.core.audit_runner import AuditRunner
from oss_audit.utils.performance_monitor import PerformanceProfiler, BaselineManager


class TestAuditRunnerPerformanceIntegration:
    """测试AuditRunner性能监控集成"""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """创建临时测试项目"""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        
        # 创建基本Python项目结构
        (project_dir / "src").mkdir()
        (project_dir / "src" / "__init__.py").write_text("")
        (project_dir / "src" / "main.py").write_text("def hello(): return 'world'")
        (project_dir / "setup.py").write_text("from setuptools import setup\nsetup(name='test')")
        (project_dir / "README.md").write_text("# Test Project")
        
        return str(project_dir)
    
    @pytest.fixture
    def temp_baseline_file(self, tmp_path):
        """临时基线文件"""
        return str(tmp_path / "test_baselines.json")
    
    def test_audit_runner_has_performance_components(self):
        """测试AuditRunner包含性能监控组件"""
        runner = AuditRunner()
        
        # 验证性能监控组件已初始化
        assert hasattr(runner, 'profiler')
        assert hasattr(runner, 'baseline_manager')
        assert hasattr(runner, 'performance_optimizer')
        
        # 验证组件类型
        assert isinstance(runner.profiler, PerformanceProfiler)
        assert isinstance(runner.baseline_manager, BaselineManager)
    
    @patch('oss_audit.core.project_detector.ProjectDetector')
    @patch('oss_audit.core.tool_executor.ToolExecutor')
    @patch('oss_audit.core.report_generator.ReportGenerator')
    def test_audit_with_performance_monitoring(self, mock_report_gen, mock_tool_exec, mock_detector, temp_project, temp_baseline_file):
        """测试带性能监控的完整审计流程"""
        
        # Mock ProjectDetector
        mock_project_info = Mock()
        mock_project_info.name = "test_project"
        mock_project_info.languages = ["python"]
        mock_project_info.project_type.value = "cli_tool"
        mock_project_info.size_metrics.code_lines = 100
        mock_project_info.get_primary_language.return_value = "python"
        mock_project_info.confidence = 0.9
        mock_project_info.path = temp_project
        
        mock_detector_instance = Mock()
        mock_detector_instance.detect_project_info.return_value = mock_project_info
        mock_detector.return_value = mock_detector_instance
        
        # Mock ToolExecutor
        mock_execution_plan = Mock()
        mock_execution_plan.phases = []
        mock_execution_plan.get_total_estimated_time.return_value = 30
        
        mock_tool_exec_instance = Mock()
        mock_tool_exec_instance.discover_available_tools.return_value = []
        mock_tool_exec_instance.create_execution_plan.return_value = mock_execution_plan
        mock_tool_exec_instance.execute_tools.return_value = {}
        mock_tool_exec_instance.get_execution_stats.return_value = {
            'total_tools': 2, 'successful_tools': 2, 'failed_tools': 0
        }
        mock_tool_exec.return_value = mock_tool_exec_instance
        
        # Mock ReportGenerator
        mock_report_gen_instance = Mock()
        mock_report_gen_instance.generate_adaptive_audit_report.return_value = f"{temp_project}/report.html"
        mock_report_gen.return_value = mock_report_gen_instance
        
        # Mock Agent创建函数
        with patch('oss_audit.core.audit_runner.create_decision_agent') as mock_decision, \
             patch('oss_audit.core.audit_runner.create_adaptive_agent') as mock_adaptive, \
             patch('oss_audit.core.audit_runner.create_recommendation_agent') as mock_recommendation:
            
            mock_decision_agent = Mock()
            mock_decision_agent.make_tool_selection_decision.return_value = []
            mock_decision_agent.create_execution_plan.return_value = mock_execution_plan
            mock_decision.return_value = mock_decision_agent
            
            mock_adaptive_agent = Mock()
            mock_scoring_model = Mock()
            mock_scoring_model.confidence_level = 0.8
            mock_scoring_model.weights = {'security': 0.25, 'quality': 0.25}
            mock_scoring_model.quality_adjustments = {}
            mock_adaptive_agent.adapt_scoring_model.return_value = mock_scoring_model
            mock_adaptive_agent.optimize_analysis_process.return_value = []
            mock_adaptive.return_value = mock_adaptive_agent
            
            mock_recommendation_agent = Mock()
            mock_recommendation_result = Mock()
            mock_recommendation_result.recommendations = []
            mock_recommendation_result.roadmap.phases = []
            mock_recommendation_agent.generate_intelligent_recommendations.return_value = mock_recommendation_result
            mock_recommendation.return_value = mock_recommendation_agent
            
            # 创建AuditRunner并使用自定义基线文件
            runner = AuditRunner()
            runner.baseline_manager = BaselineManager(temp_baseline_file)
            
            # 执行审计
            result = runner.audit_project(temp_project)
            
            # 验证结果
            assert result is not None
            assert result.endswith("report.html")
            
            # 验证性能监控数据被记录
            stats = runner.profiler.get_operation_stats("full_audit")
            assert stats is not None
            assert 'execution_time' in stats
            
            # 验证自定义指标被记录
            custom_metrics = stats.get('custom_metrics', {})
            assert 'project_path_length' in custom_metrics
            assert 'project_files_count' in custom_metrics
            assert 'available_tools_count' in custom_metrics
            assert 'selected_tools_count' in custom_metrics
    
    @patch('oss_audit.utils.performance_monitor.psutil.Process')
    def test_performance_baseline_creation(self, mock_process, temp_project, temp_baseline_file):
        """测试性能基线创建"""
        
        # Mock psutil
        mock_process_instance = Mock()
        mock_process_instance.cpu_percent.return_value = 20.0
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_process_instance.memory_percent.return_value = 10.0
        mock_process_instance.io_counters.return_value.read_bytes = 1024
        mock_process_instance.io_counters.return_value.write_bytes = 512
        mock_process.return_value = mock_process_instance
        
        with patch('psutil.net_io_counters') as mock_net:
            mock_net.return_value.bytes_sent = 2048
            mock_net.return_value.bytes_recv = 1024
            
            # 创建BaselineManager
            baseline_manager = BaselineManager(temp_baseline_file)
            
            # 模拟性能统计数据
            mock_stats = {
                'system_metrics': {
                    'cpu_stats': {'avg': 25.0},
                    'memory_stats': {'avg': 100 * 1024 * 1024},
                    'total_disk_read_mb': 10.0,
                    'total_disk_write_mb': 5.0
                },
                'execution_time': {'avg': 45.0}
            }
            
            # 创建基线
            baseline = baseline_manager.create_baseline(
                "test_project_cli_tool",
                mock_stats,
                {"project_type": "cli_tool", "files_count": 50}
            )
            
            # 验证基线创建成功
            assert baseline is not None
            assert baseline.cpu_baseline == 25.0
            assert baseline.execution_time_baseline == 45.0
            assert baseline.project_characteristics["project_type"] == "cli_tool"
            
            # 验证基线能被重新加载
            new_manager = BaselineManager(temp_baseline_file)
            loaded_baseline = new_manager.get_baseline("test_project_cli_tool")
            assert loaded_baseline is not None
            assert loaded_baseline.cpu_baseline == 25.0
    
    def test_performance_optimization_analysis(self):
        """测试性能优化分析"""
        runner = AuditRunner()
        
        # 模拟较差的性能数据
        poor_stats = {
            'system_metrics': {
                'peak_memory_mb': 1200.0,  # 高内存使用
                'memory_percent_stats': {'avg': 85.0},  # 高内存百分比
                'cpu_stats': {'avg': 85.0, 'max': 95.0},  # 高CPU使用
                'total_disk_read_mb': 120.0,
                'total_disk_write_mb': 60.0
            },
            'execution_time': {'avg': 320.0}  # 超过5分钟
        }
        
        # 执行优化分析
        analysis = runner.performance_optimizer.analyze_performance(poor_stats)
        
        # 验证分析结果
        assert analysis['performance_score'] < 100
        assert len(analysis['issues']) > 0
        assert len(analysis['recommendations']) > 0
        assert analysis['performance_level'] in ['差', '较差', '一般']
        
        # 验证具体问题被识别
        issues = analysis['issues']
        assert any('内存' in issue for issue in issues)
        assert any('CPU' in issue for issue in issues)
        assert any('执行时间' in issue for issue in issues)
    
    def test_performance_metrics_recording(self, temp_project):
        """测试性能指标记录"""
        runner = AuditRunner()
        
        # 记录一些自定义指标
        runner.profiler.record_metric("test_files_processed", 10)
        runner.profiler.record_metric("test_issues_found", 5)
        runner.profiler.record_metric("test_tools_executed", 3)
        
        # 验证指标被正确记录
        custom_metrics = runner.profiler.custom_metrics
        
        assert "test_files_processed" in custom_metrics
        assert "test_issues_found" in custom_metrics
        assert "test_tools_executed" in custom_metrics
        
        assert custom_metrics["test_files_processed"][-1]["value"] == 10
        assert custom_metrics["test_issues_found"][-1]["value"] == 5
        assert custom_metrics["test_tools_executed"][-1]["value"] == 3
    
    def test_performance_stats_collection(self):
        """测试性能统计收集"""
        runner = AuditRunner()
        
        # 模拟执行一个简单操作
        with runner.profiler.profile("test_operation", collect_system_metrics=False) as p:
            p.record_metric("operation_count", 1)
            # 模拟一些工作
            import time
            time.sleep(0.01)
        
        # 获取统计信息
        stats = runner.profiler.get_operation_stats("test_operation")
        
        # 验证统计信息
        assert stats is not None
        assert "execution_time" in stats
        assert stats["execution_time"]["count"] == 1
        assert stats["execution_time"]["avg"] > 0
        
        # 验证自定义指标
        if "custom_metrics" in stats:
            assert "operation_count" in stats["custom_metrics"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])