#!/usr/bin/env python3
"""
一致性检查工具 - 验证分析结果的幂等性
通过多次执行相同分析并比较结果来验证系统的确定性
"""

import os
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyResult:
    """一致性检查结果"""
    test_name: str
    project_path: str
    iterations: int
    consistent: bool
    consistency_score: float  # 0.0-1.0
    differences: List[Dict[str, Any]]
    execution_times: List[float]
    report_hashes: List[str]
    summary: str


@dataclass
class AnalysisRun:
    """单次分析运行结果"""
    run_id: int
    timestamp: datetime
    execution_time: float
    report_path: str
    report_hash: str
    summary_data: Dict[str, Any]


class ConsistencyChecker:
    """一致性检查器"""
    
    def __init__(self, oss_audit_path: Optional[str] = None):
        """
        初始化一致性检查器
        
        Args:
            oss_audit_path: oss-audit可执行文件路径，默认使用当前目录的main.py
        """
        self.oss_audit_path = oss_audit_path or "python main.py"
        self.temp_dir = Path(tempfile.mkdtemp(prefix="oss_audit_consistency_"))
        self.results = []
        
    def __del__(self):
        """清理临时目录"""
        try:
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"无法计算文件哈希 {file_path}: {e}")
            return ""
    
    def _extract_key_metrics(self, report_path: str) -> Dict[str, Any]:
        """从报告中提取关键指标"""
        try:
            # 尝试读取JSON报告
            json_report_path = report_path.replace('.html', '.json')
            if os.path.exists(json_report_path):
                with open(json_report_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                return {
                    'overall_score': data.get('summary', {}).get('overall_score', 0),
                    'dimension_scores': data.get('summary', {}).get('dimension_scores', {}),
                    'total_issues': data.get('summary', {}).get('total_issues', 0),
                    'project_info': data.get('project_info', {}),
                    'intelligent_recommendations': data.get('summary', {}).get('intelligent_recommendations', {})
                }
        except Exception as e:
            logger.warning(f"无法提取报告指标 {report_path}: {e}")
        
        return {}
    
    def _run_single_analysis(self, project_path: str, run_id: int) -> AnalysisRun:
        """执行单次分析"""
        start_time = datetime.now()
        
        # 创建运行特定的输出目录
        output_dir = self.temp_dir / f"run_{run_id}"
        output_dir.mkdir(exist_ok=True)
        
        try:
            # 构建命令
            cmd = f"{self.oss_audit_path} \"{project_path}\" \"{output_dir}\""
            
            # 执行分析
            logger.info(f"执行第 {run_id} 次分析: {cmd}")
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                cwd=os.getcwd(),
                timeout=600  # 10分钟超时
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if result.returncode != 0:
                logger.error(f"分析失败 (run {run_id}): {result.stderr}")
                raise RuntimeError(f"分析执行失败: {result.stderr}")
            
            # 查找生成的报告文件
            html_files = list(output_dir.glob("**/*.html"))
            main_report = None
            
            for html_file in html_files:
                if "audit_report.html" in html_file.name:
                    main_report = str(html_file)
                    break
            
            if not main_report:
                raise RuntimeError(f"未找到主报告文件在 {output_dir}")
            
            # 计算报告哈希
            report_hash = self._calculate_file_hash(main_report)
            
            # 提取关键指标
            summary_data = self._extract_key_metrics(main_report)
            
            return AnalysisRun(
                run_id=run_id,
                timestamp=start_time,
                execution_time=execution_time,
                report_path=main_report,
                report_hash=report_hash,
                summary_data=summary_data
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"分析超时 (run {run_id})")
            raise RuntimeError("分析执行超时")
        except Exception as e:
            logger.error(f"分析执行异常 (run {run_id}): {e}")
            raise
    
    def _compare_runs(self, runs: List[AnalysisRun]) -> Tuple[bool, float, List[Dict]]:
        """比较多次运行结果"""
        if len(runs) < 2:
            return True, 1.0, []
        
        differences = []
        hash_matches = 0
        score_differences = []
        
        # 检查报告哈希一致性
        base_hash = runs[0].report_hash
        for i, run in enumerate(runs[1:], 1):
            if run.report_hash == base_hash:
                hash_matches += 1
            else:
                differences.append({
                    'type': 'report_hash_mismatch',
                    'run_ids': [0, i],
                    'values': [base_hash[:16], run.report_hash[:16]]
                })
        
        # 检查关键指标一致性
        base_data = runs[0].summary_data
        for i, run in enumerate(runs[1:], 1):
            current_data = run.summary_data
            
            # 比较总分
            base_score = base_data.get('overall_score', 0)
            current_score = current_data.get('overall_score', 0)
            
            if abs(base_score - current_score) > 0.01:  # 允许0.01的浮点误差
                score_differences.append(abs(base_score - current_score))
                differences.append({
                    'type': 'overall_score_difference',
                    'run_ids': [0, i],
                    'values': [base_score, current_score],
                    'difference': abs(base_score - current_score)
                })
            
            # 比较维度分数
            base_dimensions = base_data.get('dimension_scores', {})
            current_dimensions = current_data.get('dimension_scores', {})
            
            for dimension, base_dim_score in base_dimensions.items():
                current_dim_score = current_dimensions.get(dimension, 0)
                if abs(base_dim_score - current_dim_score) > 0.01:
                    differences.append({
                        'type': 'dimension_score_difference',
                        'dimension': dimension,
                        'run_ids': [0, i],
                        'values': [base_dim_score, current_dim_score],
                        'difference': abs(base_dim_score - current_dim_score)
                    })
        
        # 计算一致性分数
        total_comparisons = len(runs) - 1
        hash_consistency = hash_matches / total_comparisons if total_comparisons > 0 else 1.0
        
        # 分数一致性（基于最大差异）
        max_score_diff = max(score_differences) if score_differences else 0
        score_consistency = max(0, 1.0 - (max_score_diff / 100.0))  # 假设100分为满分
        
        # 综合一致性分数
        consistency_score = (hash_consistency * 0.6 + score_consistency * 0.4)
        
        # 判断是否一致（阈值可调整）
        is_consistent = consistency_score >= 0.95 and len(differences) == 0
        
        return is_consistent, consistency_score, differences
    
    def check_project_consistency(self, project_path: str, iterations: int = 3,
                                 test_name: Optional[str] = None) -> ConsistencyResult:
        """
        检查项目分析的一致性
        
        Args:
            project_path: 项目路径
            iterations: 执行次数
            test_name: 测试名称
            
        Returns:
            一致性检查结果
        """
        if not test_name:
            test_name = f"consistency_test_{Path(project_path).name}"
        
        logger.info(f"开始一致性检查: {test_name} (项目: {project_path}, 迭代: {iterations}次)")
        
        runs = []
        
        # 执行多次分析
        for i in range(iterations):
            try:
                run = self._run_single_analysis(project_path, i)
                runs.append(run)
                logger.info(f"完成第 {i+1}/{iterations} 次分析，用时 {run.execution_time:.2f}秒")
            except Exception as e:
                logger.error(f"第 {i+1} 次分析失败: {e}")
                # 继续执行剩余分析
        
        if len(runs) == 0:
            return ConsistencyResult(
                test_name=test_name,
                project_path=project_path,
                iterations=iterations,
                consistent=False,
                consistency_score=0.0,
                differences=[{'type': 'execution_failure', 'message': '所有分析都失败了'}],
                execution_times=[],
                report_hashes=[],
                summary="所有分析执行失败"
            )
        
        # 比较结果
        is_consistent, consistency_score, differences = self._compare_runs(runs)
        
        # 构建结果
        result = ConsistencyResult(
            test_name=test_name,
            project_path=project_path,
            iterations=len(runs),
            consistent=is_consistent,
            consistency_score=consistency_score,
            differences=differences,
            execution_times=[run.execution_time for run in runs],
            report_hashes=[run.report_hash for run in runs],
            summary=self._generate_summary(is_consistent, consistency_score, differences, runs)
        )
        
        self.results.append(result)
        logger.info(f"一致性检查完成: {test_name} - 一致性: {is_consistent} (分数: {consistency_score:.3f})")
        
        return result
    
    def _generate_summary(self, is_consistent: bool, consistency_score: float,
                         differences: List[Dict], runs: List[AnalysisRun]) -> str:
        """生成总结信息"""
        if is_consistent:
            return f"✅ 分析结果完全一致 (一致性分数: {consistency_score:.3f})"
        
        summary_parts = [
            f"⚠️ 发现 {len(differences)} 个差异 (一致性分数: {consistency_score:.3f})"
        ]
        
        # 统计差异类型
        diff_types = {}
        for diff in differences:
            diff_type = diff['type']
            diff_types[diff_type] = diff_types.get(diff_type, 0) + 1
        
        for diff_type, count in diff_types.items():
            summary_parts.append(f"  - {diff_type}: {count} 次")
        
        # 性能统计
        if runs:
            avg_time = sum(run.execution_time for run in runs) / len(runs)
            summary_parts.append(f"  - 平均执行时间: {avg_time:.2f}秒")
        
        return "\n".join(summary_parts)
    
    def batch_check(self, projects: List[str], iterations: int = 3) -> List[ConsistencyResult]:
        """
        批量检查多个项目的一致性
        
        Args:
            projects: 项目路径列表
            iterations: 每个项目的执行次数
            
        Returns:
            所有项目的一致性检查结果
        """
        results = []
        
        for i, project_path in enumerate(projects):
            logger.info(f"检查项目 {i+1}/{len(projects)}: {project_path}")
            try:
                result = self.check_project_consistency(project_path, iterations)
                results.append(result)
            except Exception as e:
                logger.error(f"项目 {project_path} 一致性检查失败: {e}")
        
        return results
    
    def generate_report(self, output_path: str) -> str:
        """
        生成一致性检查报告
        
        Args:
            output_path: 报告输出路径
            
        Returns:
            生成的报告文件路径
        """
        if not self.results:
            logger.warning("没有一致性检查结果可用于生成报告")
            return ""
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.results),
            'consistent_tests': sum(1 for r in self.results if r.consistent),
            'average_consistency_score': sum(r.consistency_score for r in self.results) / len(self.results),
            'results': [asdict(result) for result in self.results]
        }
        
        # 生成JSON报告
        json_path = output_path.replace('.html', '.json') if output_path.endswith('.html') else f"{output_path}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 生成HTML报告
        html_content = self._generate_html_report(report_data)
        html_path = output_path if output_path.endswith('.html') else f"{output_path}.html"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"一致性检查报告已生成: {html_path}")
        return html_path
    
    def _generate_html_report(self, report_data: Dict) -> str:
        """生成HTML格式的报告"""
        consistent_count = report_data['consistent_tests']
        total_count = report_data['total_tests']
        consistency_rate = (consistent_count / total_count * 100) if total_count > 0 else 0
        
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>OSS Audit 一致性检查报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
                .stat-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .result-item {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
                .consistent {{ border-left: 4px solid #28a745; }}
                .inconsistent {{ border-left: 4px solid #dc3545; }}
                .differences {{ background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>OSS Audit 一致性检查报告</h1>
                    <p>生成时间: {report_data['timestamp']}</p>
                </div>
                
                <div class="summary">
                    <div class="stat-card">
                        <div class="stat-value">{total_count}</div>
                        <div>总测试数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{consistent_count}</div>
                        <div>一致测试数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{consistency_rate:.1f}%</div>
                        <div>一致性率</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{report_data['average_consistency_score']:.3f}</div>
                        <div>平均一致性分数</div>
                    </div>
                </div>
                
                <h2>详细结果</h2>
        """
        
        for result in report_data['results']:
            status_class = "consistent" if result['consistent'] else "inconsistent"
            status_icon = "✅" if result['consistent'] else "❌"
            
            html += f"""
                <div class="result-item {status_class}">
                    <h3>{status_icon} {result['test_name']}</h3>
                    <p><strong>项目:</strong> {result['project_path']}</p>
                    <p><strong>迭代次数:</strong> {result['iterations']}</p>
                    <p><strong>一致性分数:</strong> {result['consistency_score']:.3f}</p>
                    <p><strong>执行时间:</strong> {', '.join([f'{t:.2f}s' for t in result['execution_times']])}</p>
                    <p><strong>总结:</strong> {result['summary']}</p>
            """
            
            if result['differences']:
                html += '<div class="differences"><h4>发现的差异:</h4><ul>'
                for diff in result['differences']:
                    html += f"<li>{diff.get('type', 'unknown')}: {diff}</li>"
                html += '</ul></div>'
            
            html += '</div>'
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html


if __name__ == "__main__":
    # 测试一致性检查器
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python consistency_checker.py <项目路径> [迭代次数]")
        sys.exit(1)
    
    project_path = sys.argv[1]
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    checker = ConsistencyChecker()
    result = checker.check_project_consistency(project_path, iterations)
    
    print(f"一致性检查结果: {result.summary}")
    
    # 生成报告
    report_path = "consistency_report.html"
    checker.generate_report(report_path)
    print(f"详细报告已生成: {report_path}")