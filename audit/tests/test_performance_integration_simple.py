"""
简化的性能监控集成测试
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch

from oss_audit.core.audit_runner import AuditRunner
from oss_audit.utils.performance_monitor import (
    PerformanceProfiler, BaselineManager, PerformanceOptimizer
)


class TestSimplePerformanceIntegration:
    """简化的性能监控集成测试"""
    
    def test_audit_runner_performance_components_initialization(self):
        """测试AuditRunner性能组件初始化"""
        runner = AuditRunner()
        
        # 验证性能监控组件存在
        assert hasattr(runner, 'profiler')
        assert hasattr(runner, 'baseline_manager') 
        assert hasattr(runner, 'performance_optimizer')
        
        # 验证组件类型正确
        assert isinstance(runner.profiler, PerformanceProfiler)
        assert isinstance(runner.baseline_manager, BaselineManager)
        assert isinstance(runner.performance_optimizer, PerformanceOptimizer)
    
    def test_performance_profiler_basic_functionality(self):
        """测试性能分析器基本功能"""
        runner = AuditRunner()
        profiler = runner.profiler
        
        # 测试性能分析上下文管理器
        with profiler.profile("test_operation", collect_system_metrics=False) as p:
            time.sleep(0.01)  # 模拟一些工作
            p.record_metric("test_files", 5)
            p.record_metric("test_issues", 2)
        
        # 验证性能数据被收集
        stats = profiler.get_operation_stats("test_operation")
        assert stats is not None
        assert "execution_time" in stats
        assert stats["execution_time"]["count"] == 1
        assert stats["execution_time"]["avg"] > 0
        
        # 验证自定义指标
        all_stats = profiler.get_all_stats()
        assert "custom_metrics" in all_stats
        assert "test_files" in all_stats["custom_metrics"]
        assert "test_issues" in all_stats["custom_metrics"]
    
    def test_baseline_manager_basic_functionality(self, tmp_path):
        """测试基线管理器基本功能"""
        baseline_file = str(tmp_path / "test_baselines.json")
        baseline_manager = BaselineManager(baseline_file)
        
        # 创建测试基线
        test_stats = {
            'system_metrics': {
                'cpu_stats': {'avg': 20.0},
                'memory_stats': {'avg': 50 * 1024 * 1024},  # 50MB
                'total_disk_read_mb': 5.0,
                'total_disk_write_mb': 2.0
            },
            'execution_time': {'avg': 30.0}
        }
        
        project_characteristics = {
            "project_type": "test_project",
            "size": "small"
        }
        
        # 创建基线
        baseline = baseline_manager.create_baseline(
            "test_baseline", test_stats, project_characteristics
        )
        
        # 验证基线创建成功
        assert baseline is not None
        assert baseline.cpu_baseline == 20.0
        assert baseline.execution_time_baseline == 30.0
        assert baseline.project_characteristics["project_type"] == "test_project"
        
        # 验证基线可以被获取
        retrieved_baseline = baseline_manager.get_baseline("test_baseline")
        assert retrieved_baseline is not None
        assert retrieved_baseline.cpu_baseline == 20.0
        
        # 测试基线比较
        current_stats = {
            'system_metrics': {
                'cpu_stats': {'avg': 22.0},  # 轻微增加
                'memory_stats': {'avg': 52 * 1024 * 1024}  # 轻微增加
            },
            'execution_time': {'avg': 31.0}  # 轻微增加
        }
        
        comparison = baseline_manager.compare_with_baseline(
            "test_baseline", current_stats, tolerance_percent=10.0
        )
        
        assert comparison is not None
        assert comparison['overall_within_tolerance'] is True  # 在容忍范围内
    
    def test_performance_optimizer_basic_functionality(self):
        """测试性能优化器基本功能"""
        runner = AuditRunner()
        optimizer = runner.performance_optimizer
        
        # 测试良好性能分析
        good_stats = {
            'system_metrics': {
                'peak_memory_mb': 50.0,  # 良好
                'memory_percent_stats': {'avg': 10.0},  # 良好
                'cpu_stats': {'avg': 20.0, 'max': 40.0},  # 良好
                'total_disk_read_mb': 5.0,  # 良好
                'total_disk_write_mb': 2.0   # 良好
            },
            'execution_time': {'avg': 30.0}  # 良好
        }
        
        analysis = optimizer.analyze_performance(good_stats)
        
        assert analysis['performance_score'] == 100  # 应该是满分
        assert len(analysis['issues']) == 0
        assert len(analysis['recommendations']) == 0
        assert analysis['performance_level'] == "优秀"
        
        # 测试较差性能分析
        poor_stats = {
            'system_metrics': {
                'peak_memory_mb': 1200.0,  # 过高
                'memory_percent_stats': {'avg': 85.0},  # 过高
                'cpu_stats': {'avg': 85.0, 'max': 98.0},  # 过高
                'total_disk_read_mb': 120.0,  # 过高
                'total_disk_write_mb': 60.0   # 过高
            },
            'execution_time': {'avg': 350.0}  # 过长
        }
        
        poor_analysis = optimizer.analyze_performance(poor_stats)
        
        assert poor_analysis['performance_score'] < 100
        assert len(poor_analysis['issues']) > 0
        assert len(poor_analysis['recommendations']) > 0
        assert poor_analysis['performance_level'] in ['差', '较差', '一般']
    
    def test_analyze_performance_method_exists(self):
        """测试AuditRunner包含性能分析方法"""
        runner = AuditRunner()
        
        # 验证性能分析方法存在
        assert hasattr(runner, '_analyze_performance_and_create_baseline')
        assert callable(getattr(runner, '_analyze_performance_and_create_baseline'))
    
    @patch('oss_audit.utils.performance_monitor.psutil.Process')
    def test_performance_collector_basic_functionality(self, mock_process):
        """测试性能收集器基本功能"""
        from oss_audit.utils.performance_monitor import PerformanceCollector
        
        # Mock psutil.Process
        mock_process_instance = Mock()
        mock_process_instance.cpu_percent.return_value = 25.0
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_process_instance.memory_percent.return_value = 15.0
        mock_process_instance.io_counters.return_value.read_bytes = 1024
        mock_process_instance.io_counters.return_value.write_bytes = 512
        mock_process.return_value = mock_process_instance
        
        with patch('psutil.net_io_counters') as mock_net:
            mock_net.return_value.bytes_sent = 2048
            mock_net.return_value.bytes_recv = 1024
            
            collector = PerformanceCollector(collection_interval=0.1)
            
            # 测试单次指标收集
            metrics = collector._collect_current_metrics()
            
            assert metrics.cpu_percent == 25.0
            assert metrics.memory_usage == 100 * 1024 * 1024
            assert metrics.memory_percent == 15.0
            
            # 测试指标摘要
            collector.metrics_history.append(metrics)
            summary = collector.get_metrics_summary()
            
            assert summary['data_points'] == 1
            assert summary['cpu_stats']['avg'] == 25.0
            assert summary['peak_memory_mb'] == 100.0
    
    def test_global_profiler_functionality(self):
        """测试全局性能分析器功能"""
        from oss_audit.utils.performance_monitor import get_global_profiler, profile_operation
        
        # 测试全局分析器
        profiler1 = get_global_profiler()
        profiler2 = get_global_profiler()
        
        # 应该返回同一个实例
        assert profiler1 is profiler2
        
        # 测试装饰器
        @profile_operation("decorated_test", collect_system_metrics=False)
        def test_function():
            time.sleep(0.01)
            return "test_result"
        
        result = test_function()
        assert result == "test_result"
        
        # 验证性能数据被记录
        global_profiler = get_global_profiler()
        assert "decorated_test" in global_profiler.execution_times
        execution_time = global_profiler.execution_times["decorated_test"][-1]
        assert execution_time > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])