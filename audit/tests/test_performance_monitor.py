"""
测试性能监控模块
"""

import pytest
import time
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from oss_audit.utils.performance_monitor import (
    PerformanceCollector,
    PerformanceProfiler,
    BaselineManager,
    PerformanceOptimizer,
    PerformanceMetrics,
    PerformanceBaseline,
    get_global_profiler,
    profile_operation
)


class TestPerformanceCollector:
    """测试性能收集器"""
    
    @pytest.fixture
    def collector(self):
        return PerformanceCollector(collection_interval=0.1)
    
    def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector.collection_interval == 0.1
        assert not collector.is_collecting
        assert len(collector.metrics_history) == 0
    
    @patch('psutil.Process')
    def test_collect_current_metrics(self, mock_process, collector):
        """测试当前指标收集"""
        # Mock psutil.Process的方法
        mock_process_instance = Mock()
        mock_process_instance.cpu_percent.return_value = 25.5
        mock_process_instance.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
        mock_process_instance.memory_percent.return_value = 15.5
        mock_process_instance.io_counters.return_value.read_bytes = 1024 * 1024
        mock_process_instance.io_counters.return_value.write_bytes = 512 * 1024
        mock_process.return_value = mock_process_instance
        
        # 重新创建collector使用mock
        collector._process = mock_process_instance
        collector._initial_io = {'read_bytes': 0, 'write_bytes': 0}
        collector._initial_net = {'bytes_sent': 0, 'bytes_recv': 0}
        
        with patch('psutil.net_io_counters') as mock_net:
            mock_net.return_value.bytes_sent = 2048
            mock_net.return_value.bytes_recv = 4096
            
            metrics = collector._collect_current_metrics()
            
            assert metrics.cpu_percent == 25.5
            assert metrics.memory_usage == 1024 * 1024 * 100
            assert metrics.memory_percent == 15.5
            assert metrics.disk_io_read == 1024 * 1024
            assert metrics.disk_io_write == 512 * 1024
    
    def test_start_stop_collection(self, collector):
        """测试启停收集"""
        assert not collector.is_collecting
        
        collector.start_collection()
        assert collector.is_collecting
        assert collector._collection_thread is not None
        
        # 让收集线程运行一小段时间
        time.sleep(0.2)
        
        collector.stop_collection()
        assert not collector.is_collecting
    
    @patch('psutil.Process')  
    def test_metrics_summary(self, mock_process, collector):
        """测试指标摘要"""
        # 添加一些测试数据
        test_metrics = [
            PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=20.0,
                memory_usage=100 * 1024 * 1024,
                memory_percent=10.0,
                disk_io_read=1024,
                disk_io_write=512,
                network_io_sent=2048,
                network_io_recv=1024
            ),
            PerformanceMetrics(
                timestamp=time.time() + 1,
                cpu_percent=30.0,
                memory_usage=150 * 1024 * 1024,
                memory_percent=15.0,
                disk_io_read=2048,
                disk_io_write=1024,
                network_io_sent=4096,
                network_io_recv=2048
            )
        ]
        
        collector.metrics_history.extend(test_metrics)
        
        summary = collector.get_metrics_summary()
        
        assert summary['data_points'] == 2
        assert summary['cpu_stats']['min'] == 20.0
        assert summary['cpu_stats']['max'] == 30.0
        assert summary['cpu_stats']['avg'] == 25.0
        assert summary['peak_memory_mb'] == 150.0


class TestPerformanceProfiler:
    """测试性能分析器"""
    
    @pytest.fixture
    def profiler(self):
        return PerformanceProfiler()
    
    def test_profiler_initialization(self, profiler):
        """测试分析器初始化"""
        assert len(profiler.collectors) == 0
        assert len(profiler.execution_times) == 0
        assert len(profiler.custom_metrics) == 0
    
    def test_profile_context_manager(self, profiler):
        """测试性能分析上下文管理器"""
        start_time = time.time()
        
        with profiler.profile("test_operation", collect_system_metrics=False) as p:
            time.sleep(0.1)  # 模拟工作
            p.record_metric("test_metric", 42)
        
        end_time = time.time()
        
        # 验证执行时间记录
        assert "test_operation" in profiler.execution_times
        execution_time = profiler.execution_times["test_operation"][0]
        assert 0.09 <= execution_time <= 0.2  # 允许一些误差
        
        # 验证自定义指标
        assert "test_metric" in profiler.custom_metrics
        assert profiler.custom_metrics["test_metric"][0]["value"] == 42
    
    def test_get_operation_stats(self, profiler):
        """测试获取操作统计"""
        # 添加一些测试数据
        profiler.execution_times["test_op"] = [1.0, 1.5, 2.0]
        
        stats = profiler.get_operation_stats("test_op")
        
        assert stats["execution_time"]["count"] == 3
        assert stats["execution_time"]["avg"] == 1.5
        assert stats["execution_time"]["min"] == 1.0
        assert stats["execution_time"]["max"] == 2.0
    
    def test_record_metric(self, profiler):
        """测试记录自定义指标"""
        profiler.record_metric("files_processed", 10)
        profiler.record_metric("files_processed", 20)
        
        assert len(profiler.custom_metrics["files_processed"]) == 2
        assert profiler.custom_metrics["files_processed"][0]["value"] == 10
        assert profiler.custom_metrics["files_processed"][1]["value"] == 20


