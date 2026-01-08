"""
性能监控模块

提供系统性能监控、指标收集和性能基线建立功能。
"""

import time
import psutil
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import defaultdict, deque
import json
import os
from datetime import datetime, timedelta

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: float
    cpu_percent: float
    memory_usage: int  # bytes
    memory_percent: float
    disk_io_read: int
    disk_io_write: int
    network_io_sent: int
    network_io_recv: int
    execution_time: float = 0.0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceBaseline:
    """性能基线数据类"""
    cpu_baseline: float
    memory_baseline: int
    execution_time_baseline: float
    io_baseline: Dict[str, int]
    created_at: datetime
    project_characteristics: Dict[str, Any] = field(default_factory=dict)

class PerformanceCollector:
    """性能数据收集器"""
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.is_collecting = False
        self.metrics_history: deque = deque(maxlen=1000)
        self._collection_thread = None
        self._process = psutil.Process()
        
        # 获取初始IO计数
        self._initial_io = self._get_io_stats()
        self._initial_net = self._get_network_stats()
        
    def start_collection(self):
        """开始性能数据收集"""
        if self.is_collecting:
            return
            
        self.is_collecting = True
        self._collection_thread = threading.Thread(
            target=self._collect_metrics_loop, 
            daemon=True
        )
        self._collection_thread.start()
    
    def stop_collection(self):
        """停止性能数据收集"""
        self.is_collecting = False
        if self._collection_thread:
            self._collection_thread.join(timeout=2.0)
    
    def _collect_metrics_loop(self):
        """收集指标循环"""
        while self.is_collecting:
            try:
                metrics = self._collect_current_metrics()
                self.metrics_history.append(metrics)
                time.sleep(self.collection_interval)
            except Exception as e:
                # 记录错误但继续收集
                print(f"Error collecting metrics: {e}")
    
    def _collect_current_metrics(self) -> PerformanceMetrics:
        """收集当前性能指标"""
        try:
            cpu_percent = self._process.cpu_percent()
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
            
            # IO统计
            current_io = self._get_io_stats()
            io_read = current_io['read_bytes'] - self._initial_io['read_bytes']
            io_write = current_io['write_bytes'] - self._initial_io['write_bytes']
            
            # 网络统计
            current_net = self._get_network_stats()
            net_sent = current_net['bytes_sent'] - self._initial_net['bytes_sent']
            net_recv = current_net['bytes_recv'] - self._initial_net['bytes_recv']
            
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_usage=memory_info.rss,
                memory_percent=memory_percent,
                disk_io_read=io_read,
                disk_io_write=io_write,
                network_io_sent=net_sent,
                network_io_recv=net_recv
            )
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # 进程可能已结束或无权限
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_usage=0,
                memory_percent=0.0,
                disk_io_read=0,
                disk_io_write=0,
                network_io_sent=0,
                network_io_recv=0
            )
    
    def _get_io_stats(self) -> Dict[str, int]:
        """获取IO统计信息"""
        try:
            io_counters = self._process.io_counters()
            return {
                'read_bytes': io_counters.read_bytes,
                'write_bytes': io_counters.write_bytes
            }
        except (AttributeError, psutil.AccessDenied):
            return {'read_bytes': 0, 'write_bytes': 0}
    
    def _get_network_stats(self) -> Dict[str, int]:
        """获取网络统计信息"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv
            }
        except (AttributeError, psutil.AccessDenied):
            return {'bytes_sent': 0, 'bytes_recv': 0}
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取性能指标摘要"""
        if not self.metrics_history:
            return {}
        
        metrics_list = list(self.metrics_history)
        
        def get_stats(values: List[float]) -> Dict[str, float]:
            """计算统计信息"""
            if not values:
                return {'min': 0, 'max': 0, 'avg': 0}
            return {
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values)
            }
        
        cpu_values = [m.cpu_percent for m in metrics_list]
        memory_values = [m.memory_usage for m in metrics_list]
        memory_percent_values = [m.memory_percent for m in metrics_list]
        
        return {
            'collection_duration': metrics_list[-1].timestamp - metrics_list[0].timestamp,
            'data_points': len(metrics_list),
            'cpu_stats': get_stats(cpu_values),
            'memory_stats': get_stats(memory_values),
            'memory_percent_stats': get_stats(memory_percent_values),
            'peak_memory_mb': max(memory_values) / (1024 * 1024) if memory_values else 0,
            'total_disk_read_mb': metrics_list[-1].disk_io_read / (1024 * 1024) if metrics_list else 0,
            'total_disk_write_mb': metrics_list[-1].disk_io_write / (1024 * 1024) if metrics_list else 0
        }

