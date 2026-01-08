#!/usr/bin/env python3
"""
Plugin Result Validator - 插件结果格式验证器
确保所有插件产生统一格式的分析结果
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import logging

from .base import PluginResult, PluginError

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """验证错误"""
    field: str
    message: str
    severity: str = "warning"  # warning, error


class PluginResultValidator:
    """插件结果验证器"""
    
    # 标准化的严重性级别
    STANDARD_SEVERITIES = {'low', 'medium', 'high', 'critical', 'info', 'warning', 'error'}
    
    # 标准化的工具状态
    STANDARD_STATUSES = {'completed', 'failed', 'timeout', 'skipped'}
    
    def __init__(self):
        self.validation_errors: List[ValidationError] = []
    
    def validate_plugin_result(self, result: PluginResult) -> List[ValidationError]:
        """验证插件结果格式"""
        self.validation_errors = []
        
        # 验证基本字段
        self._validate_basic_fields(result)
        
        # 验证工具结果
        self._validate_tool_results(result)
        
        # 验证质量分数
        self._validate_quality_score(result)
        
        # 验证错误列表
        self._validate_errors(result)
        
        # 验证插件特定数据
        self._validate_plugin_data(result)
        
        return self.validation_errors
    
    def _validate_basic_fields(self, result: PluginResult):
        """验证基本字段"""
        # 检查必需字段
        if not result.plugin_name:
            self._add_error("plugin_name", "Plugin name is required", "error")
        
        if not result.language:
            self._add_error("language", "Language is required", "error")
        
        # 验证执行时间
        if result.execution_time < 0:
            self._add_error("execution_time", "Execution time cannot be negative", "error")
        
        # 验证问题计数
        if result.issues_found < 0:
            self._add_error("issues_found", "Issues count cannot be negative", "error")
    
    def _validate_tool_results(self, result: PluginResult):
        """验证工具结果"""
        for tool_name, tool_result in result.tool_results.items():
            # 验证工具结果基本字段
            if not tool_result.tool_name:
                self._add_error(f"tool_results.{tool_name}.tool_name", 
                              "Tool name is required", "error")
            
            if tool_result.status not in self.STANDARD_STATUSES:
                self._add_error(f"tool_results.{tool_name}.status",
                              f"Invalid status: {tool_result.status}. Must be one of {self.STANDARD_STATUSES}",
                              "warning")
            
            if tool_result.execution_time < 0:
                self._add_error(f"tool_results.{tool_name}.execution_time",
                              "Execution time cannot be negative", "error")
            
            # 验证工具结果内容
            if tool_result.result:
                self._validate_tool_result_content(tool_name, tool_result.result)
    
    def _validate_tool_result_content(self, tool_name: str, result_content: Dict[str, Any]):
        """验证工具结果内容"""
        # 标准化字段验证
        required_fields = {'issues', 'issues_count', 'score'}
        for field in required_fields:
            if field not in result_content:
                self._add_error(f"tool_results.{tool_name}.result.{field}",
                              f"Required field '{field}' is missing", "warning")
        
        # 验证分数范围
        if 'score' in result_content:
            score = result_content['score']
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                self._add_error(f"tool_results.{tool_name}.result.score",
                              "Score must be a number between 0 and 100", "error")
        
        # 验证问题计数
        if 'issues_count' in result_content:
            count = result_content['issues_count']
            if not isinstance(count, int) or count < 0:
                self._add_error(f"tool_results.{tool_name}.result.issues_count",
                              "Issues count must be a non-negative integer", "error")
        
        # 验证问题列表
        if 'issues' in result_content:
            issues = result_content['issues']
            if not isinstance(issues, list):
                self._add_error(f"tool_results.{tool_name}.result.issues",
                              "Issues must be a list", "error")
            else:
                self._validate_issues_list(tool_name, issues)
        
        # 验证严重性分组（如果存在）
        if 'by_severity' in result_content:
            self._validate_severity_grouping(tool_name, result_content['by_severity'])
    
    def _validate_issues_list(self, tool_name: str, issues: List[Dict[str, Any]]):
        """验证问题列表"""
        for i, issue in enumerate(issues):
            if not isinstance(issue, dict):
                self._add_error(f"tool_results.{tool_name}.result.issues[{i}]",
                              "Each issue must be a dictionary", "error")
                continue
            
            # 验证问题字段
            if 'message' not in issue:
                self._add_error(f"tool_results.{tool_name}.result.issues[{i}].message",
                              "Issue message is required", "warning")
            
            # 标准化严重性级别
            if 'severity' in issue:
                severity = issue['severity'].lower()
                if severity not in self.STANDARD_SEVERITIES:
                    self._add_error(f"tool_results.{tool_name}.result.issues[{i}].severity",
                                  f"Non-standard severity: {severity}. "
                                  f"Consider using: {', '.join(sorted(self.STANDARD_SEVERITIES))}",
                                  "warning")
    
    def _validate_severity_grouping(self, tool_name: str, severity_groups: Dict[str, int]):
        """验证严重性分组"""
        if not isinstance(severity_groups, dict):
            self._add_error(f"tool_results.{tool_name}.result.by_severity",
                          "Severity grouping must be a dictionary", "error")
            return
        
        standard_groups = {'HIGH', 'MEDIUM', 'LOW'}
        for severity, count in severity_groups.items():
            if severity not in standard_groups:
                self._add_error(f"tool_results.{tool_name}.result.by_severity.{severity}",
                              f"Non-standard severity group: {severity}. "
                              f"Standard groups are: {', '.join(standard_groups)}",
                              "warning")
            
            if not isinstance(count, int) or count < 0:
                self._add_error(f"tool_results.{tool_name}.result.by_severity.{severity}",
                              "Severity count must be a non-negative integer", "error")
    
    def _validate_quality_score(self, result: PluginResult):
        """验证质量分数"""
        if not isinstance(result.quality_score, (int, float)):
            self._add_error("quality_score", "Quality score must be a number", "error")
        elif result.quality_score < 0 or result.quality_score > 100:
            self._add_error("quality_score", "Quality score must be between 0 and 100", "error")
    
    def _validate_errors(self, result: PluginResult):
        """验证错误列表"""
        if not isinstance(result.errors, list):
            self._add_error("errors", "Errors must be a list", "error")
            return
        
        for i, error in enumerate(result.errors):
            if not isinstance(error, PluginError):
                self._add_error(f"errors[{i}]", "Each error must be a PluginError instance", "error")
    
    def _validate_plugin_data(self, result: PluginResult):
        """验证插件特定数据"""
        if not isinstance(result.plugin_data, dict):
            self._add_error("plugin_data", "Plugin data must be a dictionary", "error")
    
    def _add_error(self, field: str, message: str, severity: str = "warning"):
        """添加验证错误"""
        self.validation_errors.append(ValidationError(
            field=field,
            message=message,
            severity=severity
        ))


class ResultStandardizer:
    """结果标准化器 - 将插件结果标准化为统一格式"""
    
    @staticmethod
    def standardize_plugin_result(result: PluginResult) -> PluginResult:
        """标准化插件结果"""
        # 标准化工具结果
        for tool_name, tool_result in result.tool_results.items():
            if tool_result.result:
                ResultStandardizer._standardize_tool_result(tool_result.result)
        
        # 确保质量分数在有效范围内
        result.quality_score = max(0, min(100, result.quality_score))
        
        # 确保问题计数非负
        result.issues_found = max(0, result.issues_found)
        
        return result
    
    @staticmethod
    def _standardize_tool_result(result_content: Dict[str, Any]):
        """标准化工具结果内容"""
        # 确保必需字段存在
        if 'issues' not in result_content:
            result_content['issues'] = []
        
        # 确保问题列表是有效的
        issues = result_content['issues']
        if not isinstance(issues, list):
            result_content['issues'] = []
            issues = []
        
        # 标准化问题计数（确保非负值）
        if 'issues_count' not in result_content or result_content['issues_count'] < 0:
            result_content['issues_count'] = len(issues)
        
        if 'score' not in result_content:
            result_content['score'] = 100 if result_content['issues_count'] == 0 else 70
        
        # 标准化分数
        result_content['score'] = max(0, min(100, result_content['score']))
        
        # 标准化问题列表中的每个问题
        for issue in issues:
            if isinstance(issue, dict):
                ResultStandardizer._standardize_issue(issue)
        
        # 标准化严重性分组
        if 'by_severity' in result_content:
            ResultStandardizer._standardize_severity_grouping(result_content['by_severity'])
    
    @staticmethod
    def _standardize_issue(issue: Dict[str, Any]):
        """标准化单个问题"""
        # 标准化严重性级别
        if 'severity' in issue:
            severity = issue['severity'].lower()
            # 映射常见的非标准严重性
            severity_mapping = {
                'err': 'error',
                'warn': 'warning', 
                'suggestion': 'info',
                'note': 'info',
                'critical': 'high',
                'major': 'high',
                'minor': 'low'
            }
            
            issue['severity'] = severity_mapping.get(severity, severity)
    
    @staticmethod
    def _standardize_severity_grouping(severity_groups: Dict[str, int]):
        """标准化严重性分组"""
        if not isinstance(severity_groups, dict):
            return
        
        # 确保标准分组存在
        standard_groups = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for group in standard_groups:
            if group not in severity_groups:
                severity_groups[group] = 0
        
        # 移除非标准分组（可选）
        non_standard = [k for k in severity_groups.keys() if k not in standard_groups]
        for key in non_standard:
            logger.debug(f"Found non-standard severity group: {key}")


def validate_and_standardize_result(result: PluginResult) -> tuple[PluginResult, List[ValidationError]]:
    """验证并标准化插件结果"""
    # 先标准化
    standardized_result = ResultStandardizer.standardize_plugin_result(result)
    
    # 再验证
    validator = PluginResultValidator()
    validation_errors = validator.validate_plugin_result(standardized_result)
    
    return standardized_result, validation_errors