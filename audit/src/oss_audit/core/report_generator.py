#!/usr/bin/env python3
"""
Report Generator - 报告生成器
负责生成各种格式的审计报告（HTML、JSON、PDF等）
负责生成多格式审计报告，支持智能分析结果展示
"""

import os
import json
import time
import pathlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

from .project_detector import ProjectInfo
from .tool_executor import ToolResult
from ..utils.ai_analyzer import AIAnalyzer
from .report_generators.dimension_formatter import DimensionFormatter
from .report_generators.dimension_html_generator import DimensionHtmlGenerator

logger = logging.getLogger(__name__)


@dataclass
class DimensionReport:
    """维度报告"""
    dimension_id: int
    dimension_name: str
    score: float
    status: str  # PASS, WARN, FAIL
    tools_used: List[str]
    issues_count: int
    details: Dict[str, Any]
    recommendations: List[str]
    ai_analysis: Optional[Dict[str, Any]] = None


@dataclass
class AuditReport:
    """审计报告数据模型"""
    project_info: ProjectInfo
    timestamp: str
    dimensions: List[DimensionReport]
    tool_results: Dict[str, ToolResult]
    overall_score: float
    overall_status: str
    summary: Dict[str, Any]
    execution_stats: Dict[str, Any]
    ai_analysis: Optional[Dict[str, Any]] = None


