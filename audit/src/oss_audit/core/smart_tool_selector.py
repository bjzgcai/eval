#!/usr/bin/env python3
"""
Smart Tool Selector - 智能工具选择器
基于维度和项目特征选择最优的1-2个工具
"""

import logging
from typing import List, Dict, Set, Any
from dataclasses import dataclass
from enum import Enum

from .tool_registry import Tool
from .project_detector import ProjectInfo, ProjectType

logger = logging.getLogger(__name__)


class DimensionCategory(Enum):
    """分析维度分类"""
    CODE_QUALITY = "质量分析"      # pylint, eslint, checkstyle  
    SECURITY = "安全分析"          # bandit, npm-audit, spotbugs-security
    TESTING = "测试分析"           # pytest, jest, junit
    FORMATTING = "格式分析"        # black, prettier, gofmt
    DEPENDENCIES = "依赖分析"      # safety, npm-audit, dependency-check
    BUILD = "构建分析"             # maven, gradle, webpack
    PERFORMANCE = "性能分析"       # profiling tools
    DOCUMENTATION = "文档分析"     # doc coverage, sphinx


@dataclass
class ToolDimensionMapping:
    """工具维度映射"""
    
    # 14个具体维度到通用类别的映射
    dimension_to_category = {
        1: [DimensionCategory.CODE_QUALITY],                    # 代码结构与可维护性
        2: [DimensionCategory.TESTING],                         # 测试覆盖与质量保障
        3: [DimensionCategory.BUILD, DimensionCategory.FORMATTING], # 构建与工程可重复性
        4: [DimensionCategory.DEPENDENCIES],                    # 依赖与许可证合规
        5: [DimensionCategory.SECURITY],                        # 安全性与敏感信息防护
        6: [DimensionCategory.BUILD],                           # CI/CD 自动化保障
        7: [DimensionCategory.DOCUMENTATION],                   # 使用文档与复现性
        8: [DimensionCategory.CODE_QUALITY],                    # 接口与平台兼容性
        9: [DimensionCategory.FORMATTING],                      # 协作流程与代码规范
        10: [DimensionCategory.DEPENDENCIES],                   # 开源协议与法律合规
        11: [DimensionCategory.DOCUMENTATION],                  # 社区治理与贡献机制
        12: [DimensionCategory.SECURITY],                       # 舆情与风险监控
        13: [DimensionCategory.SECURITY],                       # 数据与算法合规审核
        14: [DimensionCategory.DEPENDENCIES],                   # IP（知识产权）
    }
    
    # 工具名称到维度的映射
    tool_to_dimensions = {
        # Python tools
        'pylint': [DimensionCategory.CODE_QUALITY],
        'flake8': [DimensionCategory.CODE_QUALITY, DimensionCategory.FORMATTING],
        'mypy': [DimensionCategory.CODE_QUALITY],
        'bandit': [DimensionCategory.SECURITY],
        'safety': [DimensionCategory.SECURITY, DimensionCategory.DEPENDENCIES],
        'black': [DimensionCategory.FORMATTING],
        'isort': [DimensionCategory.FORMATTING],
        'pytest': [DimensionCategory.TESTING],
        'coverage': [DimensionCategory.TESTING],
        
        # JavaScript tools
        'eslint': [DimensionCategory.CODE_QUALITY],
        'prettier': [DimensionCategory.FORMATTING],
        'jest': [DimensionCategory.TESTING],
        'npm-audit': [DimensionCategory.SECURITY, DimensionCategory.DEPENDENCIES],
        'retire': [DimensionCategory.SECURITY, DimensionCategory.DEPENDENCIES],
        
        # Java tools
        'checkstyle': [DimensionCategory.CODE_QUALITY, DimensionCategory.FORMATTING],
        'pmd': [DimensionCategory.CODE_QUALITY],
        'spotbugs': [DimensionCategory.CODE_QUALITY, DimensionCategory.SECURITY],
        'find-sec-bugs': [DimensionCategory.SECURITY],
        'dependency-check': [DimensionCategory.SECURITY, DimensionCategory.DEPENDENCIES],
        'maven': [DimensionCategory.BUILD],
        'gradle': [DimensionCategory.BUILD],
        'junit': [DimensionCategory.TESTING],
        
        # Go tools
        'gofmt': [DimensionCategory.FORMATTING],
        'go-vet': [DimensionCategory.CODE_QUALITY],
        'golint': [DimensionCategory.CODE_QUALITY],
        'gosec': [DimensionCategory.SECURITY],
        'staticcheck': [DimensionCategory.CODE_QUALITY],
        
        # Universal tools
        'semgrep': [DimensionCategory.SECURITY, DimensionCategory.CODE_QUALITY],
        'gitleaks': [DimensionCategory.SECURITY],
        'trivy': [DimensionCategory.SECURITY, DimensionCategory.DEPENDENCIES],
        'sonarqube-scanner': [DimensionCategory.CODE_QUALITY, DimensionCategory.SECURITY],
        'syft': [DimensionCategory.DEPENDENCIES]
    }