class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.collectors: Dict[str, PerformanceCollector] = {}
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.custom_metrics: Dict[str, List[Any]] = defaultdict(list)
    
    @contextmanager
    def profile(self, operation_name: str, collect_system_metrics: bool = True):
        """性能分析上下文管理器"""
        start_time = time.time()
        
        collector = None
        if collect_system_metrics:
            collector = PerformanceCollector()
            self.collectors[operation_name] = collector
            collector.start_collection()
        
        try:
            yield self
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            self.execution_times[operation_name].append(execution_time)
            
            if collector:
                collector.stop_collection()
    
    def record_metric(self, metric_name: str, value: Any):
        """记录自定义指标"""
        self.custom_metrics[metric_name].append({
            'value': value,
            'timestamp': time.time()
        })
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """获取特定操作的性能统计"""
        stats = {}
        
        # 执行时间统计
        if operation_name in self.execution_times:
            times = self.execution_times[operation_name]
            stats['execution_time'] = {
                'count': len(times),
                'total': sum(times),
                'avg': sum(times) / len(times),
                'min': min(times),
                'max': max(times)
            }
        
        # 系统指标统计
        if operation_name in self.collectors:
            collector = self.collectors[operation_name]
            stats['system_metrics'] = collector.get_metrics_summary()
        
        return stats
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有操作的性能统计"""
        all_stats = {}
        
        for operation_name in set(self.execution_times.keys()) | set(self.collectors.keys()):
            all_stats[operation_name] = self.get_operation_stats(operation_name)
        
        # 添加自定义指标
        if self.custom_metrics:
            all_stats['custom_metrics'] = dict(self.custom_metrics)
        
        return all_stats

class BaselineManager:
    """性能基线管理器"""
    
    def __init__(self, baseline_file: str = "performance_baselines.json"):
        self.baseline_file = baseline_file
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self._load_baselines()
    
    def _load_baselines(self):
        """加载现有基线数据"""
        if os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for key, baseline_data in data.items():
                    self.baselines[key] = PerformanceBaseline(
                        cpu_baseline=baseline_data['cpu_baseline'],
                        memory_baseline=baseline_data['memory_baseline'],
                        execution_time_baseline=baseline_data['execution_time_baseline'],
                        io_baseline=baseline_data['io_baseline'],
                        created_at=datetime.fromisoformat(baseline_data['created_at']),
                        project_characteristics=baseline_data.get('project_characteristics', {})
                    )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Warning: Failed to load baselines: {e}")
    
    def _save_baselines(self):
        """保存基线数据"""
        data = {}
        for key, baseline in self.baselines.items():
            data[key] = {
                'cpu_baseline': baseline.cpu_baseline,
                'memory_baseline': baseline.memory_baseline,
                'execution_time_baseline': baseline.execution_time_baseline,
                'io_baseline': baseline.io_baseline,
                'created_at': baseline.created_at.isoformat(),
                'project_characteristics': baseline.project_characteristics
            }
        
        try:
            with open(self.baseline_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Failed to save baselines: {e}")
    
    def create_baseline(self, 
                       baseline_key: str,
                       profiler_stats: Dict[str, Any],
                       project_characteristics: Dict[str, Any] = None) -> PerformanceBaseline:
        """创建性能基线"""
        
        # 从profiler统计中提取基线指标
        system_metrics = profiler_stats.get('system_metrics', {})
        execution_stats = profiler_stats.get('execution_time', {})
        
        baseline = PerformanceBaseline(
            cpu_baseline=system_metrics.get('cpu_stats', {}).get('avg', 0.0),
            memory_baseline=int(system_metrics.get('memory_stats', {}).get('avg', 0)),
            execution_time_baseline=execution_stats.get('avg', 0.0),
            io_baseline={
                'disk_read_mb': system_metrics.get('total_disk_read_mb', 0),
                'disk_write_mb': system_metrics.get('total_disk_write_mb', 0)
            },
            created_at=datetime.now(),
            project_characteristics=project_characteristics or {}
        )
        
        self.baselines[baseline_key] = baseline
        self._save_baselines()
        return baseline
    
    def get_baseline(self, baseline_key: str) -> Optional[PerformanceBaseline]:
        """获取基线数据"""
        return self.baselines.get(baseline_key)
    
    def compare_with_baseline(self, 
                            baseline_key: str,
                            current_stats: Dict[str, Any],
                            tolerance_percent: float = 10.0) -> Dict[str, Any]:
        """与基线比较性能"""
        baseline = self.get_baseline(baseline_key)
        if not baseline:
            return {'error': f'Baseline {baseline_key} not found'}
        
        comparison = {
            'baseline_key': baseline_key,
            'baseline_created_at': baseline.created_at.isoformat(),
            'tolerance_percent': tolerance_percent,
            'results': {}
        }
        
        # 比较执行时间
        current_exec_time = current_stats.get('execution_time', {}).get('avg', 0)
        exec_time_diff_percent = ((current_exec_time - baseline.execution_time_baseline) / 
                                 baseline.execution_time_baseline * 100) if baseline.execution_time_baseline > 0 else 0
        
        comparison['results']['execution_time'] = {
            'baseline': baseline.execution_time_baseline,
            'current': current_exec_time,
            'diff_percent': exec_time_diff_percent,
            'within_tolerance': abs(exec_time_diff_percent) <= tolerance_percent
        }
        
        # 比较CPU使用
        current_cpu = current_stats.get('system_metrics', {}).get('cpu_stats', {}).get('avg', 0)
        cpu_diff_percent = ((current_cpu - baseline.cpu_baseline) / 
                           baseline.cpu_baseline * 100) if baseline.cpu_baseline > 0 else 0
        
        comparison['results']['cpu_usage'] = {
            'baseline': baseline.cpu_baseline,
            'current': current_cpu,
            'diff_percent': cpu_diff_percent,
            'within_tolerance': abs(cpu_diff_percent) <= tolerance_percent
        }
        
        # 比较内存使用
        current_memory = current_stats.get('system_metrics', {}).get('memory_stats', {}).get('avg', 0)
        memory_diff_percent = ((current_memory - baseline.memory_baseline) / 
                              baseline.memory_baseline * 100) if baseline.memory_baseline > 0 else 0
        
        comparison['results']['memory_usage'] = {
            'baseline': baseline.memory_baseline,
            'current': current_memory,
            'diff_percent': memory_diff_percent,
            'within_tolerance': abs(memory_diff_percent) <= tolerance_percent
        }
        
        # 总体评估
        all_within_tolerance = all(
            result['within_tolerance'] 
            for result in comparison['results'].values()
        )
        comparison['overall_within_tolerance'] = all_within_tolerance
        
        return comparison

class PerformanceOptimizer:
    """性能优化建议器"""
    
    def __init__(self):
        self.optimization_rules = [
            self._check_memory_usage,
            self._check_cpu_usage,
            self._check_execution_time,
            self._check_io_efficiency
        ]
    
    def analyze_performance(self, profiler_stats: Dict[str, Any]) -> Dict[str, Any]:
        """分析性能并提供优化建议"""
        analysis = {
            'performance_score': 100,
            'issues': [],
            'recommendations': [],
            'detailed_analysis': {}
        }
        
        # 应用所有优化规则
        for rule in self.optimization_rules:
            try:
                rule_result = rule(profiler_stats)
                if rule_result:
                    analysis['issues'].extend(rule_result.get('issues', []))
                    analysis['recommendations'].extend(rule_result.get('recommendations', []))
                    analysis['performance_score'] -= rule_result.get('score_penalty', 0)
                    analysis['detailed_analysis'].update(rule_result.get('details', {}))
            except Exception as e:
                print(f"Warning: Optimization rule failed: {e}")
        
        analysis['performance_score'] = max(0, analysis['performance_score'])
        analysis['performance_level'] = self._get_performance_level(analysis['performance_score'])
        
        return analysis
    
    def _check_memory_usage(self, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """检查内存使用情况"""
        system_metrics = stats.get('system_metrics', {})
        peak_memory_mb = system_metrics.get('peak_memory_mb', 0)
        avg_memory_percent = system_metrics.get('memory_percent_stats', {}).get('avg', 0)
        
        issues = []
        recommendations = []
        score_penalty = 0
        
        if peak_memory_mb > 1000:  # 1GB
            issues.append("内存使用过高")
            recommendations.append("考虑优化内存使用，如使用生成器、减少缓存大小")
            score_penalty += 15
        
        if avg_memory_percent > 80:
            issues.append("内存使用率过高")
            recommendations.append("监控内存泄漏，优化数据结构")
            score_penalty += 10
        
        return {
            'issues': issues,
            'recommendations': recommendations,
            'score_penalty': score_penalty,
            'details': {'memory_analysis': {
                'peak_memory_mb': peak_memory_mb,
                'avg_memory_percent': avg_memory_percent
            }}
        } if issues else None
    
    def _check_cpu_usage(self, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """检查CPU使用情况"""
        system_metrics = stats.get('system_metrics', {})
        avg_cpu = system_metrics.get('cpu_stats', {}).get('avg', 0)
        max_cpu = system_metrics.get('cpu_stats', {}).get('max', 0)
        
        issues = []
        recommendations = []
        score_penalty = 0
        
        if avg_cpu > 80:
            issues.append("CPU使用率过高")
            recommendations.append("考虑并行化处理、算法优化或减少计算复杂度")
            score_penalty += 20
        
        if max_cpu > 95:
            issues.append("CPU峰值使用率过高")
            recommendations.append("检查是否有CPU密集型操作可以优化")
            score_penalty += 10
        
        return {
            'issues': issues,
            'recommendations': recommendations,
            'score_penalty': score_penalty,
            'details': {'cpu_analysis': {
                'avg_cpu': avg_cpu,
                'max_cpu': max_cpu
            }}
        } if issues else None
    
    def _check_execution_time(self, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """检查执行时间"""
        exec_time = stats.get('execution_time', {}).get('avg', 0)
        
        issues = []
        recommendations = []
        score_penalty = 0
        
        if exec_time > 300:  # 5分钟
            issues.append("执行时间过长")
            recommendations.append("考虑并行处理、缓存机制或算法优化")
            score_penalty += 25
        elif exec_time > 120:  # 2分钟
            issues.append("执行时间较长")
            recommendations.append("检查是否有不必要的等待或计算")
            score_penalty += 10
        
        return {
            'issues': issues,
            'recommendations': recommendations,
            'score_penalty': score_penalty,
            'details': {'execution_analysis': {
                'avg_execution_time': exec_time
            }}
        } if issues else None
    
    def _check_io_efficiency(self, stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """检查IO效率"""
        system_metrics = stats.get('system_metrics', {})
        disk_read_mb = system_metrics.get('total_disk_read_mb', 0)
        disk_write_mb = system_metrics.get('total_disk_write_mb', 0)
        
        issues = []
        recommendations = []
        score_penalty = 0
        
        if disk_read_mb > 100:  # 100MB
            issues.append("磁盘读取量过大")
            recommendations.append("考虑缓存数据或优化文件读取策略")
            score_penalty += 10
        
        if disk_write_mb > 50:  # 50MB
            issues.append("磁盘写入量过大")
            recommendations.append("检查是否有不必要的文件写入或日志输出")
            score_penalty += 10
        
        return {
            'issues': issues,
            'recommendations': recommendations,
            'score_penalty': score_penalty,
            'details': {'io_analysis': {
                'disk_read_mb': disk_read_mb,
                'disk_write_mb': disk_write_mb
            }}
        } if issues else None
    
    def _get_performance_level(self, score: int) -> str:
        """根据分数获取性能等级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "一般"
        elif score >= 60:
            return "较差"
        else:
            return "差"

# 全局性能监控器实例
_global_profiler = None

def get_global_profiler() -> PerformanceProfiler:
    """获取全局性能分析器"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler

def profile_operation(operation_name: str, collect_system_metrics: bool = True):
    """装饰器：性能分析"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            profiler = get_global_profiler()
            with profiler.profile(operation_name, collect_system_metrics):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# 使用示例和测试
if __name__ == "__main__":
    # 基本使用示例
    profiler = PerformanceProfiler()
    baseline_manager = BaselineManager()
    optimizer = PerformanceOptimizer()
    
    # 模拟性能分析
    with profiler.profile("test_operation") as p:
        # 模拟一些工作
        time.sleep(1)
        p.record_metric("processed_files", 10)
        p.record_metric("found_issues", 5)
    
    # 获取统计
    stats = profiler.get_operation_stats("test_operation")
    print("性能统计:", json.dumps(stats, indent=2))
    
    # 创建基线
    baseline = baseline_manager.create_baseline(
        "test_baseline", 
        stats, 
        {"project_size": "medium"}
    )
    print("基线创建完成")
    
    # 性能优化分析
    optimization_result = optimizer.analyze_performance(stats)
    print("优化分析:", json.dumps(optimization_result, indent=2))