class ReportGenerator:
    """报告生成器 - 负责生成各种格式的审计报告"""
    
    def __init__(self):
        """初始化报告生成器"""
        # 初始化AI分析器
        try:
            from ..utils.ai_analyzer import AIAnalyzer
            self.ai_analyzer = AIAnalyzer()
        except Exception as e:
            logger.debug(f"AI分析器初始化失败: {e}")
        
        # 初始化维度格式化器
        self.dimension_formatter = DimensionFormatter()
        self.dimension_html_generator = DimensionHtmlGenerator()
        
        if not hasattr(self, 'ai_analyzer') or self.ai_analyzer is None:
            self.ai_analyzer = None
        
        self.dimension_names = [
            "代码结构与可维护性",
            "测试覆盖与质量保障", 
            "构建与工程可重复性",
            "依赖与许可证合规",
            "安全性与敏感信息防护",
            "CI/CD 自动化保障",
            "使用文档与复现性",
            "接口与平台兼容性",
            "协作流程与代码规范",
            "开源协议与法律合规",
            "社区治理与贡献机制",
            "舆情与风险监控",
            "数据与算法合规审核",
            "IP（知识产权）"
        ]
    
    def generate_audit_report(self, project_info: ProjectInfo,
                            tool_results: Dict[str, ToolResult],
                            execution_stats: Dict[str, Any],
                            output_dir: str) -> str:
        """
        生成完整的审计报告
        
        Args:
            project_info: 项目信息
            tool_results: 工具执行结果
            execution_stats: 执行统计信息
            output_dir: 输出目录
            
        Returns:
            报告文件路径
        """
        logger.info(f"开始生成审计报告，输出目录: {output_dir}")
        
        # 创建输出目录
        output_path = pathlib.Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 构建审计报告数据
        audit_report = self._build_audit_report(
            project_info, tool_results, execution_stats)
        
        # 生成不同格式的报告
        reports_generated = []
        
        # 1. 生成JSON报告
        json_report_path = self._generate_json_report(audit_report, output_path)
        reports_generated.append(json_report_path)
        
        # 2. 生成HTML报告
        html_report_path = self._generate_html_report(audit_report, output_path)
        reports_generated.append(html_report_path)
        
        # 3. 生成维度详细报告
        dimension_reports = self._generate_dimension_reports(audit_report, output_path)
        reports_generated.extend(dimension_reports)
        
        # 4. 生成工具结果报告
        tool_reports = self._generate_tool_reports(audit_report, output_path)
        reports_generated.extend(tool_reports)
        
        logger.info(f"报告生成完成，共生成 {len(reports_generated)} 个文件")
        return html_report_path  # 返回主报告路径
    
    def _build_audit_report(self, project_info: ProjectInfo,
                          tool_results: Dict[str, ToolResult],
                          execution_stats: Dict[str, Any]) -> AuditReport:
        """构建审计报告数据"""
        
        # 分析维度得分
        dimensions = self._analyze_dimensions(project_info, tool_results)
        
        # 计算总体得分
        overall_score = sum(d.score for d in dimensions) / len(dimensions) if dimensions else 0
        
        # 确定总体状态
        overall_status = self._calculate_overall_status(overall_score, dimensions)
        
        # 计算准确的执行统计 - 只统计实际执行的工具
        # 过滤出实际执行的工具（排除 not_available 状态的工具）
        executed_tools = {
            name: result for name, result in tool_results.items() 
            if not (hasattr(result, 'status') and result.status == 'not_available')
        }
        
        total_tools = len(executed_tools)
        successful_tools = len([r for r in executed_tools.values() if r.success])
        failed_tools = len([r for r in executed_tools.values() if not r.success])
        
        # 安全计算总执行时间，处理可能的异常值
        total_execution_time = 0.0
        for result in executed_tools.values():
            if hasattr(result, 'execution_time') and result.execution_time is not None:
                try:
                    time_value = float(result.execution_time)
                    if time_value >= 0:  # 确保时间值合理
                        total_execution_time += time_value
                except (ValueError, TypeError):
                    continue
        
        # 更新执行统计，确保数据准确性
        corrected_execution_stats = {
            'total_tools': total_tools,
            'successful_tools': successful_tools,
            'failed_tools': failed_tools,
            'total_time': total_execution_time
        }
        
        # 构建摘要信息
        summary = {
            'total_dimensions': len(dimensions),
            'passed_dimensions': len([d for d in dimensions if d.status == 'PASS']),
            'warned_dimensions': len([d for d in dimensions if d.status == 'WARN']),
            'failed_dimensions': len([d for d in dimensions if d.status == 'FAIL']),
            'primary_language': project_info.get_primary_language(),
            'project_size': project_info.size_metrics.get_size_category(),
            'code_lines': project_info.size_metrics.code_lines,
            'structure_type': project_info.structure_type.value if hasattr(project_info.structure_type, 'value') else str(project_info.structure_type),
            'project_type': project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type)
        }
        
        # 添加项目总体AI分析
        overall_ai_analysis = None
        try:
            overall_data = {
                'project_info': {
                    'name': project_info.name,
                    'languages': project_info.languages,
                    'size': project_info.size_metrics.get_size_category(),
                    'code_lines': project_info.size_metrics.code_lines,
                    'project_type': project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type),
                    'structure_type': project_info.structure_type.value if hasattr(project_info.structure_type, 'value') else str(project_info.structure_type),
                    'build_tools': project_info.build_tools,
                    'dependencies': project_info.dependencies,
                    'test_files': project_info.size_metrics.test_files,
                    'confidence': project_info.confidence
                },
                'overall_score': overall_score,
                'overall_status': overall_status,
                'summary': summary,
                'execution_stats': execution_stats,
                'dimensions_summary': [
                    {
                        'id': d.dimension_id,
                        'name': d.dimension_name,
                        'score': d.score,
                        'status': d.status,
                        'issues_count': d.issues_count,
                        'tools_used': d.tools_used,
                        'recommendations': d.recommendations
                    } for d in dimensions
                ],
                'tool_results_summary': {
                    name: {
                        'success': result.success,
                        'execution_time': result.execution_time,
                        'return_code': result.return_code
                    }
                    for name, result in tool_results.items()
                }
            }
            overall_ai_analysis = self.ai_analyzer.analyze_overall_project(overall_data)
        except Exception as e:
            logger.debug(f"项目总体AI分析失败: {e}")
        
        return AuditReport(
            project_info=project_info,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            dimensions=dimensions,
            tool_results=tool_results,
            overall_score=overall_score,
            overall_status=overall_status,
            summary=summary,
            execution_stats=corrected_execution_stats,  # 使用修正的执行统计
            ai_analysis=overall_ai_analysis
        )
    
    def _analyze_dimensions(self, project_info: ProjectInfo,
                          tool_results: Dict[str, ToolResult]) -> List[DimensionReport]:
        """分析各个维度的得分"""
        dimensions = []
        
        # 初始化智能工具选择器
        from .smart_tool_selector import create_smart_tool_selector
        from .tool_registry import Tool
        smart_selector = create_smart_tool_selector()
        
        # 构造可用工具列表
        available_tools = []
        for tool_name, result in tool_results.items():
            tool = Tool(
                name=tool_name,
                command=[tool_name],
                args=[],
                language=self._infer_tool_language(tool_name, project_info),
                install=[],
                priority=self._infer_tool_priority(tool_name),
                estimated_time=int(result.execution_time) if result.execution_time else 60,
                categories=[self._infer_tool_category(tool_name)]
            )
            available_tools.append(tool)
        
        # 全局智能工具选择（去重）
        dimension_tool_mapping = smart_selector.select_optimal_tools_for_all_dimensions(
            available_tools, project_info, max_tools_per_dimension=2
        )
        
        # 初始化维度分析器以获取AI分析
        try:
            from .dimension_analyzer import create_dimension_analyzer, AnalysisLevel
            dimension_analyzer = create_dimension_analyzer(AnalysisLevel.AI_POWERED)
            logger.info("使用AI增强维度分析器进行详细分析")
        except ImportError:
            from .dimension_analyzer import create_dimension_analyzer, AnalysisLevel
            dimension_analyzer = create_dimension_analyzer(AnalysisLevel.ENHANCED)
            logger.info("使用增强维度分析器进行详细分析")
        
        # 使用全局智能选择的工具列表 - 先定义工具列表
        selected_tools_1 = dimension_tool_mapping.get(1, [])
        tools_used_1 = [t.name for t in selected_tools_1]
        
        # 维度1: 代码结构与可维护性
        dim1_score, dim1_details = self._analyze_code_structure(project_info, tool_results)
        
        # 添加AI分析
        ai_analysis_1 = None
        try:
            # 使用智能工具选择器选择的实际工具列表，确保与主页面一致
            tool_execution_results = {}
            for tool_name in tools_used_1:
                if tool_name in tool_results:
                    tool_result = tool_results[tool_name]
                    tool_execution_results[tool_name] = {
                        'success': tool_result.success,
                        'execution_time': tool_result.execution_time,
                        'return_code': tool_result.return_code,
                        'result': tool_result.result if tool_result.success else {},
                        'error': tool_result.error if not tool_result.success else None
                    }
            
            dimension_data = {
                'score': dim1_score,
                'status': self._get_status_by_score(dim1_score),
                'details': dim1_details,
                'tools_used': tools_used_1,
                'tool_execution_results': tool_execution_results  # 新增工具执行结果
            }
            ai_analysis_1 = self.ai_analyzer.analyze_dimension(self.dimension_names[0], dimension_data)
        except Exception as e:
            logger.debug(f"维度1 AI分析失败: {e}")
        
        dimensions.append(DimensionReport(
            dimension_id=1,
            dimension_name=self.dimension_names[0],
            score=dim1_score,
            status=self._get_status_by_score(dim1_score),
            tools_used=tools_used_1,  # 使用全局智能选择的工具
            issues_count=dim1_details.get('total_issues', 0),
            details=dim1_details,
            recommendations=self._generate_dimension_recommendations(1, dim1_details),
            ai_analysis=ai_analysis_1
        ))
        
        # 使用全局智能选择的工具列表 - 先定义工具列表
        selected_tools_2 = dimension_tool_mapping.get(2, [])
        tools_used_2 = [t.name for t in selected_tools_2]
        
        # 维度2: 测试覆盖与质量保障
        dim2_score, dim2_details = self._analyze_test_coverage(project_info, tool_results)
        
        # 添加AI分析
        ai_analysis_2 = None
        try:
            # 使用智能工具选择器选择的实际工具列表，确保与主页面一致
            tool_execution_results = {}
            for tool_name in tools_used_2:
                if tool_name in tool_results:
                    tool_result = tool_results[tool_name]
                    tool_execution_results[tool_name] = {
                        'success': tool_result.success,
                        'execution_time': tool_result.execution_time,
                        'return_code': tool_result.return_code,
                        'result': tool_result.result if tool_result.success else {},
                        'error': tool_result.error if not tool_result.success else None
                    }
            
            dimension_data = {
                'score': dim2_score,
                'status': self._get_status_by_score(dim2_score),
                'details': dim2_details,
                'tools_used': tools_used_2,
                'tool_execution_results': tool_execution_results  # 新增工具执行结果
            }
            ai_analysis_2 = self.ai_analyzer.analyze_dimension(self.dimension_names[1], dimension_data)
        except Exception as e:
            logger.debug(f"维度2 AI分析失败: {e}")
        
        dimensions.append(DimensionReport(
            dimension_id=2,
            dimension_name=self.dimension_names[1],
            score=dim2_score,
            status=self._get_status_by_score(dim2_score),
            tools_used=tools_used_2,  # 使用全局智能选择的工具
            issues_count=dim2_details.get('total_issues', 0),
            details=dim2_details,
            recommendations=self._generate_dimension_recommendations(2, dim2_details),
            ai_analysis=ai_analysis_2
        ))
        
        # 使用全局智能选择的工具列表 - 先定义工具列表
        selected_tools_3 = dimension_tool_mapping.get(3, [])
        tools_used_3 = [t.name for t in selected_tools_3]
        
        # 维度3: 构建与工程可重复性
        dim3_score, dim3_details = self._analyze_build_reproducibility(project_info, tool_results)
        
        # 添加AI分析
        ai_analysis_3 = None
        try:
            # 使用智能工具选择器选择的实际工具列表，确保与主页面一致
            tool_execution_results = {}
            for tool_name in tools_used_3:
                if tool_name in tool_results:
                    tool_result = tool_results[tool_name]
                    tool_execution_results[tool_name] = {
                        'success': tool_result.success,
                        'execution_time': tool_result.execution_time,
                        'return_code': tool_result.return_code,
                        'result': tool_result.result if tool_result.success else {},
                        'error': tool_result.error if not tool_result.success else None
                    }
            
            dimension_data = {
                'score': dim3_score,
                'status': self._get_status_by_score(dim3_score),
                'details': dim3_details,
                'tools_used': tools_used_3,
                'tool_execution_results': tool_execution_results  # 新增工具执行结果
            }
            ai_analysis_3 = self.ai_analyzer.analyze_dimension(self.dimension_names[2], dimension_data)
        except Exception as e:
            logger.debug(f"维度3 AI分析失败: {e}")
        
        dimensions.append(DimensionReport(
            dimension_id=3,
            dimension_name=self.dimension_names[2],
            score=dim3_score,
            status=self._get_status_by_score(dim3_score),
            tools_used=tools_used_3,  # 使用全局智能选择的工具
            issues_count=dim3_details.get('total_issues', 0),
            details=dim3_details,
            recommendations=self._generate_dimension_recommendations(3, dim3_details),
            ai_analysis=ai_analysis_3
        ))
        
        # 使用全局智能选择的工具列表 - 先定义工具列表
        selected_tools_4 = dimension_tool_mapping.get(4, [])
        tools_used_4 = [t.name for t in selected_tools_4]
        
        # 维度4: 依赖与许可证合规
        dim4_score, dim4_details = self._analyze_dependencies_license(project_info, tool_results)
        
        # 添加AI分析
        ai_analysis_4 = None
        try:
            # 使用智能工具选择器选择的实际工具列表，确保与主页面一致
            tool_execution_results = {}
            for tool_name in tools_used_4:
                if tool_name in tool_results:
                    tool_result = tool_results[tool_name]
                    tool_execution_results[tool_name] = {
                        'success': tool_result.success,
                        'execution_time': tool_result.execution_time,
                        'return_code': tool_result.return_code,
                        'result': tool_result.result if tool_result.success else {},
                        'error': tool_result.error if not tool_result.success else None
                    }
            
            dimension_data = {
                'score': dim4_score,
                'status': self._get_status_by_score(dim4_score),
                'details': dim4_details,
                'tools_used': tools_used_4,
                'tool_execution_results': tool_execution_results  # 新增工具执行结果
            }
            ai_analysis_4 = self.ai_analyzer.analyze_dimension(self.dimension_names[3], dimension_data)
        except Exception as e:
            logger.debug(f"维度4 AI分析失败: {e}")
        
        dimensions.append(DimensionReport(
            dimension_id=4,
            dimension_name=self.dimension_names[3],
            score=dim4_score,
            status=self._get_status_by_score(dim4_score),
            tools_used=tools_used_4,  # 使用全局智能选择的工具
            issues_count=dim4_details.get('total_issues', 0),
            details=dim4_details,
            recommendations=self._generate_dimension_recommendations(4, dim4_details),
            ai_analysis=ai_analysis_4
        ))
        
        # 使用全局智能选择的工具列表 - 先定义工具列表
        selected_tools_5 = dimension_tool_mapping.get(5, [])
        tools_used_5 = [t.name for t in selected_tools_5]
        
        # 维度5: 安全性与敏感信息防护
        dim5_score, dim5_details = self._analyze_security(project_info, tool_results)
        
        # 添加AI分析
        ai_analysis_5 = None
        try:
            # 使用智能工具选择器选择的实际工具列表，确保与主页面一致
            tool_execution_results = {}
            for tool_name in tools_used_5:
                if tool_name in tool_results:
                    tool_result = tool_results[tool_name]
                    tool_execution_results[tool_name] = {
                        'success': tool_result.success,
                        'execution_time': tool_result.execution_time,
                        'return_code': tool_result.return_code,
                        'result': tool_result.result if tool_result.success else {},
                        'error': tool_result.error if not tool_result.success else None
                    }
            
            dimension_data = {
                'score': dim5_score,
                'status': self._get_status_by_score(dim5_score),
                'details': dim5_details,
                'tools_used': tools_used_5,
                'tool_execution_results': tool_execution_results  # 新增工具执行结果
            }
            ai_analysis_5 = self.ai_analyzer.analyze_dimension(self.dimension_names[4], dimension_data)
        except Exception as e:
            logger.debug(f"维度5 AI分析失败: {e}")
        
        dimensions.append(DimensionReport(
            dimension_id=5,
            dimension_name=self.dimension_names[4],
            score=dim5_score,
            status=self._get_status_by_score(dim5_score),
            tools_used=tools_used_5,  # 使用全局智能选择的工具
            issues_count=dim5_details.get('total_issues', 0),
            details=dim5_details,
            recommendations=self._generate_dimension_recommendations(5, dim5_details),
            ai_analysis=ai_analysis_5
        ))
        
        # 其他维度使用简化分析
        for dim_id in range(6, 15):  # 维度6-14
            dim_score, dim_details = self._analyze_basic_dimension(dim_id, project_info)
            
            # 使用全局智能选择的工具列表
            selected_tools = dimension_tool_mapping.get(dim_id, [])
            tools_used = [t.name for t in selected_tools]
            
            # 为每个维度添加AI分析
            ai_analysis = None
            try:
                # 获取该维度使用的工具及其执行结果
                tool_execution_results = {}
                for tool_name in tools_used:
                    if tool_name in tool_results:
                        tool_result = tool_results[tool_name]
                        tool_execution_results[tool_name] = {
                            'success': tool_result.success,
                            'execution_time': tool_result.execution_time,
                            'return_code': tool_result.return_code,
                            'result': tool_result.result if tool_result.success else {},
                            'error': tool_result.error if not tool_result.success else None
                        }
                
                dimension_data = {
                    'score': dim_score,
                    'status': self._get_status_by_score(dim_score),
                    'details': dim_details,
                    'tools_used': tools_used,
                    'tool_execution_results': tool_execution_results  # 新增工具执行结果
                }
                ai_analysis = self.ai_analyzer.analyze_dimension(self.dimension_names[dim_id-1], dimension_data)
            except Exception as e:
                logger.debug(f"维度{dim_id} AI分析失败: {e}")
            
            dimensions.append(DimensionReport(
                dimension_id=dim_id,
                dimension_name=self.dimension_names[dim_id-1],
                score=dim_score,
                status=self._get_status_by_score(dim_score),
                tools_used=tools_used,  # 使用全局智能选择的工具
                issues_count=0,
                details=dim_details,
                recommendations=self._generate_dimension_recommendations(dim_id, dim_details),
                ai_analysis=ai_analysis
            ))
        
        return dimensions
    
    def _analyze_code_structure(self, project_info: ProjectInfo,
                              tool_results: Dict[str, ToolResult]) -> tuple[float, Dict[str, Any]]:
        """分析代码结构与可维护性"""
        score = 60.0  # 基础分数
        details = {
            'primary_language': project_info.get_primary_language(),
            'code_lines': project_info.size_metrics.code_lines,
            'code_files': project_info.size_metrics.code_files,
            'total_issues': 0,
            'quality_tools_results': {}
        }
        
        # 基于工具结果调整分数
        quality_tools = ['pylint', 'flake8', 'mypy', 'eslint', 'checkstyle']
        for tool_name in quality_tools:
            if tool_name in tool_results:
                result = tool_results[tool_name]
                details['quality_tools_results'][tool_name] = result.result
                
                if result.success and result.result:
                    tool_score = result.result.get('score', 60)
                    score = (score + tool_score) / 2  # 平均得分
                    details['total_issues'] += result.result.get('issues_count', 0)
        
        # 基于项目规模调整
        if project_info.size_metrics.code_lines > 10000:
            score -= 5  # 大项目维护难度更高
        
        return min(100, max(0, score)), details
    
    def _analyze_test_coverage(self, project_info: ProjectInfo,
                             tool_results: Dict[str, ToolResult]) -> tuple[float, Dict[str, Any]]:
        """分析测试覆盖与质量保障"""
        score = 50.0  # 基础分数
        details = {
            'test_files': project_info.size_metrics.test_files,
            'test_lines': project_info.size_metrics.test_lines,
            'coverage_percentage': 0,
            'total_issues': 0,
            'test_tools_results': {}
        }
        
        # 基于测试文件数量
        if project_info.size_metrics.test_files > 0:
            score += 20
            
            # 计算测试覆盖率
            if project_info.size_metrics.code_files > 0:
                test_ratio = project_info.size_metrics.test_files / project_info.size_metrics.code_files
                score += min(30, test_ratio * 30)
        
        # 基于工具结果
        test_tools = ['pytest', 'coverage', 'jest']
        for tool_name in test_tools:
            if tool_name in tool_results:
                result = tool_results[tool_name]
                details['test_tools_results'][tool_name] = result.result
                
                if result.success and result.result:
                    if 'percentage' in result.result:
                        details['coverage_percentage'] = result.result['percentage']
                        score += result.result['percentage'] * 0.3
        
        return min(100, max(0, score)), details
    
    def _analyze_build_reproducibility(self, project_info: ProjectInfo,
                                     tool_results: Dict[str, ToolResult]) -> tuple[float, Dict[str, Any]]:
        """分析构建与工程可重复性"""
        score = 40.0  # 基础分数
        details = {
            'build_tools': project_info.build_tools,
            'dependencies_count': sum(len(deps) for deps in project_info.dependencies.values()),
            'total_issues': 0,
            'format_tools_results': {}
        }
        
        # 基于构建工具
        score += min(30, len(project_info.build_tools) * 10)
        
        # 基于依赖管理
        if project_info.dependencies:
            score += 20
        
        # 基于格式化工具结果
        format_tools = ['black', 'prettier', 'rustfmt', 'gofmt']
        for tool_name in format_tools:
            if tool_name in tool_results:
                result = tool_results[tool_name]
                details['format_tools_results'][tool_name] = result.result
                
                if result.success:
                    score += 10
        
        return min(100, max(0, score)), details
    
    def _analyze_dependencies_license(self, project_info: ProjectInfo,
                                    tool_results: Dict[str, ToolResult]) -> tuple[float, Dict[str, Any]]:
        """分析依赖与许可证合规"""
        score = 70.0  # 基础分数
        details = {
            'dependencies': project_info.dependencies,
            'total_dependencies': sum(len(deps) for deps in project_info.dependencies.values()),
            'total_issues': 0,
            'security_tools_results': {}
        }
        
        # 基于安全工具结果
        security_tools = ['safety', 'npm-audit', 'cargo-audit']
        for tool_name in security_tools:
            if tool_name in tool_results:
                result = tool_results[tool_name]
                details['security_tools_results'][tool_name] = result.result
                
                if result.success and result.result:
                    vulnerabilities = result.result.get('issues_count', 0)
                    details['total_issues'] += vulnerabilities
                    score -= min(30, vulnerabilities * 5)
        
        return min(100, max(0, score)), details
    
    def _analyze_security(self, project_info: ProjectInfo,
                         tool_results: Dict[str, ToolResult]) -> tuple[float, Dict[str, Any]]:
        """分析安全性与敏感信息防护"""
        score = 75.0  # 基础分数
        details = {
            'security_issues': 0,
            'total_issues': 0,
            'security_tools_results': {}
        }
        
        # 基于安全工具结果
        security_tools = ['bandit', 'semgrep', 'gosec', 'gitleaks']
        for tool_name in security_tools:
            if tool_name in tool_results:
                result = tool_results[tool_name]
                details['security_tools_results'][tool_name] = result.result
                
                if result.success and result.result:
                    issues = result.result.get('issues_count', 0)
                    details['security_issues'] += issues
                    details['total_issues'] += issues
                    
                    # 根据严重程度调整分数
                    severity_counts = result.result.get('by_severity', {})
                    penalty = (severity_counts.get('HIGH', 0) * 15 + 
                             severity_counts.get('MEDIUM', 0) * 8 + 
                             severity_counts.get('LOW', 0) * 3)
                    score -= min(50, penalty)
        
        return min(100, max(0, score)), details
    
    def _analyze_basic_dimension(self, dimension_id: int, 
                               project_info: ProjectInfo) -> tuple[float, Dict[str, Any]]:
        """基础维度分析（用于暂未实现详细分析的维度）"""
        
        # 基于项目基本信息给出评分
        base_score = 65.0
        details = {'analysis_method': 'basic_heuristic'}
        
        # 根据维度特性调整基础分数
        if dimension_id == 6:  # CI/CD 自动化保障
            # 检查是否有CI/CD文件
            project_path = pathlib.Path(project_info.path)
            ci_files = ['.github/workflows', '.gitlab-ci.yml', 'Jenkinsfile']
            if any((project_path / f).exists() for f in ci_files):
                base_score = 80.0
            else:
                base_score = 45.0
                
        elif dimension_id == 7:  # 使用文档与复现性
            # 检查文档文件
            project_path = pathlib.Path(project_info.path)
            doc_files = ['README.md', 'docs/', 'INSTALL.md']
            doc_count = sum(1 for f in doc_files if (project_path / f).exists())
            base_score = 40.0 + doc_count * 20
            
        elif dimension_id == 10:  # 开源协议与法律合规
            # 检查许可证文件
            project_path = pathlib.Path(project_info.path)
            license_files = ['LICENSE', 'LICENSE.txt', 'COPYING']
            if any((project_path / f).exists() for f in license_files):
                base_score = 85.0
            else:
                base_score = 30.0
        
        details['base_score'] = base_score
        return base_score, details
    
    def _get_tools_for_dimension(self, dimension_id: int, 
                               tool_results: Dict[str, ToolResult]) -> List[str]:
        """获取用于特定维度的工具列表"""
        
        dimension_tool_mapping = {
            1: ['pylint', 'flake8', 'mypy', 'eslint', 'checkstyle'],  # 代码结构与可维护性
            2: ['pytest', 'coverage', 'jest'],  # 测试覆盖与质量保障
            3: ['black', 'prettier', 'rustfmt', 'clang-format', 'isort'],  # 构建与工程可重复性
            4: ['safety', 'npm-audit', 'cargo-audit', 'trivy', 'syft'],  # 依赖与许可证合规
            5: ['bandit', 'semgrep', 'gosec', 'gitleaks'],  # 安全性与敏感信息防护
            6: ['sonarqube-scanner'],  # CI/CD 自动化保障
            7: [],  # 使用文档与复现性 (文件检查，无工具)
            8: ['tsc', 'tslint'],  # 接口与平台兼容性
            9: ['black', 'prettier', 'rustfmt', 'clang-format'],  # 协作流程与代码规范
            10: [],  # 开源协议与法律合规 (文件检查，无工具)
            11: [],  # 社区治理与贡献机制 (Git分析，无专用工具)
            12: ['gitleaks'],  # 舆情与风险监控
            13: ['bandit', 'semgrep'],  # 数据与算法合规审核
            14: []  # IP（知识产权） (文件检查，无工具)
        }
        
        tools_for_dim = dimension_tool_mapping.get(dimension_id, [])
        return [tool for tool in tools_for_dim if tool in tool_results]
    
    def _get_status_by_score(self, score: float) -> str:
        """根据分数确定状态"""
        if score >= 80:
            return "PASS"
        elif score >= 60:
            return "WARN"
        else:
            return "FAIL"
    
    def _calculate_overall_status(self, overall_score: float, 
                                dimensions: List[DimensionReport]) -> str:
        """计算总体状态"""
        if overall_score >= 80:
            return "EXCELLENT"
        elif overall_score >= 70:
            return "GOOD"
        elif overall_score >= 60:
            return "FAIR"
        else:
            return "NEEDS_IMPROVEMENT"
    
    def _generate_dimension_recommendations(self, dimension_id: int, 
                                          details: Dict[str, Any]) -> List[str]:
        """生成维度改进建议"""
        recommendations = []
        
        if dimension_id == 1:  # 代码结构
            if details.get('total_issues', 0) > 50:
                recommendations.append("代码质量问题较多，建议优先修复高优先级问题")
            if details.get('code_lines', 0) > 10000:
                recommendations.append("项目规模较大，建议考虑模块化重构")
                
        elif dimension_id == 2:  # 测试覆盖
            if details.get('test_files', 0) == 0:
                recommendations.append("缺少测试文件，建议添加单元测试")
            if details.get('coverage_percentage', 0) < 70:
                recommendations.append("测试覆盖率较低，建议提高到70%以上")
                
        elif dimension_id == 5:  # 安全性
            if details.get('security_issues', 0) > 0:
                recommendations.append("发现安全问题，请及时修复")
                
        # 通用建议
        if not recommendations:
            recommendations.append("继续保持当前的良好实践")
        
        return recommendations
    
    def _generate_json_report(self, audit_report: AuditReport, 
                            output_path: pathlib.Path) -> str:
        """生成JSON格式报告"""
        report_file = output_path / f"{audit_report.project_info.name}_audit_report.json"
        
        # 转换为可序列化的字典
        report_dict = {
            'project_info': {
                'name': audit_report.project_info.name,
                'path': audit_report.project_info.path,
                'languages': audit_report.project_info.languages,
                'structure_type': audit_report.project_info.structure_type.value,
                'project_type': audit_report.project_info.project_type.value if hasattr(audit_report.project_info.project_type, 'value') else str(audit_report.project_info.project_type),
                'size_metrics': asdict(audit_report.project_info.size_metrics),
                'build_tools': audit_report.project_info.build_tools,
                'confidence': audit_report.project_info.confidence
            },
            'timestamp': audit_report.timestamp,
            'overall_score': audit_report.overall_score,
            'overall_status': audit_report.overall_status,
            'summary': audit_report.summary,
            'dimensions': [asdict(dim) for dim in audit_report.dimensions],
            'tool_results': {name: result.to_dict() for name, result in audit_report.tool_results.items()},
            'execution_stats': audit_report.execution_stats,
            'ai_analysis': audit_report.ai_analysis
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON报告已生成: {report_file}")
        return str(report_file)
    
    def _generate_html_report(self, audit_report: AuditReport, 
                            output_path: pathlib.Path) -> str:
        """生成HTML格式报告"""
        report_file = output_path / f"{audit_report.project_info.name}_audit_report.html"
        
        # 构建HTML内容
        html_content = self._build_html_content(audit_report)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML报告已生成: {report_file}")
        return str(report_file)
    
    def _build_html_content(self, audit_report: AuditReport) -> str:
        """构建HTML报告内容"""
        
        # 状态标签样式
        status_colors = {
            'PASS': '#28a745', 'WARN': '#ffc107', 'FAIL': '#dc3545',
            'EXCELLENT': '#28a745', 'GOOD': '#17a2b8', 'FAIR': '#ffc107', 
            'NEEDS_IMPROVEMENT': '#dc3545'
        }
        
        # 构建维度表格，包含工具执行状态
        dimensions_html = ""
        for dim in audit_report.dimensions:
            color = status_colors.get(dim.status, '#6c757d')
            # 清理文件名中的特殊字符，与生成文件名逻辑保持一致
            clean_name = dim.dimension_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
            detail_link = f"dimensions/dimension_{dim.dimension_id}_{clean_name}.html"
            
            # 构建工具状态显示
            if dim.tools_used:
                tools_html = []
                for tool_name in dim.tools_used:
                    tool_result = audit_report.tool_results.get(tool_name)
                    if tool_result:
                        status_icon = "✅" if tool_result.success else "❌"
                        # 创建工具状态的超链接，点击跳转到工具结果报告
                        tool_report_link = f"tools/{tool_name}_report.html"
                        tool_link = f'<a href="{tool_report_link}" style="color: #27ae60; text-decoration: none;" title="执行时间: {tool_result.execution_time:.2f}s, 退出码: {tool_result.return_code}">{tool_name} {status_icon}</a>'
                        tools_html.append(tool_link)
                    else:
                        tools_html.append(f'{tool_name} ❓')
                tools_display = ', '.join(tools_html)
            else:
                tools_display = 'N/A'
            
            dimensions_html += f"""
            <tr>
                <td>{dim.dimension_id}</td>
                <td><a href="{detail_link}" style="color: #27ae60; text-decoration: none;">{dim.dimension_name}</a></td>
                <td><span class="badge" style="background-color: {color}">{dim.status}</span></td>
                <td><strong>{dim.score:.1f}</strong></td>
                <td>{dim.issues_count}</td>
                <td>{tools_display}</td>
            </tr>
            """
        
        # 工具执行摘要已移除，在维度工具列中显示
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{audit_report.project_info.name} - OSS审计报告</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    min-height: 100vh; 
                    color: #212529;
                    line-height: 1.6;
                }}
                .container {{ 
                    max-width: 1200px; 
                    margin: 0 auto; 
                    background: white; 
                    border-radius: 16px; 
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1), 0 4px 8px rgba(0,0,0,0.05); 
                    overflow: hidden;
                    border: 1px solid rgba(255,255,255,0.8);
                }}
                .header {{ 
                    background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
                    color: white; 
                    padding: 40px 30px; 
                    position: relative;
                }}
                .header::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: linear-gradient(135deg, rgba(39,174,96,0.1) 0%, rgba(46,204,113,0.1) 100%);
                }}
                .header h1 {{ position: relative; z-index: 1; margin: 0 0 10px 0; }}
                .header p {{ position: relative; z-index: 1; opacity: 0.9; margin: 5px 0; }}
                .content {{ padding: 40px; }}
                .summary-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
                    gap: 24px; 
                    margin: 30px 0; 
                }}
                .summary-card {{ 
                    background: linear-gradient(135deg, #fff 0%, #fcfcfc 100%); 
                    padding: 28px; 
                    border-radius: 16px; 
                    text-align: center; 
                    border: 1px solid rgba(233,236,239,0.8);
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                    overflow: hidden;
                }}
                .summary-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
                    opacity: 0;
                    transition: opacity 0.3s ease;
                }}
                .summary-card:hover {{
                    transform: translateY(-4px) scale(1.02);
                    box-shadow: 0 12px 24px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06);
                    border-color: rgba(39,174,96,0.3);
                }}
                .summary-card:hover::before {{
                    opacity: 1;
                }}
                .summary-card h3 {{ 
                    margin: 0 0 15px 0; 
                    color: #2c3e50; 
                    font-size: 1.1em;
                    font-weight: 600;
                }}
                .summary-card .value {{ 
                    font-size: 2.2em; 
                    font-weight: 700; 
                    color: #27ae60;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin: 25px 0; 
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
                    border: 1px solid rgba(233,236,239,0.6);
                }}
                th, td {{ 
                    padding: 18px 16px; 
                    text-align: left; 
                    border-bottom: 1px solid rgba(233,236,239,0.6); 
                }}
                th {{ 
                    background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
                    color: white;
                    font-weight: 600; 
                    text-transform: uppercase;
                    font-size: 0.85em;
                    letter-spacing: 0.8px;
                    position: relative;
                }}
                th::after {{
                    content: '';
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(90deg, #27ae60, #2ecc71);
                }}
                tr:hover {{ 
                    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                    transition: background 0.2s ease;
                }}
                td a {{
                    transition: color 0.2s ease;
                }}
                td a:hover {{
                    color: #1e8449;
                    text-decoration: none;
                }}
                .badge {{ 
                    padding: 6px 12px; 
                    border-radius: 20px; 
                    color: white; 
                    font-size: 0.875em; 
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .section {{ margin: 40px 0; }}
                .section h2 {{ 
                    color: #2c3e50; 
                    border-bottom: 3px solid #27ae60; 
                    padding-bottom: 12px; 
                    font-size: 1.8em;
                    font-weight: 700;
                    margin-bottom: 25px;
                }}
                .status-excellent {{ background: #27ae60; }}
                .status-good {{ background: #f39c12; }}
                .status-fair {{ background: #e67e22; }}
                .status-poor {{ background: #e74c3c; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{audit_report.project_info.name} - OSS审计报告</h1>
                    <p>生成时间: {audit_report.timestamp}</p>
                    <p>项目路径: {audit_report.project_info.path}</p>
                </div>
                
                <div class="content">
                    <div class="section">
                        <h2>总体评估</h2>
                        <div class="summary-grid">
                            <div class="summary-card">
                                <h3>总体得分</h3>
                                <div class="value" style="color: {status_colors.get(audit_report.overall_status, '#6c757d')}">{audit_report.overall_score:.1f}</div>
                            </div>
                            <div class="summary-card">
                                <h3>评估状态</h3>
                                <div class="value" style="color: {status_colors.get(audit_report.overall_status, '#6c757d')}">{audit_report.overall_status}</div>
                            </div>
                            <div class="summary-card">
                                <h3>通过维度</h3>
                                <div class="value">{audit_report.summary['passed_dimensions']}/{audit_report.summary['total_dimensions']}</div>
                            </div>
                            <div class="summary-card">
                                <h3>主要语言</h3>
                                <div class="value" style="font-size: 1.5em">{audit_report.summary.get('primary_language', 'N/A')}</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>项目信息</h2>
                        <div class="summary-grid">
                            <div class="summary-card">
                                <h3>项目结构</h3>
                                <div class="value" style="font-size: 1.2em">{audit_report.summary.get('structure_type', 'N/A')}</div>
                            </div>
                            <div class="summary-card">
                                <h3>项目类型</h3>
                                <div class="value" style="font-size: 1.2em">{audit_report.summary.get('project_type', 'N/A')}</div>
                            </div>
                            <div class="summary-card">
                                <h3>代码规模</h3>
                                <div class="value">{audit_report.summary.get('code_lines', 0):,} 行</div>
                            </div>
                            <div class="summary-card">
                                <h3>项目大小</h3>
                                <div class="value" style="font-size: 1.2em">{audit_report.summary.get('project_size', 'N/A')}</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>维度评估详情</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>维度</th>
                                    <th>名称</th>
                                    <th>状态</th>
                                    <th>得分</th>
                                    <th>问题数</th>
                                    <th>使用工具</th>
                                </tr>
                            </thead>
                            <tbody>
                                {dimensions_html}
                            </tbody>
                        </table>
                    </div>
                    
"""
        
        # 添加AI分析部分（如果有的话）
        if audit_report.ai_analysis:
            ai_analysis_html = f"""
                    <div class="section">
                        <h2>AI智能分析</h2>
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #27ae60;">
                            <h3>项目综合评估</h3>
                            <p><strong>总体评价:</strong> {audit_report.ai_analysis.get('overall_assessment', 'AI分析数据格式错误')}</p>
                            <p><strong>主要优势:</strong> {audit_report.ai_analysis.get('strengths', 'N/A')}</p>
                            <p><strong>改进建议:</strong> {audit_report.ai_analysis.get('recommendations', 'N/A')}</p>
                            <p><strong>风险提示:</strong> {audit_report.ai_analysis.get('risks', 'N/A')}</p>
                        </div>
                    </div>"""
            html_content += ai_analysis_html

        html_content += """
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def generate_adaptive_audit_report(self, project_info: ProjectInfo,
                                     tool_results: Dict[str, Any],
                                     execution_stats: Dict[str, Any],
                                     adaptive_scoring_model,
                                     intelligent_recommendations,
                                     optimization_actions,
                                     output_dir: str) -> str:
        """
        生成自适应审计报告
        
        Args:
            project_info: 项目信息
            tool_results: 工具执行结果
            execution_stats: 执行统计信息
            adaptive_scoring_model: 自适应评分模型
            intelligent_recommendations: 智能推荐结果
            optimization_actions: 优化建议
            output_dir: 输出目录
            
        Returns:
            主报告文件路径
        """
        logger.info(f"生成智能自适应审计报告，输出目录: {output_dir}")
        
        # 创建输出目录
        output_path = pathlib.Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 构建增强版审计报告数据
        audit_report = self._build_adaptive_audit_report(
            project_info, tool_results, execution_stats,
            adaptive_scoring_model, intelligent_recommendations, optimization_actions)
        
        # 生成不同格式的报告
        reports_generated = []
        
        # 1. 生成增强JSON报告
        json_report_path = self._generate_adaptive_json_report(audit_report, output_path)
        reports_generated.append(json_report_path)
        
        # 2. 生成增强HTML报告
        html_report_path = self._generate_adaptive_html_report(audit_report, output_path)
        reports_generated.append(html_report_path)
        
        # 3. 生成维度详细报告
        dimension_reports = self._generate_dimension_reports(audit_report, output_path)
        reports_generated.extend(dimension_reports)
        
        # 4. 生成工具结果报告
        tool_reports = self._generate_tool_reports(audit_report, output_path)
        reports_generated.extend(tool_reports)
        
        # 5. 生成智能推荐报告
        recommendation_report = self._generate_recommendation_report(
            intelligent_recommendations, output_path, project_info)
        reports_generated.append(recommendation_report)
        
        logger.info(f"智能自适应报告生成完成，共生成 {len(reports_generated)} 个文件")
        return html_report_path  # 返回主报告路径
    
    def _build_adaptive_audit_report(self, project_info: ProjectInfo,
                                   tool_results: Dict[str, Any],
                                   execution_stats: Dict[str, Any],
                                   adaptive_scoring_model,
                                   intelligent_recommendations,
                                   optimization_actions) -> AuditReport:
        """构建自适应审计报告数据"""
        
        # 使用自适应评分模型重新计算维度得分
        dimensions = self._analyze_adaptive_dimensions(
            project_info, tool_results, adaptive_scoring_model)
        
        # 使用自适应权重计算总体得分
        overall_score = self._calculate_adaptive_overall_score(
            dimensions, adaptive_scoring_model)
        
        # 确定总体状态
        overall_status = self._calculate_overall_status(overall_score, dimensions)
        
        # 构建增强摘要信息
        summary = {
            'total_dimensions': len(dimensions),
            'passed_dimensions': len([d for d in dimensions if d.status == 'PASS']),
            'warned_dimensions': len([d for d in dimensions if d.status == 'WARN']),
            'failed_dimensions': len([d for d in dimensions if d.status == 'FAIL']),
            'primary_language': project_info.get_primary_language(),
            'project_size': project_info.size_metrics.get_size_category(),
            'code_lines': project_info.size_metrics.code_lines,
            'structure_type': project_info.structure_type.value if hasattr(project_info.structure_type, 'value') else str(project_info.structure_type),
            'project_type': project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type),
            # 智能分析增强信息
            'adaptive_scoring': {
                'confidence_level': adaptive_scoring_model.confidence_level,
                'model_version': adaptive_scoring_model.model_version,
                'weights_adjusted': len(adaptive_scoring_model.weights) > 0
            },
            'intelligent_recommendations': {
                'total_recommendations': len(intelligent_recommendations.recommendations),
                'roadmap_phases': len(intelligent_recommendations.roadmap.phases),
                'estimated_roi': intelligent_recommendations.roadmap.estimated_roi,
                'confidence_level': intelligent_recommendations.confidence_level
            },
            'optimization_actions': {
                'additional_tools': len(optimization_actions.additional_tools),
                'weight_adjustments': len(optimization_actions.weight_adjustments),
                'has_time_adjustment': optimization_actions.time_budget_adjustment is not None
            }
        }
        
        # 执行统计信息处理
        executed_tools = {
            name: result for name, result in tool_results.items() 
            if not (hasattr(result, 'status') and getattr(result, 'status', None) == 'not_available')
        }
        
        total_tools = len(executed_tools)
        successful_tools = len([
            r for r in executed_tools.values() 
            if (getattr(r, 'success', False) if hasattr(r, 'success') 
                else (r.get('success', False) if isinstance(r, dict) else False))
        ])
        failed_tools = total_tools - successful_tools
        
        corrected_execution_stats = {
            'total_tools': total_tools,
            'successful_tools': successful_tools,
            'failed_tools': failed_tools,
            'total_time': sum(
                getattr(r, 'execution_time', 0) if hasattr(r, 'execution_time') 
                else r.get('execution_time', 0) if isinstance(r, dict) and isinstance(r.get('execution_time'), (int, float))
                else 0
                for r in executed_tools.values()
            )
        }
        
        return AuditReport(
            project_info=project_info,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            dimensions=dimensions,
            tool_results=tool_results,
            overall_score=overall_score,
            overall_status=overall_status,
            summary=summary,
            execution_stats=corrected_execution_stats,
            ai_analysis=None  # AI分析保持兼容性
        )
    
    def _analyze_adaptive_dimensions(self, project_info: ProjectInfo,
                                   tool_results: Dict[str, Any],
                                   adaptive_scoring_model) -> List[DimensionReport]:
        """使用自适应评分模型分析维度"""
        dimensions = []
        
        # 使用自适应权重进行维度分析
        weights = adaptive_scoring_model.weights
        quality_adjustments = adaptive_scoring_model.quality_adjustments
        
        # 为简化实现，这里仍使用原有的维度分析逻辑
        # 但应用自适应权重调整
        original_dimensions = self._analyze_dimensions(project_info, tool_results)
        
        for dim in original_dimensions:
            # 应用自适应评分调整
            adjusted_score = self._apply_adaptive_scoring(
                dim.score, dim.dimension_name, weights, quality_adjustments)
            
            adjusted_dim = DimensionReport(
                dimension_id=dim.dimension_id,
                dimension_name=dim.dimension_name,
                score=adjusted_score,
                status=self._get_status_by_score(adjusted_score),
                tools_used=dim.tools_used,
                issues_count=dim.issues_count,
                details={**dim.details, 'adaptive_score_applied': True, 'original_score': dim.score},
                recommendations=dim.recommendations,
                ai_analysis=dim.ai_analysis
            )
            dimensions.append(adjusted_dim)
        
        return dimensions
    
    def _apply_adaptive_scoring(self, original_score: float, dimension_name: str,
                              weights: Dict[str, float], 
                              quality_adjustments: Dict[str, float]) -> float:
        """应用自适应评分调整"""
        adjusted_score = original_score
        
        # 应用质量调整
        confidence_bonus = quality_adjustments.get('confidence_bonus', 0)
        confidence_penalty = quality_adjustments.get('confidence_penalty', 0)
        consistency_bonus = quality_adjustments.get('consistency_bonus', 0)
        consistency_penalty = quality_adjustments.get('consistency_penalty', 0)
        
        # 应用调整
        adjusted_score += (confidence_bonus + consistency_bonus) * 100
        adjusted_score += (confidence_penalty + consistency_penalty) * 100
        
        # 确保分数在有效范围内
        return max(0, min(100, adjusted_score))
    
    def _calculate_adaptive_overall_score(self, dimensions: List[DimensionReport],
                                        adaptive_scoring_model) -> float:
        """使用自适应权重计算总体得分"""
        if not dimensions:
            return 0
        
        weights = adaptive_scoring_model.weights
        weighted_sum = 0
        total_weight = 0
        
        for dim in dimensions:
            # 映射维度名称到权重键
            weight_key = self._map_dimension_to_weight_key(dim.dimension_name)
            weight = weights.get(weight_key, 1.0 / len(dimensions))  # 默认平均权重
            
            weighted_sum += dim.score * weight
            total_weight += weight
        
        return weighted_sum / max(total_weight, 1.0)
    
    def _map_dimension_to_weight_key(self, dimension_name: str) -> str:
        """映射维度名称到权重键"""
        mapping = {
            "代码结构与可维护性": "quality",
            "测试覆盖与质量保障": "testing",
            "构建与工程可重复性": "reproducibility", 
            "依赖与许可证合规": "dependencies",
            "安全性与敏感信息防护": "security",
            "CI/CD 自动化保障": "automation",
            "使用文档与复现性": "documentation",
            "接口与平台兼容性": "compatibility",
            "协作流程与代码规范": "collaboration",
            "开源协议与法律合规": "legal",
            "社区治理与贡献机制": "community",
            "舆情与风险监控": "risk_monitoring",
            "数据与算法合规审核": "compliance",
            "IP（知识产权）": "intellectual_property"
        }
        return mapping.get(dimension_name, "quality")
    
    def _generate_adaptive_json_report(self, audit_report: AuditReport,
                                     output_path: pathlib.Path) -> str:
        """生成自适应JSON报告"""
        report_file = output_path / f"{audit_report.project_info.name}_adaptive_audit_report.json"
        
        # 转换为可序列化的字典，包含智能分析增强信息
        report_dict = {
            'project_info': {
                'name': audit_report.project_info.name,
                'path': audit_report.project_info.path,
                'languages': audit_report.project_info.languages,
                'structure_type': audit_report.project_info.structure_type.value,
                'project_type': audit_report.project_info.project_type.value if hasattr(audit_report.project_info.project_type, 'value') else str(audit_report.project_info.project_type),
                'size_metrics': asdict(audit_report.project_info.size_metrics),
                'build_tools': audit_report.project_info.build_tools,
                'confidence': audit_report.project_info.confidence
            },
            'timestamp': audit_report.timestamp,
            'overall_score': audit_report.overall_score,
            'overall_status': audit_report.overall_status,
            'summary': audit_report.summary,
            'dimensions': [asdict(dim) for dim in audit_report.dimensions],
            'tool_results': {
                name: result if isinstance(result, dict) else {
                    'success': getattr(result, 'success', False) if hasattr(result, 'success') else False,
                    'execution_time': getattr(result, 'execution_time', 0) if hasattr(result, 'execution_time') else 0,
                    'issues_count': getattr(result, 'issues_count', 0) if hasattr(result, 'issues_count') else 0
                } 
                for name, result in audit_report.tool_results.items()
            },
            'execution_stats': audit_report.execution_stats,
            'report_version': 'OSS Audit 2.0 智能增强版',
            'features_used': [
                'adaptive_scoring',
                'intelligent_recommendations', 
                'optimization_actions'
            ]
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"自适应JSON报告已生成: {report_file}")
        return str(report_file)
    
    def _generate_adaptive_html_report(self, audit_report: AuditReport,
                                     output_path: pathlib.Path) -> str:
        """生成自适应HTML报告"""
        report_file = output_path / f"{audit_report.project_info.name}_audit_report.html"
        
        # 构建增强版HTML内容，包含智能分析特性
        html_content = self._build_adaptive_html_content(audit_report)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"自适应HTML报告已生成: {report_file}")
        return str(report_file)
    
    def _build_adaptive_html_content(self, audit_report: AuditReport) -> str:
        """构建自适应HTML报告内容"""
        # 复用原有的HTML构建逻辑，添加智能分析增强信息
        base_html = self._build_html_content(audit_report)
        
        # 在报告中添加智能分析特性信息
        adaptive_section = f"""
                    <div class="section">
                        <h2>🧠 智能分析特性</h2>
                        <div class="summary-grid">
                            <div class="summary-card">
                                <h3>自适应评分</h3>
                                <div class="value" style="font-size: 1.2em">信心度 {audit_report.summary['adaptive_scoring']['confidence_level']:.2f}</div>
                            </div>
                            <div class="summary-card">
                                <h3>智能推荐</h3>
                                <div class="value">{audit_report.summary['intelligent_recommendations']['total_recommendations']} 条建议</div>
                                <div style="margin-top: 10px;">
                                    <a href="{audit_report.project_info.name}_recommendations.html" 
                                       style="color: #007bff; text-decoration: none; font-size: 0.9em; border: 1px solid #007bff; padding: 5px 10px; border-radius: 4px; display: inline-block;">
                                        查看详细推荐 →
                                    </a>
                                </div>
                            </div>
                            <div class="summary-card">
                                <h3>改进路线图</h3>
                                <div class="value">{audit_report.summary['intelligent_recommendations']['roadmap_phases']} 个阶段</div>
                            </div>
                            <div class="summary-card">
                                <h3>预估ROI</h3>
                                <div class="value">{audit_report.summary['intelligent_recommendations']['estimated_roi']:.1f}%</div>
                            </div>
                        </div>
                    </div>
        """
        
        # 在项目信息部分后插入
        insertion_point = '<div class="section">\n                        <h2>维度评估详情</h2>'
        enhanced_html = base_html.replace(insertion_point, adaptive_section + '\n                    ' + insertion_point)
        
        return enhanced_html
    
    def _generate_recommendation_report(self, intelligent_recommendations,
                                      output_path: pathlib.Path, 
                                      project_info: ProjectInfo) -> str:
        """生成智能推荐报告"""
        report_file = output_path / f"{project_info.name}_recommendations.html"
        
        # 构建推荐报告HTML
        recommendations_html = ""
        for i, rec in enumerate(intelligent_recommendations.recommendations, 1):
            priority_color = "#dc3545" if rec.priority_score > 80 else "#ffc107" if rec.priority_score > 60 else "#28a745"
            
            action_items_html = "".join([f"<li>{item}</li>" for item in rec.action_items])
            resources_html = "".join([f"<li>{resource}</li>" for resource in rec.resources])
            success_metrics_html = "".join([f"<li>{metric}</li>" for metric in rec.success_metrics])
            
            recommendations_html += f"""
            <div class="recommendation-card" style="border-left: 4px solid {priority_color}; margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="margin: 0; color: #2c3e50;">#{i} {rec.title}</h3>
                    <span style="background: {priority_color}; color: white; padding: 4px 12px; border-radius: 15px; font-size: 0.85em; font-weight: 600;">
                        优先级 {rec.priority_score:.1f}
                    </span>
                </div>
                <p style="color: #495057; margin: 10px 0;"><strong>描述:</strong> {rec.description}</p>
                <p style="color: #495057; margin: 10px 0;"><strong>理由:</strong> {rec.rationale}</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 15px 0;">
                    <div>
                        <p style="margin: 5px 0;"><strong>预估工作量:</strong> {rec.estimated_effort} 小时</p>
                        <p style="margin: 5px 0;"><strong>影响程度:</strong> {rec.impact_level:.1%}</p>
                        <p style="margin: 5px 0;"><strong>类别:</strong> {rec.category}</p>
                    </div>
                    <div>
                        <h5 style="margin: 10px 0 5px 0;">行动项目:</h5>
                        <ul style="margin: 0; padding-left: 20px;">{action_items_html}</ul>
                    </div>
                </div>
                {f'<h5 style="margin: 15px 0 5px 0;">相关资源:</h5><ul style="margin: 0; padding-left: 20px;">{resources_html}</ul>' if rec.resources else ''}
                {f'<h5 style="margin: 15px 0 5px 0;">成功指标:</h5><ul style="margin: 0; padding-left: 20px;">{success_metrics_html}</ul>' if rec.success_metrics else ''}
            </div>
            """
        
        # 构建路线图HTML
        roadmap_html = ""
        for i, phase in enumerate(intelligent_recommendations.roadmap.phases, 1):
            phase_recommendations_html = "".join([
                f"<li>{rec.title} (优先级: {rec.priority_score:.1f})</li>" 
                for rec in phase.recommendations
            ])
            
            roadmap_html += f"""
            <div class="roadmap-phase" style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%); border-radius: 12px; border: 1px solid #e9ecef;">
                <h3 style="color: #2c3e50; margin: 0 0 15px 0;">阶段 {i}: {phase.name}</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 15px;">
                    <div>
                        <p><strong>持续时间:</strong> {phase.duration_weeks} 周</p>
                        <p><strong>包含建议:</strong> {len(phase.recommendations)} 条</p>
                    </div>
                    <div>
                        <p><strong>理由:</strong> {phase.rationale}</p>
                    </div>
                </div>
                <h5>阶段建议:</h5>
                <ul style="padding-left: 20px;">{phase_recommendations_html}</ul>
                {f'<h5>前置条件:</h5><ul style="padding-left: 20px;">{"".join([f"<li>{prereq}</li>" for prereq in phase.prerequisites])}</ul>' if phase.prerequisites else ''}
                {f'<h5>成功标准:</h5><ul style="padding-left: 20px;">{"".join([f"<li>{criteria}</li>" for criteria in phase.success_criteria])}</ul>' if phase.success_criteria else ''}
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{project_info.name} - 智能推荐报告</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 40px 30px; }}
                .content {{ padding: 40px; }}
                .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #e9ecef; }}
                .summary-card h4 {{ margin: 0 0 10px 0; color: #495057; }}
                .summary-card .value {{ font-size: 1.8em; font-weight: bold; color: #27ae60; }}
                .back-link {{ display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: #27ae60; color: white; text-decoration: none; border-radius: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{project_info.name} - 智能推荐报告</h1>
                    <p>基于智能分析生成的改进建议和路线图</p>
                </div>
                <div class="content">
                    <a href="{project_info.name}_audit_report.html" class="back-link">← 返回主报告</a>
                    
                    <h2>推荐摘要</h2>
                    <div class="summary-grid">
                        <div class="summary-card">
                            <h4>总推荐数</h4>
                            <div class="value">{len(intelligent_recommendations.recommendations)}</div>
                        </div>
                        <div class="summary-card">
                            <h4>路线图阶段</h4>
                            <div class="value">{len(intelligent_recommendations.roadmap.phases)}</div>
                        </div>
                        <div class="summary-card">
                            <h4>预估ROI</h4>
                            <div class="value">{intelligent_recommendations.roadmap.estimated_roi:.1f}%</div>
                        </div>
                        <div class="summary-card">
                            <h4>信心度</h4>
                            <div class="value">{intelligent_recommendations.confidence_level:.2f}</div>
                        </div>
                    </div>
                    
                    <h2>具体推荐建议</h2>
                    {recommendations_html}
                    
                    <h2>改进路线图</h2>
                    <p style="color: #6c757d; margin: 15px 0;">总持续时间: <strong>{intelligent_recommendations.roadmap.total_duration_weeks} 周</strong></p>
                    {roadmap_html}
                    
                    <h2>成功指标</h2>
                    <div style="background: #d1ecf1; padding: 20px; border-radius: 8px; border-left: 4px solid #17a2b8;">
                        <ul>
                            {"".join([f"<li>{metric}</li>" for metric in intelligent_recommendations.success_metrics])}
                        </ul>
                    </div>
                    
                    <h2>影响预测</h2>
                    <div style="background: #d4edda; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
                        {"".join([f"<p><strong>{key}:</strong> {value}</p>" for key, value in intelligent_recommendations.impact_predictions.items()])}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"智能推荐报告已生成: {report_file}")
        return str(report_file)
    
    def _generate_dimension_reports(self, audit_report: AuditReport, 
                                  output_path: pathlib.Path) -> List[str]:
        """生成各维度详细报告 - 使用新的维度分析器"""
        dimension_reports = []
        
        # 创建维度报告目录
        dimensions_dir = output_path / "dimensions"
        dimensions_dir.mkdir(exist_ok=True)
        
        # 初始化维度分析器
        try:
            from .dimension_analyzer import create_dimension_analyzer, AnalysisLevel
            dimension_analyzer = create_dimension_analyzer(AnalysisLevel.AI_POWERED)
            logger.info("使用AI增强维度分析器")
        except ImportError:
            from .dimension_analyzer import create_dimension_analyzer, AnalysisLevel
            dimension_analyzer = create_dimension_analyzer(AnalysisLevel.ENHANCED)
            logger.info("使用增强维度分析器")
        
        # 为每个维度生成详细分析
        for dimension in audit_report.dimensions:
            try:
                # 使用维度分析器重新分析
                detailed_analysis = dimension_analyzer.analyze_dimension(
                    dimension.dimension_id,
                    audit_report.tool_results,
                    audit_report.project_info
                )
                
                # 清理文件名中的特殊字符
                clean_name = dimension.dimension_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
                report_file = dimensions_dir / f"dimension_{dimension.dimension_id}_{clean_name}.json"
                
                # 生成结构化的维度报告 - 使用主页面的分数确保一致性
                dimension_data = {
                    'dimension_info': {
                        'dimension_id': dimension.dimension_id,
                        'dimension_name': dimension.dimension_name,
                        'score': dimension.score,  # 使用主页面的分数
                        'status': dimension.status,  # 使用主页面的状态
                        'analysis_level': detailed_analysis.analysis_level.value,
                        'analysis_timestamp': detailed_analysis.analysis_timestamp.isoformat(),
                        'analysis_duration': detailed_analysis.analysis_duration
                    },
                    'analysis_summary': {
                        'summary': detailed_analysis.summary,
                        'key_findings': detailed_analysis.key_findings,
                        'ai_analysis': detailed_analysis.ai_analysis,
                        'ai_recommendations': detailed_analysis.ai_recommendations
                    },
                    'metrics': asdict(detailed_analysis.metrics),
                    'issues': [
                        {
                            'issue_id': issue.issue_id,
                            'title': issue.title,
                            'description': issue.description,
                            'severity': issue.severity,
                            'category': issue.category,
                            'file_path': issue.file_path,
                            'line_number': issue.line_number,
                            'tool_source': issue.tool_source,
                            'recommendation': issue.recommendation
                        }
                        for issue in detailed_analysis.issues
                    ],
                    'insights': [
                        {
                            'insight_type': insight.insight_type,
                            'title': insight.title,
                            'description': insight.description,
                            'impact': insight.impact,
                            'suggestions': insight.suggestions
                        }
                        for insight in detailed_analysis.insights
                    ],
                    'tools_analysis': {
                        'tools_used': dimension.tools_used,  # 使用与主页面一致的工具列表
                        'tool_results_summary': {
                            name: result.to_dict() 
                            for name, result in audit_report.tool_results.items() 
                            if name in dimension.tools_used  # 只包含维度实际使用的工具结果
                        }
                    },
                    'project_context': {
                        'project_name': audit_report.project_info.name,
                        'primary_language': audit_report.project_info.get_primary_language(),
                        'project_type': str(audit_report.project_info.project_type),
                        'size_category': audit_report.project_info.size_metrics.get_size_category()
                    }
                }
                
                # 只生成HTML维度报告
                try:
                    html_report_file = report_file.with_suffix('.html')
                    html_content = self.dimension_html_generator.generate_dimension_html(dimension_data)
                    with open(html_report_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logger.debug(f"生成维度 {dimension.dimension_id} HTML报告: {html_report_file}")
                except Exception as e:
                    logger.warning(f"生成维度 {dimension.dimension_id} HTML报告失败: {e}")
                    # 如果HTML生成失败，作为备用方案保存JSON
                    with open(report_file, 'w', encoding='utf-8') as f:
                        json.dump(dimension_data, f, indent=2, ensure_ascii=False)
                
                dimension_reports.append(str(report_file))
                logger.debug(f"维度 {dimension.dimension_id} 详细分析完成，得分: {detailed_analysis.score:.1f}")
                
            except Exception as e:
                logger.error(f"生成维度 {dimension.dimension_id} 详细报告失败: {e}")
                # 回退到原始方式
                clean_name = dimension.dimension_name.replace('/', '_').replace('\\', '_')
                report_file = dimensions_dir / f"dimension_{dimension.dimension_id}_{clean_name}.json"
                
                dimension_data = {
                    'dimension_info': asdict(dimension),
                    'project_name': audit_report.project_info.name,
                    'timestamp': audit_report.timestamp,
                    'error': f"维度分析失败: {str(e)}",
                    'related_tools': {
                        name: result.to_dict() 
                        for name, result in audit_report.tool_results.items() 
                        if name in dimension.tools_used
                    }
                }
                
                # 尝试生成HTML报告（即使是回退情况）
                try:
                    html_report_file = report_file.with_suffix('.html')
                    html_content = self.dimension_html_generator.generate_dimension_html(dimension_data)
                    with open(html_report_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logger.debug(f"生成维度 {dimension.dimension_id} HTML报告 (回退): {html_report_file}")
                except Exception as e:
                    logger.warning(f"生成维度 {dimension.dimension_id} HTML报告失败 (回退): {e}")
                    # HTML生成失败时才保存JSON作为备用
                    with open(report_file, 'w', encoding='utf-8') as f:
                        json.dump(dimension_data, f, indent=2, ensure_ascii=False)
                
                dimension_reports.append(str(report_file))
        
        logger.info(f"生成了 {len(dimension_reports)} 个维度详细报告")
        return dimension_reports
    
    def _infer_tool_language(self, tool_name: str, project_info: ProjectInfo) -> str:
        """根据工具名称推测工具语言"""
        language_mapping = {
            'pylint': 'python', 'flake8': 'python', 'mypy': 'python', 'bandit': 'python',
            'safety': 'python', 'black': 'python', 'isort': 'python', 'pytest': 'python',
            'coverage': 'python', 'eslint': 'javascript', 'prettier': 'javascript',
            'jest': 'javascript', 'npm-audit': 'javascript', 'tsc': 'javascript',
            'tslint': 'javascript', 'checkstyle': 'java', 'pmd': 'java', 'spotbugs': 'java',
            'maven': 'java', 'gradle': 'java', 'junit': 'java', 'gofmt': 'go',
            'go-vet': 'go', 'golint': 'go', 'gosec': 'go', 'staticcheck': 'go',
            'rustfmt': 'rust', 'clippy': 'rust', 'cargo-audit': 'rust',
            'semgrep': 'universal', 'gitleaks': 'universal', 'trivy': 'universal',
            'sonarqube-scanner': 'universal', 'syft': 'universal'
        }
        return language_mapping.get(tool_name, 'universal')
    
    def _infer_tool_priority(self, tool_name: str) -> int:
        """根据工具名称推测工具优先级（1=最高，10=最低）"""
        priority_mapping = {
            'pylint': 2, 'eslint': 2, 'semgrep': 1, 'sonarqube-scanner': 1,
            'gitleaks': 1, 'bandit': 2, 'flake8': 3, 'mypy': 3, 'prettier': 4,
            'black': 4, 'safety': 3, 'npm-audit': 3, 'isort': 5, 'coverage': 4,
            'pytest': 3, 'jest': 3
        }
        return priority_mapping.get(tool_name, 5)
    
    def _infer_tool_category(self, tool_name: str) -> str:
        """根据工具名称推测工具分类"""
        category_mapping = {
            'pylint': 'quality', 'eslint': 'quality', 'flake8': 'quality',
            'mypy': 'typing', 'checkstyle': 'quality', 'pmd': 'quality',
            'bandit': 'security', 'safety': 'security', 'semgrep': 'security',
            'gitleaks': 'security', 'gosec': 'security', 'npm-audit': 'security',
            'trivy': 'security', 'pytest': 'testing', 'jest': 'testing',
            'junit': 'testing', 'coverage': 'coverage', 'black': 'format',
            'prettier': 'format', 'rustfmt': 'format', 'gofmt': 'format',
            'isort': 'format'
        }
        return category_mapping.get(tool_name, 'quality')
    
    def _generate_tool_reports(self, audit_report: AuditReport, output_path: pathlib.Path) -> List[str]:
        """生成各工具结果报告"""
        tool_reports = []
        
        # 创建工具报告目录
        tools_dir = output_path / "tools"
        tools_dir.mkdir(exist_ok=True)
        
        # 为每个工具生成详细报告
        for tool_name, tool_result in audit_report.tool_results.items():
            try:
                report_file = tools_dir / f"{tool_name}_report.html"
                
                # 生成工具报告HTML
                html_content = self._build_tool_report_html(tool_name, tool_result, audit_report.project_info)
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                    
                tool_reports.append(str(report_file))
                logger.debug(f"生成工具报告: {tool_name} -> {report_file}")
                
            except Exception as e:
                logger.warning(f"生成工具 {tool_name} 报告失败: {e}")
        
        logger.info(f"生成了 {len(tool_reports)} 个工具报告")
        return tool_reports
    
    def _build_tool_report_html(self, tool_name: str, tool_result, project_info) -> str:
        """构建工具报告HTML内容"""
        
        # 状态信息
        status_color = "#28a745" if tool_result.success else "#dc3545"
        status_text = "成功" if tool_result.success else "失败"
        
        # 工具结果信息 - 优先展示友好格式
        result_info = ""
        if tool_result.result:
            result_data = tool_result.result
            result_info = self._format_tool_result_display(tool_name, result_data)
        
        # 错误信息
        error_info = ""
        if not tool_result.success and tool_result.error:
            error_info = f"""
            <h3>错误信息</h3>
            <div style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; border-left: 4px solid #dc3545;">
                <pre>{tool_result.error}</pre>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{tool_name} - 工具执行报告</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    min-height: 100vh;
                    color: #212529;
                    line-height: 1.6;
                }}
                .container {{ 
                    max-width: 1000px; 
                    margin: 0 auto; 
                    background: white; 
                    border-radius: 16px; 
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1), 0 4px 8px rgba(0,0,0,0.05); 
                    border: 1px solid rgba(255,255,255,0.8);
                    overflow: hidden;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
                    color: white; 
                    padding: 40px 30px; 
                    position: relative;
                }}
                .header::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: linear-gradient(135deg, rgba(39,174,96,0.1) 0%, rgba(46,204,113,0.1) 100%);
                }}
                .header h1, .header p {{ position: relative; z-index: 1; }}
                .content {{ padding: 40px; }}
                .status-badge {{ 
                    padding: 10px 18px; 
                    border-radius: 25px; 
                    color: white; 
                    font-weight: 600; 
                    display: inline-block; 
                    font-size: 0.9em;
                    letter-spacing: 0.5px;
                    text-transform: uppercase;
                }}
                .info-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
                    gap: 24px; 
                    margin: 30px 0; 
                }}
                .info-card {{ 
                    background: linear-gradient(135deg, #fff 0%, #fcfcfc 100%); 
                    padding: 24px; 
                    border-radius: 16px; 
                    border: 1px solid rgba(233,236,239,0.8);
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                    overflow: hidden;
                }}
                .info-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
                    opacity: 0;
                    transition: opacity 0.3s ease;
                }}
                .info-card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 8px 16px rgba(0,0,0,0.08);
                    border-color: rgba(39,174,96,0.3);
                }}
                .info-card:hover::before {{
                    opacity: 1;
                }}
                .info-card h4 {{ 
                    margin: 0 0 12px 0; 
                    color: #2c3e50; 
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    font-weight: 600;
                }}
                .info-card .value {{ 
                    font-size: 1.4em; 
                    font-weight: 700; 
                    color: #27ae60;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .back-link {{ 
                    display: inline-block; 
                    margin-bottom: 25px; 
                    padding: 12px 24px; 
                    background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 25px; 
                    font-weight: 600;
                    font-size: 0.9em;
                    letter-spacing: 0.5px;
                    transition: all 0.3s ease;
                }}
                .back-link:hover {{ 
                    background: linear-gradient(135deg, #1e8449 0%, #27ae60 100%);
                    transform: translateY(-2px);
                    box-shadow: 0 8px 16px rgba(39,174,96,0.3);
                }}
                pre {{ 
                    overflow-x: auto; 
                    white-space: pre-wrap; 
                    word-wrap: break-word; 
                    background: #2d3748;
                    color: #e2e8f0;
                    padding: 20px;
                    border-radius: 12px;
                    font-family: 'SFMono-Regular', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{tool_name} - 工具执行报告</h1>
                    <p>项目: {project_info.name}</p>
                    <span class="status-badge" style="background-color: {status_color};">执行{status_text}</span>
                </div>
                
                <div class="content">
                    <a href="../{project_info.name}_audit_report.html" class="back-link">← 返回主报告</a>
                    
                    <h2>执行信息</h2>
                    <div class="info-grid">
                        <div class="info-card">
                            <h4>工具名称</h4>
                            <div class="value">{tool_name}</div>
                        </div>
                        <div class="info-card">
                            <h4>执行状态</h4>
                            <div class="value" style="color: {status_color};">{status_text}</div>
                        </div>
                        <div class="info-card">
                            <h4>执行时间</h4>
                            <div class="value">{tool_result.execution_time:.2f}s</div>
                        </div>
                        <div class="info-card">
                            <h4>退出码</h4>
                            <div class="value">{tool_result.return_code}</div>
                        </div>
                    </div>
                    
                    {result_info}
                    {error_info}
                    
                    <h3>命令行输出</h3>
                    <div style="background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 5px; font-family: monospace;">
                        <pre>{tool_result.stdout if hasattr(tool_result, 'stdout') and tool_result.stdout else '无输出'}</pre>
                    </div>
                    
                    {"<h3>错误输出</h3><div style='background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 5px; font-family: monospace;'><pre>" + str(tool_result.stderr) + "</pre></div>" if hasattr(tool_result, 'stderr') and tool_result.stderr else ""}
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _format_tool_result_display(self, tool_name: str, result_data: Any) -> str:
        """
        智能格式化工具结果显示
        优先选择友好可读的格式，如HTML表格、图表等
        回退到原始数据展示
        """
        if not result_data:
            return "<p>工具执行成功但无结果数据</p>"
        
        # 1. 安全工具结果格式化
        if tool_name in ['bandit', 'safety', 'semgrep', 'gitleaks', 'gosec']:
            return self._format_security_tool_result(tool_name, result_data)
        
        # 2. 代码质量工具结果格式化
        elif tool_name in ['pylint', 'flake8', 'eslint', 'checkstyle']:
            return self._format_quality_tool_result(tool_name, result_data)
        
        # 3. 测试工具结果格式化
        elif tool_name in ['pytest', 'jest', 'junit', 'coverage']:
            return self._format_test_tool_result(tool_name, result_data)
        
        # 4. 依赖工具结果格式化
        elif tool_name in ['npm-audit', 'trivy', 'syft', 'cargo-audit']:
            return self._format_dependency_tool_result(tool_name, result_data)
        
        # 5. 格式化工具结果
        elif tool_name in ['black', 'prettier', 'rustfmt', 'isort']:
            return self._format_formatting_tool_result(tool_name, result_data)
        
        # 6. 默认原始数据展示
        else:
            return self._format_raw_data_result(result_data)
    
    def _format_security_tool_result(self, tool_name: str, result_data: Any) -> str:
        """格式化安全工具结果"""
        if isinstance(result_data, dict):
            # 如果有issues_count等结构化数据，生成表格
            if 'issues_count' in result_data or 'vulnerabilities' in result_data:
                return self._create_security_summary_table(tool_name, result_data)
            # 如果有详细的issues列表，生成问题列表
            elif 'issues' in result_data and isinstance(result_data['issues'], list):
                return self._create_issues_list(tool_name, result_data['issues'])
        
        return self._format_raw_data_result(result_data)
    
    def _format_quality_tool_result(self, tool_name: str, result_data: Any) -> str:
        """格式化代码质量工具结果"""
        if isinstance(result_data, dict):
            # 创建代码质量摘要
            if 'score' in result_data or 'issues_count' in result_data:
                return self._create_quality_summary_table(tool_name, result_data)
        
        return self._format_raw_data_result(result_data)
    
    def _format_test_tool_result(self, tool_name: str, result_data: Any) -> str:
        """格式化测试工具结果"""
        if isinstance(result_data, dict):
            if tool_name == 'coverage' and 'percentage' in result_data:
                return self._create_coverage_display(result_data)
            elif 'tests_run' in result_data or 'passed' in result_data:
                return self._create_test_summary_table(tool_name, result_data)
        
        return self._format_raw_data_result(result_data)
    
    def _format_dependency_tool_result(self, tool_name: str, result_data: Any) -> str:
        """格式化依赖工具结果"""
        if isinstance(result_data, dict):
            if 'vulnerabilities' in result_data or 'packages' in result_data:
                return self._create_dependency_summary_table(tool_name, result_data)
        
        return self._format_raw_data_result(result_data)
    
    def _format_formatting_tool_result(self, tool_name: str, result_data: Any) -> str:
        """格式化代码格式化工具结果"""
        if isinstance(result_data, dict):
            if 'files_formatted' in result_data or 'changes_made' in result_data:
                return self._create_formatting_summary_table(tool_name, result_data)
        
        return self._format_raw_data_result(result_data)
    
    def _create_security_summary_table(self, tool_name: str, data: dict) -> str:
        """创建安全工具摘要表格"""
        issues_count = data.get('issues_count', 0)
        by_severity = data.get('by_severity', {})
        
        severity_rows = ""
        for severity, count in by_severity.items():
            color = {'HIGH': '#dc3545', 'MEDIUM': '#ffc107', 'LOW': '#28a745'}.get(severity, '#6c757d')
            severity_rows += f"""
            <tr>
                <td><span style="color: {color}; font-weight: bold;">{severity}</span></td>
                <td>{count}</td>
            </tr>
            """
        
        return f"""
        <h3>安全扫描结果摘要</h3>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 15px;">
                <div style="text-align: center;">
                    <h4 style="margin: 0; color: #495057;">总问题数</h4>
                    <div style="font-size: 2em; font-weight: bold; color: {'#dc3545' if issues_count > 0 else '#28a745'};">{issues_count}</div>
                </div>
                <div style="text-align: center;">
                    <h4 style="margin: 0; color: #495057;">工具</h4>
                    <div style="font-size: 1.5em; font-weight: bold; color: #27ae60;">{tool_name}</div>
                </div>
            </div>
            {f'''
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <thead>
                    <tr style="background: #e9ecef;">
                        <th style="padding: 8px; text-align: left; border-bottom: 1px solid #dee2e6;">严重程度</th>
                        <th style="padding: 8px; text-align: left; border-bottom: 1px solid #dee2e6;">数量</th>
                    </tr>
                </thead>
                <tbody>
                    {severity_rows}
                </tbody>
            </table>
            ''' if by_severity else ''}
        </div>
        {self._format_raw_data_result(data, show_title=False)}
        """
    
    def _create_quality_summary_table(self, tool_name: str, data: dict) -> str:
        """创建代码质量摘要表格"""
        score = data.get('score', 'N/A')
        issues_count = data.get('issues_count', 0)
        
        return f"""
        <h3>代码质量分析结果</h3>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; text-align: center;">
                <div>
                    <h4 style="margin: 0; color: #495057;">质量得分</h4>
                    <div style="font-size: 2em; font-weight: bold; color: #27ae60;">{score}</div>
                </div>
                <div>
                    <h4 style="margin: 0; color: #495057;">问题数量</h4>
                    <div style="font-size: 2em; font-weight: bold; color: {'#dc3545' if issues_count > 0 else '#28a745'};">{issues_count}</div>
                </div>
                <div>
                    <h4 style="margin: 0; color: #495057;">分析工具</h4>
                    <div style="font-size: 1.5em; font-weight: bold; color: #27ae60;">{tool_name}</div>
                </div>
            </div>
        </div>
        {self._format_raw_data_result(data, show_title=False)}
        """
    
    def _create_coverage_display(self, data: dict) -> str:
        """创建覆盖率显示"""
        percentage = data.get('percentage', 0)
        covered_lines = data.get('covered_lines', 0)
        total_lines = data.get('total_lines', 0)
        
        color = '#28a745' if percentage >= 80 else '#ffc107' if percentage >= 60 else '#dc3545'
        
        return f"""
        <h3>测试覆盖率报告</h3>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 3em; font-weight: bold; color: {color};">{percentage}%</div>
                <div style="color: #495057;">测试覆盖率</div>
            </div>
            <div style="background: #e9ecef; height: 10px; border-radius: 5px; overflow: hidden;">
                <div style="background: {color}; height: 100%; width: {percentage}%; transition: width 0.3s;"></div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; text-align: center;">
                <div>
                    <h5 style="margin: 0; color: #495057;">已覆盖行数</h5>
                    <div style="font-size: 1.5em; font-weight: bold; color: #28a745;">{covered_lines:,}</div>
                </div>
                <div>
                    <h5 style="margin: 0; color: #495057;">总行数</h5>
                    <div style="font-size: 1.5em; font-weight: bold; color: #27ae60;">{total_lines:,}</div>
                </div>
            </div>
        </div>
        {self._format_raw_data_result(data, show_title=False)}
        """
    
    def _create_test_summary_table(self, tool_name: str, data: dict) -> str:
        """创建测试摘要表格"""
        tests_run = data.get('tests_run', 0)
        passed = data.get('passed', 0)
        failed = data.get('failed', 0)
        
        return f"""
        <h3>测试执行结果</h3>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px; text-align: center;">
                <div>
                    <h4 style="margin: 0; color: #495057;">总测试数</h4>
                    <div style="font-size: 2em; font-weight: bold; color: #27ae60;">{tests_run}</div>
                </div>
                <div>
                    <h4 style="margin: 0; color: #495057;">通过</h4>
                    <div style="font-size: 2em; font-weight: bold; color: #28a745;">{passed}</div>
                </div>
                <div>
                    <h4 style="margin: 0; color: #495057;">失败</h4>
                    <div style="font-size: 2em; font-weight: bold; color: #dc3545;">{failed}</div>
                </div>
                <div>
                    <h4 style="margin: 0; color: #495057;">测试工具</h4>
                    <div style="font-size: 1.5em; font-weight: bold; color: #27ae60;">{tool_name}</div>
                </div>
            </div>
        </div>
        {self._format_raw_data_result(data, show_title=False)}
        """
    
    def _create_dependency_summary_table(self, tool_name: str, data: dict) -> str:
        """创建依赖分析摘要表格"""
        vulnerabilities = data.get('vulnerabilities', 0)
        packages_scanned = data.get('packages_scanned', data.get('packages', 0))
        
        return f"""
        <h3>依赖安全分析结果</h3>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; text-align: center;">
                <div>
                    <h4 style="margin: 0; color: #495057;">扫描包数量</h4>
                    <div style="font-size: 2em; font-weight: bold; color: #27ae60;">{packages_scanned}</div>
                </div>
                <div>
                    <h4 style="margin: 0; color: #495057;">发现漏洞</h4>
                    <div style="font-size: 2em; font-weight: bold; color: {'#dc3545' if vulnerabilities > 0 else '#28a745'};">{vulnerabilities}</div>
                </div>
                <div>
                    <h4 style="margin: 0; color: #495057;">分析工具</h4>
                    <div style="font-size: 1.5em; font-weight: bold; color: #27ae60;">{tool_name}</div>
                </div>
            </div>
        </div>
        {self._format_raw_data_result(data, show_title=False)}
        """
    
    def _create_formatting_summary_table(self, tool_name: str, data: dict) -> str:
        """创建格式化工具摘要表格"""
        files_formatted = data.get('files_formatted', 0)
        changes_made = data.get('changes_made', data.get('files_changed', 0))
        
        return f"""
        <h3>代码格式化结果</h3>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; text-align: center;">
                <div>
                    <h4 style="margin: 0; color: #495057;">处理文件数</h4>
                    <div style="font-size: 2em; font-weight: bold; color: #27ae60;">{files_formatted}</div>
                </div>
                <div>
                    <h4 style="margin: 0; color: #495057;">修改文件数</h4>
                    <div style="font-size: 2em; font-weight: bold; color: {'#ffc107' if changes_made > 0 else '#28a745'};">{changes_made}</div>
                </div>
                <div>
                    <h4 style="margin: 0; color: #495057;">格式化工具</h4>
                    <div style="font-size: 1.5em; font-weight: bold; color: #27ae60;">{tool_name}</div>
                </div>
            </div>
        </div>
        {self._format_raw_data_result(data, show_title=False)}
        """
    
    def _create_issues_list(self, tool_name: str, issues: list) -> str:
        """创建问题列表显示"""
        if not issues:
            return "<p>未发现问题</p>"
        
        issues_html = ""
        for i, issue in enumerate(issues[:10]):  # 限制显示前10个问题
            severity = issue.get('severity', 'UNKNOWN')
            title = issue.get('title', issue.get('description', 'Unknown Issue'))
            file_path = issue.get('file', issue.get('filename', 'Unknown File'))
            line = issue.get('line', issue.get('line_number', '?'))
            
            severity_color = {'HIGH': '#dc3545', 'MEDIUM': '#ffc107', 'LOW': '#28a745'}.get(severity, '#6c757d')
            
            issues_html += f"""
            <div style="border-left: 4px solid {severity_color}; padding: 15px; margin: 10px 0; background: #f8f9fa;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h5 style="margin: 0; color: #495057;">问题 #{i+1}</h5>
                    <span style="background: {severity_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">{severity}</span>
                </div>
                <p style="margin: 10px 0; font-weight: bold;">{title}</p>
                <p style="margin: 5px 0; color: #6c757d; font-size: 0.9em;">
                    <strong>文件:</strong> {file_path}:{line}
                </p>
            </div>
            """
        
        if len(issues) > 10:
            issues_html += f"<p style='text-align: center; color: #6c757d; font-style: italic;'>... 还有 {len(issues) - 10} 个问题未显示</p>"
        
        return f"""
        <h3>发现的问题 (共 {len(issues)} 个)</h3>
        {issues_html}
        <div style="margin-top: 20px;">
            <h4>完整原始数据:</h4>
            {self._format_raw_data_result(issues, show_title=False)}
        </div>
        """
    
    def _format_raw_data_result(self, result_data: Any, show_title: bool = True) -> str:
        """格式化原始数据结果"""
        title_html = "<h3>原始检测数据</h3>" if show_title else ""
        
        if isinstance(result_data, dict) or isinstance(result_data, list):
            return f"""
            {title_html}
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace;">
                <pre>{json.dumps(result_data, indent=2, ensure_ascii=False)}</pre>
            </div>
            """
        else:
            return f"""
            {title_html}
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace;">
                <pre>{str(result_data)}</pre>
            </div>
            """