class SmartToolSelector:
    """智能工具选择器"""
    
    def __init__(self):
        self.dimension_mapping = ToolDimensionMapping()
    
    def get_tools_for_dimension(self, dimension_id: int, available_tools: List[Tool], 
                               project_info: ProjectInfo, max_tools: int = 2) -> List[Tool]:
        """
        为特定维度ID获取最优工具
        
        Args:
            dimension_id: 维度ID (1-14)
            available_tools: 可用工具列表  
            project_info: 项目信息
            max_tools: 最大工具数量
            
        Returns:
            该维度的最优工具列表
        """
        if dimension_id not in self.dimension_mapping.dimension_to_category:
            logger.warning(f"Unknown dimension ID: {dimension_id}")
            return []
        
        # 获取该维度对应的类别
        categories = self.dimension_mapping.dimension_to_category[dimension_id]
        
        # 收集该维度相关的所有工具
        relevant_tools = []
        for tool in available_tools:
            if tool.name in self.dimension_mapping.tool_to_dimensions:
                tool_categories = self.dimension_mapping.tool_to_dimensions[tool.name]
                # 检查是否有交集
                if any(cat in categories for cat in tool_categories):
                    relevant_tools.append(tool)
        
        if not relevant_tools:
            return []
        
        # 为这些工具打分并选择最优的
        scored_tools = []
        for tool in relevant_tools:
            # 基于主要类别计算分数
            score = 0
            for category in categories:
                if category in self.dimension_mapping.tool_to_dimensions.get(tool.name, []):
                    score += self._calculate_tool_score(tool, project_info, category)
            
            scored_tools.append((tool, score))
        
        # 排序并返回前max_tools个
        scored_tools.sort(key=lambda x: x[1], reverse=True)
        selected = [tool for tool, score in scored_tools[:max_tools]]
        
        logger.debug(f"维度{dimension_id}: 从{len(relevant_tools)}个相关工具中选择了{len(selected)}个: {[t.name for t in selected]}")
        return selected

    def select_optimal_tools_for_all_dimensions(self, available_tools: List[Tool], 
                                              project_info: ProjectInfo, 
                                              max_tools_per_dimension: int = 1) -> Dict[int, List[Tool]]:
        """
        为所有维度选择最优工具，避免重复分配
        
        Args:
            available_tools: 可用工具列表
            project_info: 项目信息
            max_tools_per_dimension: 每个维度最多选择的工具数量
            
        Returns:
            维度ID到工具列表的映射
        """
        logger.info(f"开始全局智能工具选择，可用工具: {len(available_tools)}")
        
        # 所有维度ID (1-14)
        all_dimensions = list(range(1, 15))
        
        # 记录已分配的工具，避免重复
        # 但允许某些关键安全工具在相关维度之间共享
        allocated_tools = set()
        shared_security_tools = {'gitleaks', 'semgrep', 'bandit', 'sonarqube-scanner'}
        security_dimensions = {5, 12, 13}  # 安全性与敏感信息防护、舆情与风险监控、数据与算法合规审核
        dimension_tool_mapping = {}
        
        # 根据项目特征确定维度优先级
        dimension_scores = {}
        for dim_id in all_dimensions:
            # 根据维度重要性和项目特征计算优先级
            priority_score = self._calculate_dimension_priority_score(dim_id, project_info)
            dimension_scores[dim_id] = priority_score
        
        # 按优先级排序维度
        sorted_dimensions = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)
        
        for dim_id, _ in sorted_dimensions:
            # 获取该维度的候选工具
            candidate_tools = self.get_tools_for_dimension(dim_id, available_tools, project_info, max_tools=5)
            
            # 过滤已分配的工具，但允许安全工具在安全维度间共享
            available_for_dim = []
            for t in candidate_tools:
                if t.name not in allocated_tools:
                    # 工具尚未分配，可以使用
                    available_for_dim.append(t)
                elif (t.name in shared_security_tools and 
                      dim_id in security_dimensions):
                    # 安全工具可以在安全维度间共享
                    available_for_dim.append(t)
            
            # 选择最优工具
            if available_for_dim:
                selected_count = min(max_tools_per_dimension, len(available_for_dim))
                selected_tools = available_for_dim[:selected_count]
                
                # 记录分配
                dimension_tool_mapping[dim_id] = selected_tools
                for tool in selected_tools:
                    # 只有非共享工具才加入去重列表
                    if tool.name not in shared_security_tools:
                        allocated_tools.add(tool.name)
                
                logger.debug(f"维度{dim_id}: 选择了{len(selected_tools)}个工具: {[t.name for t in selected_tools]}")
            else:
                dimension_tool_mapping[dim_id] = []
                logger.debug(f"维度{dim_id}: 无可用工具（避免重复）")
        
        total_tools = sum(len(tools) for tools in dimension_tool_mapping.values())
        logger.info(f"全局智能选择完成: 分配了{total_tools}个工具给{len(all_dimensions)}个维度")
        return dimension_tool_mapping
    
    def _group_tools_by_dimension(self, available_tools: List[Tool]) -> Dict[DimensionCategory, List[Tool]]:
        """按维度分组工具"""
        dimension_tools = {dim: [] for dim in DimensionCategory}
        
        unmapped_tools = []
        for tool in available_tools:
            dimensions = self.dimension_mapping.tool_to_dimensions.get(tool.name, [])
            if not dimensions:
                unmapped_tools.append(tool.name)
            for dimension in dimensions:
                dimension_tools[dimension].append(tool)
        
        if unmapped_tools:
            logger.debug(f"未映射的工具: {unmapped_tools}")
        
        return dimension_tools
    
    def _calculate_dimension_priorities(self, project_info: ProjectInfo) -> List[DimensionCategory]:
        """根据项目特征计算维度优先级"""
        priorities = []
        
        # 基于项目类型的维度优先级
        project_type_priorities = {
            ProjectType.WEB_APPLICATION: [
                DimensionCategory.SECURITY,      # Web应用安全最重要
                DimensionCategory.CODE_QUALITY,
                DimensionCategory.TESTING,
                DimensionCategory.DEPENDENCIES,
                DimensionCategory.FORMATTING
            ],
            ProjectType.LIBRARY: [
                DimensionCategory.CODE_QUALITY,  # 库项目质量最重要
                DimensionCategory.TESTING,
                DimensionCategory.FORMATTING,
                DimensionCategory.DOCUMENTATION,
                DimensionCategory.DEPENDENCIES
            ],
            ProjectType.CLI_TOOL: [
                DimensionCategory.CODE_QUALITY,
                DimensionCategory.TESTING,
                DimensionCategory.BUILD,
                DimensionCategory.FORMATTING,
                DimensionCategory.DEPENDENCIES
            ],
            ProjectType.DATA_SCIENCE: [
                DimensionCategory.CODE_QUALITY,
                DimensionCategory.SECURITY,      # 数据安全重要
                DimensionCategory.DEPENDENCIES,  # 依赖管理重要
                DimensionCategory.TESTING,
                DimensionCategory.FORMATTING
            ]
        }
        
        # 获取项目类型对应的优先级
        project_type = project_info.project_type
        if hasattr(project_type, 'value'):
            project_type = ProjectType(project_type.value)
        elif isinstance(project_type, str):
            try:
                project_type = ProjectType(project_type)
            except ValueError:
                project_type = ProjectType.UNKNOWN
        
        if project_type in project_type_priorities:
            priorities = project_type_priorities[project_type]
        else:
            # 默认优先级
            priorities = [
                DimensionCategory.CODE_QUALITY,
                DimensionCategory.SECURITY,
                DimensionCategory.TESTING,
                DimensionCategory.DEPENDENCIES,
                DimensionCategory.FORMATTING,
                DimensionCategory.BUILD
            ]
        
        logger.debug(f"项目类型 {project_type} 的维度优先级: {[p.value for p in priorities]}")
        return priorities
    
    def _select_tools_for_dimension(self, tools: List[Tool], 
                                   project_info: ProjectInfo, 
                                   dimension: DimensionCategory,
                                   max_count: int) -> List[Tool]:
        """为特定维度选择最优工具"""
        if not tools:
            return []
        
        # 根据项目语言和工具特点评分
        scored_tools = []
        
        for tool in tools:
            score = self._calculate_tool_score(tool, project_info, dimension)
            scored_tools.append((tool, score))
        
        # 按分数排序，取前max_count个
        scored_tools.sort(key=lambda x: x[1], reverse=True)
        selected = [tool for tool, score in scored_tools[:max_count]]
        
        return selected
    
    def _calculate_tool_score(self, tool: Tool, 
                            project_info: ProjectInfo, 
                            dimension: DimensionCategory) -> float:
        """计算工具评分"""
        score = 0.0
        
        # 1. 语言匹配度 (40%)
        if tool.language in project_info.languages:
            language_percentage = project_info.languages[tool.language]
            score += language_percentage * 40
        elif tool.language == 'universal':
            # 通用工具基础分
            score += 20
        
        # 2. 工具优先级 (30%) - 数字越小优先级越高
        priority_score = max(0, 10 - tool.priority) * 3  # priority 1-10 映射到 30-0
        score += priority_score
        
        # 3. 执行时间 (20%) - 时间越短分数越高
        time_score = max(0, 300 - tool.estimated_time) / 300 * 20
        score += time_score
        
        # 4. 维度匹配度 (10%)
        tool_dimensions = self.dimension_mapping.tool_to_dimensions.get(tool.name, [])
        if dimension in tool_dimensions:
            score += 10
        
        # 5. 项目特征加分
        score += self._get_project_specific_bonus(tool, project_info)
        
        return score
    
    def _get_project_specific_bonus(self, tool: Tool, project_info: ProjectInfo) -> float:
        """获取项目特征相关的加分"""
        bonus = 0.0
        
        # 项目规模加分
        code_lines = project_info.size_metrics.code_lines
        if code_lines > 10000 and tool.name in ['sonarqube-scanner', 'semgrep']:
            bonus += 5  # 大项目倾向于使用强力工具
        elif code_lines < 1000 and tool.name in ['pylint', 'eslint']:
            bonus += 3  # 小项目倾向于使用轻量工具
        
        # 测试文件数量
        if project_info.size_metrics.test_files > 0:
            if tool.name in ['pytest', 'jest', 'junit', 'coverage']:
                bonus += 5
        
        # Web应用特征
        project_type = getattr(project_info.project_type, 'value', str(project_info.project_type))
        if project_type == 'web_application':
            if tool.name in ['bandit', 'npm-audit', 'semgrep']:
                bonus += 5  # Web应用更需要安全工具
        
        return bonus
    
    def _calculate_dimension_priority_score(self, dimension_id: int, project_info: ProjectInfo) -> float:
        """计算维度优先级分数，分数越高越优先"""
        base_scores = {
            5: 100,  # 安全性与敏感信息防护 - 最高优先级
            1: 90,   # 代码结构与可维护性
            2: 80,   # 测试覆盖与质量保障
            4: 70,   # 依赖与许可证合规
            3: 60,   # 构建与工程可重复性
            6: 50,   # CI/CD 自动化保障
            7: 40,   # 使用文档与复现性
            8: 35,   # 接口与平台兼容性
            9: 30,   # 协作流程与代码规范
            10: 25,  # 开源协议与法律合规
            11: 20,  # 社区治理与贡献机制
            12: 15,  # 舆情与风险监控
            13: 10,  # 数据与算法合规审核
            14: 5    # IP（知识产权）
        }
        
        score = base_scores.get(dimension_id, 0)
        
        # 根据项目特征调整优先级
        project_type = getattr(project_info.project_type, 'value', str(project_info.project_type))
        
        if project_type == 'web_application':
            if dimension_id == 5:  # 安全性
                score += 20
            elif dimension_id == 2:  # 测试覆盖
                score += 10
        elif project_type == 'library':
            if dimension_id == 1:  # 代码质量
                score += 15
            elif dimension_id == 7:  # 文档
                score += 10
        elif project_type == 'data_science':
            if dimension_id == 13:  # 数据合规
                score += 25
            elif dimension_id == 5:  # 安全性
                score += 10
        
        # 根据项目大小调整
        if project_info.size_metrics.code_lines > 10000:
            if dimension_id in [1, 6]:  # 代码质量和CI/CD对大项目更重要
                score += 10
        
        return score


def create_smart_tool_selector() -> SmartToolSelector:
    """创建智能工具选择器实例"""
    return SmartToolSelector()