class TestBaselineManager:
    """测试基线管理器"""
    
    @pytest.fixture
    def temp_baseline_file(self):
        """临时基线文件"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.close()
        yield temp_file.name
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    @pytest.fixture
    def baseline_manager(self, temp_baseline_file):
        return BaselineManager(temp_baseline_file)
    
    def test_baseline_manager_initialization(self, baseline_manager):
        """测试基线管理器初始化"""
        assert len(baseline_manager.baselines) == 0
        assert baseline_manager.baseline_file is not None
    
    def test_create_baseline(self, baseline_manager):
        """测试创建基线"""
        test_stats = {
            'system_metrics': {
                'cpu_stats': {'avg': 25.0},
                'memory_stats': {'avg': 100 * 1024 * 1024},
                'total_disk_read_mb': 10.0,
                'total_disk_write_mb': 5.0
            },
            'execution_time': {'avg': 30.5}
        }
        
        baseline = baseline_manager.create_baseline(
            "test_baseline",
            test_stats,
            {"project_size": "small"}
        )
        
        assert baseline.cpu_baseline == 25.0
        assert baseline.memory_baseline == 100 * 1024 * 1024
        assert baseline.execution_time_baseline == 30.5
        assert baseline.project_characteristics["project_size"] == "small"
        
        # 验证基线已保存
        assert "test_baseline" in baseline_manager.baselines
    
    def test_compare_with_baseline(self, baseline_manager):
        """测试基线比较"""
        # 创建基线
        baseline_stats = {
            'system_metrics': {
                'cpu_stats': {'avg': 20.0},
                'memory_stats': {'avg': 100 * 1024 * 1024}
            },
            'execution_time': {'avg': 30.0}
        }
        
        baseline_manager.create_baseline("test_baseline", baseline_stats)
        
        # 当前统计
        current_stats = {
            'system_metrics': {
                'cpu_stats': {'avg': 22.0},  # 10% 增加
                'memory_stats': {'avg': 105 * 1024 * 1024}  # 5% 增加
            },
            'execution_time': {'avg': 33.0}  # 10% 增加
        }
        
        comparison = baseline_manager.compare_with_baseline(
            "test_baseline", current_stats, tolerance_percent=10.0
        )
        
        assert comparison['baseline_key'] == "test_baseline"
        assert comparison['results']['execution_time']['within_tolerance'] is True
        assert comparison['results']['cpu_usage']['within_tolerance'] is True
        assert comparison['results']['memory_usage']['within_tolerance'] is True
        assert comparison['overall_within_tolerance'] is True
    
    def test_baseline_persistence(self, temp_baseline_file):
        """测试基线持久化"""
        # 创建第一个管理器并添加基线
        manager1 = BaselineManager(temp_baseline_file)
        test_stats = {
            'system_metrics': {'cpu_stats': {'avg': 25.0}},
            'execution_time': {'avg': 30.0}
        }
        manager1.create_baseline("persistent_baseline", test_stats)
        
        # 创建第二个管理器，应该能加载基线
        manager2 = BaselineManager(temp_baseline_file)
        assert "persistent_baseline" in manager2.baselines
        
        baseline = manager2.get_baseline("persistent_baseline")
        assert baseline.cpu_baseline == 25.0


class TestPerformanceOptimizer:
    """测试性能优化器"""
    
    @pytest.fixture
    def optimizer(self):
        return PerformanceOptimizer()
    
    def test_optimizer_initialization(self, optimizer):
        """测试优化器初始化"""
        assert len(optimizer.optimization_rules) > 0
    
    def test_analyze_good_performance(self, optimizer):
        """测试分析良好性能"""
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
        
        assert analysis['performance_score'] == 100
        assert len(analysis['issues']) == 0
        assert len(analysis['recommendations']) == 0
        assert analysis['performance_level'] == "优秀"
    
    def test_analyze_poor_performance(self, optimizer):
        """测试分析较差性能"""
        poor_stats = {
            'system_metrics': {
                'peak_memory_mb': 1500.0,  # 过高
                'memory_percent_stats': {'avg': 85.0},  # 过高
                'cpu_stats': {'avg': 85.0, 'max': 98.0},  # 过高
                'total_disk_read_mb': 150.0,  # 过高
                'total_disk_write_mb': 80.0   # 过高
            },
            'execution_time': {'avg': 350.0}  # 过长
        }
        
        analysis = optimizer.analyze_performance(poor_stats)
        
        assert analysis['performance_score'] < 100
        assert len(analysis['issues']) > 0
        assert len(analysis['recommendations']) > 0
        assert "内存使用过高" in analysis['issues']
        assert "CPU使用率过高" in analysis['issues']
        assert "执行时间过长" in analysis['issues']
    
    def test_memory_usage_check(self, optimizer):
        """测试内存使用检查"""
        high_memory_stats = {
            'system_metrics': {
                'peak_memory_mb': 1200.0,
                'memory_percent_stats': {'avg': 85.0}
            }
        }
        
        result = optimizer._check_memory_usage(high_memory_stats)
        
        assert result is not None
        assert "内存使用过高" in result['issues']
        assert "内存使用率过高" in result['issues']
        assert result['score_penalty'] == 25  # 15 + 10
    
    def test_cpu_usage_check(self, optimizer):
        """测试CPU使用检查"""
        high_cpu_stats = {
            'system_metrics': {
                'cpu_stats': {'avg': 85.0, 'max': 98.0}
            }
        }
        
        result = optimizer._check_cpu_usage(high_cpu_stats)
        
        assert result is not None
        assert "CPU使用率过高" in result['issues']
        assert "CPU峰值使用率过高" in result['issues']
        assert result['score_penalty'] == 30  # 20 + 10
    
    def test_execution_time_check(self, optimizer):
        """测试执行时间检查"""
        slow_execution_stats = {
            'execution_time': {'avg': 350.0}  # 超过5分钟
        }
        
        result = optimizer._check_execution_time(slow_execution_stats)
        
        assert result is not None
        assert "执行时间过长" in result['issues']
        assert result['score_penalty'] == 25


class TestGlobalProfiler:
    """测试全局性能分析器"""
    
    def test_get_global_profiler(self):
        """测试获取全局分析器"""
        profiler1 = get_global_profiler()
        profiler2 = get_global_profiler()
        
        # 应该返回同一个实例
        assert profiler1 is profiler2
    
    def test_profile_operation_decorator(self):
        """测试性能分析装饰器"""
        @profile_operation("decorated_operation", collect_system_metrics=False)
        def test_function():
            time.sleep(0.1)
            return "test_result"
        
        result = test_function()
        
        assert result == "test_result"
        
        # 验证性能数据被记录
        profiler = get_global_profiler()
        assert "decorated_operation" in profiler.execution_times
        execution_time = profiler.execution_times["decorated_operation"][-1]
        assert 0.05 <= execution_time <= 0.2


@pytest.mark.integration
class TestPerformanceIntegration:
    """集成测试"""
    
    def test_complete_performance_workflow(self, tmp_path):
        """测试完整性能监控工作流"""
        baseline_file = str(tmp_path / "test_baselines.json")
        
        # 1. 创建性能分析器和基线管理器
        profiler = PerformanceProfiler()
        baseline_manager = BaselineManager(baseline_file)
        optimizer = PerformanceOptimizer()
        
        # 2. 执行性能分析
        with profiler.profile("integration_test", collect_system_metrics=False) as p:
            # 模拟一些工作
            for i in range(10):
                time.sleep(0.01)
                p.record_metric("processed_items", i)
        
        # 3. 获取统计信息
        stats = profiler.get_operation_stats("integration_test")
        assert "execution_time" in stats
        
        # 4. 创建基线
        project_characteristics = {
            "language": "python",
            "project_size": "small",
            "complexity": "low"
        }
        
        baseline = baseline_manager.create_baseline(
            "integration_baseline",
            stats,
            project_characteristics
        )
        
        assert baseline is not None
        assert baseline.project_characteristics["language"] == "python"
        
        # 5. 性能优化分析
        optimization_analysis = optimizer.analyze_performance(stats)
        assert "performance_score" in optimization_analysis
        assert "performance_level" in optimization_analysis
        
        # 6. 验证基线比较
        comparison = baseline_manager.compare_with_baseline(
            "integration_baseline",
            stats,
            tolerance_percent=10.0
        )
        
        assert comparison["overall_within_tolerance"] is True
        
        # 7. 验证数据持久化
        new_manager = BaselineManager(baseline_file)
        loaded_baseline = new_manager.get_baseline("integration_baseline")
        
        assert loaded_baseline is not None
        assert loaded_baseline.project_characteristics["language"] == "python"


if __name__ == "__main__":
    # 运行特定测试
    pytest.main([__file__ + "::TestPerformanceCollector::test_collector_initialization", "-v"])