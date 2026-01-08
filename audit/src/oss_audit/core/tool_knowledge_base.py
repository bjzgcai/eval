#!/usr/bin/env python3
"""
工具知识库 - 存储工具执行历史和效果预测模型
为智能决策代理提供工具执行历史数据和效果预测
"""

import json
import logging
import time
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict
import hashlib

from .project_detector import ProjectInfo, ProjectType, StructureType
from .tool_registry import Tool

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionRecord:
    """工具执行记录"""
    tool_name: str
    project_type: str
    project_language: str
    project_size: int  # 代码行数
    execution_time: float
    success: bool
    quality_score: float  # 工具给出的质量分数
    issues_found: int
    timestamp: float = field(default_factory=time.time)
    project_hash: str = ""  # 项目特征哈希
    
    def __post_init__(self):
        if not self.project_hash:
            # 生成项目特征哈希用于匿名化
            features = f"{self.project_type}_{self.project_language}_{self.project_size//1000}k"
            self.project_hash = hashlib.md5(features.encode()).hexdigest()[:8]


@dataclass 
class ToolEffectiveness:
    """工具效果评估"""
    tool_name: str
    project_type: str
    accuracy_score: float  # 准确性评分 0-1
    speed_score: float     # 速度评分 0-1  
    coverage_score: float  # 覆盖度评分 0-1
    reliability_score: float  # 可靠性评分 0-1
    overall_effectiveness: float  # 综合效果 0-1
    execution_count: int   # 执行次数
    last_updated: float = field(default_factory=time.time)


@dataclass
class ProjectProfile:
    """项目特征档案"""
    project_type: str
    primary_language: str
    size_category: str  # small, medium, large, huge
    complexity_level: str  # low, medium, high, very_high
    risk_factors: List[str]
    recommended_tools: List[str]
    confidence: float = 0.0


class ToolKnowledgeBase:
    """工具知识库 - 基于历史数据预测工具效果"""
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        self.knowledge_base_path = knowledge_base_path or self._get_default_path()
        self.execution_records: List[ToolExecutionRecord] = []
        self.tool_effectiveness: Dict[str, ToolEffectiveness] = {}
        self.project_profiles: Dict[str, ProjectProfile] = {}
        self.learning_enabled = True
        
        self._load_knowledge_base()
        self._initialize_baseline_knowledge()
        
    def _get_default_path(self) -> str:
        """获取默认知识库路径"""
        return str(Path.home() / ".oss-audit" / "knowledge_base.json")
        
    def _load_knowledge_base(self):
        """加载知识库"""
        try:
            if Path(self.knowledge_base_path).exists():
                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 加载执行记录
                self.execution_records = [
                    ToolExecutionRecord(**record) 
                    for record in data.get('execution_records', [])
                ]
                
                # 加载工具效果
                self.tool_effectiveness = {
                    key: ToolEffectiveness(**value)
                    for key, value in data.get('tool_effectiveness', {}).items()
                }
                
                # 加载项目档案
                self.project_profiles = {
                    key: ProjectProfile(**value)
                    for key, value in data.get('project_profiles', {}).items()
                }
                
                logger.info(f"知识库加载完成: {len(self.execution_records)} 条记录")
                
        except Exception as e:
            logger.warning(f"知识库加载失败: {e}, 使用空知识库")
            
    def _save_knowledge_base(self):
        """保存知识库"""
        try:
            # 确保目录存在
            Path(self.knowledge_base_path).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'execution_records': [asdict(record) for record in self.execution_records],
                'tool_effectiveness': {
                    key: asdict(value) for key, value in self.tool_effectiveness.items()
                },
                'project_profiles': {
                    key: asdict(value) for key, value in self.project_profiles.items()
                },
                'last_updated': time.time(),
                'version': '1.0'
            }
            
            with open(self.knowledge_base_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"知识库保存失败: {e}")
            
    def _initialize_baseline_knowledge(self):
        """初始化基线知识"""
        if not self.tool_effectiveness:
            # Python工具基线知识
            self.tool_effectiveness.update({
                'pylint_python_library': ToolEffectiveness(
                    tool_name='pylint', project_type='library',
                    accuracy_score=0.85, speed_score=0.6, coverage_score=0.9,
                    reliability_score=0.95, overall_effectiveness=0.825,
                    execution_count=0
                ),
                'bandit_python_web': ToolEffectiveness(
                    tool_name='bandit', project_type='web_application', 
                    accuracy_score=0.8, speed_score=0.8, coverage_score=0.7,
                    reliability_score=0.9, overall_effectiveness=0.8,
                    execution_count=0
                ),
                'eslint_javascript_web': ToolEffectiveness(
                    tool_name='eslint', project_type='web_application',
                    accuracy_score=0.9, speed_score=0.85, coverage_score=0.85,
                    reliability_score=0.9, overall_effectiveness=0.875,
                    execution_count=0
                ),
                'checkstyle_java_library': ToolEffectiveness(
                    tool_name='checkstyle', project_type='library',
                    accuracy_score=0.75, speed_score=0.7, coverage_score=0.8,
                    reliability_score=0.85, overall_effectiveness=0.775,
                    execution_count=0
                )
            })
            
    def record_tool_execution(self, tool_name: str, project_info: ProjectInfo,
                            execution_time: float, success: bool,
                            quality_score: float, issues_found: int):
        """记录工具执行结果"""
        if not self.learning_enabled:
            return
            
        try:
            record = ToolExecutionRecord(
                tool_name=tool_name,
                project_type=project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type),
                project_language=project_info.get_primary_language() or 'unknown',
                project_size=project_info.size_metrics.code_lines,
                execution_time=execution_time,
                success=success,
                quality_score=quality_score,
                issues_found=issues_found
            )
            
            self.execution_records.append(record)
            
            # 限制记录数量，保留最新的1000条
            if len(self.execution_records) > 1000:
                self.execution_records = self.execution_records[-1000:]
                
            # 更新工具效果评估
            self._update_tool_effectiveness(record)
            
            logger.debug(f"记录工具执行: {tool_name} on {record.project_hash}")
            
        except Exception as e:
            logger.error(f"记录工具执行失败: {e}")
            
    def _update_tool_effectiveness(self, record: ToolExecutionRecord):
        """更新工具效果评估"""
        key = f"{record.tool_name}_{record.project_type}"
        
        if key not in self.tool_effectiveness:
            # 创建新的效果评估
            self.tool_effectiveness[key] = ToolEffectiveness(
                tool_name=record.tool_name,
                project_type=record.project_type,
                accuracy_score=0.7,  # 默认值
                speed_score=1.0 if record.execution_time < 30 else 0.5,
                coverage_score=0.7,
                reliability_score=1.0 if record.success else 0.5,
                overall_effectiveness=0.7,
                execution_count=1
            )
        else:
            # 更新现有评估（使用指数移动平均）
            effectiveness = self.tool_effectiveness[key]
            alpha = 0.1  # 学习率
            
            # 更新速度评分
            current_speed = 1.0 if record.execution_time < 30 else max(0.1, 60.0 / record.execution_time)
            effectiveness.speed_score = (1 - alpha) * effectiveness.speed_score + alpha * current_speed
            
            # 更新可靠性评分
            current_reliability = 1.0 if record.success else 0.0
            effectiveness.reliability_score = (1 - alpha) * effectiveness.reliability_score + alpha * current_reliability
            
            # 更新执行次数
            effectiveness.execution_count += 1
            effectiveness.last_updated = time.time()
            
            # 重新计算综合效果
            effectiveness.overall_effectiveness = (
                effectiveness.accuracy_score * 0.3 +
                effectiveness.speed_score * 0.2 +
                effectiveness.coverage_score * 0.2 +
                effectiveness.reliability_score * 0.3
            )
            
    def predict_tool_effectiveness(self, tools: List[Tool], 
                                 project_info: ProjectInfo) -> Dict[str, float]:
        """预测工具在特定项目上的效果"""
        try:
            predictions = {}
            project_type = project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type)
            
            for tool in tools:
                key = f"{tool.name}_{project_type}"
                
                if key in self.tool_effectiveness:
                    # 基于历史数据预测
                    effectiveness = self.tool_effectiveness[key]
                    base_score = effectiveness.overall_effectiveness
                    
                    # 根据项目特征调整预测
                    adjusted_score = self._adjust_prediction_for_project(
                        base_score, tool, project_info, effectiveness
                    )
                    predictions[tool.name] = adjusted_score
                    
                else:
                    # 没有历史数据，使用启发式预测
                    predictions[tool.name] = self._heuristic_effectiveness_prediction(tool, project_info)
                    
            return predictions
            
        except Exception as e:
            logger.error(f"工具效果预测失败: {e}")
            return {tool.name: 0.7 for tool in tools}  # 默认预测
            
    def _adjust_prediction_for_project(self, base_score: float, tool: Tool,
                                     project_info: ProjectInfo,
                                     effectiveness: ToolEffectiveness) -> float:
        """根据项目特征调整预测分数"""
        adjusted_score = base_score
        
        # 根据项目规模调整
        if project_info.size_metrics.code_lines > 50000:  # 大型项目
            if effectiveness.speed_score < 0.5:  # 慢速工具
                adjusted_score *= 0.8  # 大型项目上慢速工具效果降低
            else:
                adjusted_score *= 1.1  # 快速工具在大项目上更有价值
                
        # 根据项目复杂度调整
        language_count = len(project_info.languages)
        if language_count > 2:  # 多语言项目
            if tool.language == 'universal':
                adjusted_score *= 1.2  # 通用工具在多语言项目更有价值
            else:
                adjusted_score *= 0.9   # 单语言工具价值降低
                
        # 根据工具可靠性调整
        if effectiveness.execution_count > 10:  # 有足够的历史数据
            if effectiveness.reliability_score > 0.9:
                adjusted_score *= 1.1  # 可靠工具加分
            elif effectiveness.reliability_score < 0.7:
                adjusted_score *= 0.8  # 不可靠工具扣分
                
        return min(max(adjusted_score, 0.1), 1.0)  # 限制在0.1-1.0范围内
        
    def _heuristic_effectiveness_prediction(self, tool: Tool, project_info: ProjectInfo) -> float:
        """基于启发式规则预测工具效果"""
        base_score = 0.7  # 默认基础分数
        
        # 基于工具优先级调整
        priority_bonus = {1: 0.2, 2: 0.1, 3: 0.0, 4: -0.1, 5: -0.2}
        base_score += priority_bonus.get(tool.priority, 0)
        
        # 基于工具类型调整
        project_type = project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type)
        
        if project_type == 'web_application':
            if 'security' in tool.categories:
                base_score += 0.1  # Web项目安全工具加分
        elif project_type == 'library':
            if 'quality' in tool.categories:
                base_score += 0.1  # 库项目质量工具加分
                
        # 基于语言匹配度调整
        primary_language = project_info.get_primary_language()
        if tool.language == primary_language:
            base_score += 0.15  # 语言匹配加分
        elif tool.language == 'universal':
            base_score += 0.05  # 通用工具小幅加分
            
        return min(max(base_score, 0.1), 1.0)
        
    def get_similar_projects(self, project_info: ProjectInfo, limit: int = 5) -> List[ToolExecutionRecord]:
        """获取相似项目的执行记录"""
        try:
            project_type = project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type)
            primary_language = project_info.get_primary_language() or 'unknown'
            size_category = self._get_size_category(project_info.size_metrics.code_lines)
            
            # 按相似度排序
            scored_records = []
            for record in self.execution_records:
                similarity = self._calculate_project_similarity(
                    project_type, primary_language, size_category,
                    record.project_type, record.project_language, 
                    self._get_size_category(record.project_size)
                )
                if similarity > 0.3:  # 最低相似度阈值
                    scored_records.append((similarity, record))
                    
            # 按相似度降序排序，返回top N
            scored_records.sort(key=lambda x: x[0], reverse=True)
            return [record for _, record in scored_records[:limit]]
            
        except Exception as e:
            logger.error(f"获取相似项目失败: {e}")
            return []
            
    def _calculate_project_similarity(self, type1: str, lang1: str, size1: str,
                                    type2: str, lang2: str, size2: str) -> float:
        """计算项目相似度"""
        similarity = 0.0
        
        # 项目类型相似度 (权重40%)
        if type1 == type2:
            similarity += 0.4
        elif self._are_related_types(type1, type2):
            similarity += 0.2
            
        # 语言相似度 (权重40%) 
        if lang1 == lang2:
            similarity += 0.4
        elif self._are_related_languages(lang1, lang2):
            similarity += 0.2
            
        # 规模相似度 (权重20%)
        if size1 == size2:
            similarity += 0.2
        elif self._are_adjacent_sizes(size1, size2):
            similarity += 0.1
            
        return similarity
        
    def _are_related_types(self, type1: str, type2: str) -> bool:
        """判断项目类型是否相关"""
        related_groups = [
            {'web_application', 'api_service'},
            {'library', 'framework'},
            {'cli_tool', 'desktop_application'},
            {'data_science', 'machine_learning'}
        ]
        
        for group in related_groups:
            if type1 in group and type2 in group:
                return True
        return False
        
    def _are_related_languages(self, lang1: str, lang2: str) -> bool:
        """判断编程语言是否相关"""
        related_groups = [
            {'javascript', 'typescript'},
            {'python', 'python3'},
            {'c', 'cpp', 'c++'},
            {'java', 'kotlin', 'scala'}
        ]
        
        for group in related_groups:
            if lang1 in group and lang2 in group:
                return True
        return False
        
    def _are_adjacent_sizes(self, size1: str, size2: str) -> bool:
        """判断项目规模是否相邻"""
        size_order = ['small', 'medium', 'large', 'huge']
        try:
            idx1, idx2 = size_order.index(size1), size_order.index(size2)
            return abs(idx1 - idx2) == 1
        except ValueError:
            return False
            
    def _get_size_category(self, code_lines: int) -> str:
        """根据代码行数确定规模类别"""
        if code_lines < 1000:
            return 'small'
        elif code_lines < 10000:
            return 'medium'
        elif code_lines < 100000:
            return 'large'
        else:
            return 'huge'
            
    def get_tool_statistics(self) -> Dict[str, Any]:
        """获取工具使用统计"""
        try:
            stats = {
                'total_executions': len(self.execution_records),
                'tool_usage': defaultdict(int),
                'success_rates': {},
                'avg_execution_times': {},
                'project_types': defaultdict(int)
            }
            
            for record in self.execution_records:
                stats['tool_usage'][record.tool_name] += 1
                stats['project_types'][record.project_type] += 1
                
            # 计算成功率和平均执行时间
            tool_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'times': []})
            
            for record in self.execution_records:
                tool_stats[record.tool_name]['total'] += 1
                if record.success:
                    tool_stats[record.tool_name]['success'] += 1
                tool_stats[record.tool_name]['times'].append(record.execution_time)
                
            for tool_name, data in tool_stats.items():
                stats['success_rates'][tool_name] = data['success'] / data['total'] if data['total'] > 0 else 0
                stats['avg_execution_times'][tool_name] = sum(data['times']) / len(data['times']) if data['times'] else 0
                
            return dict(stats)
            
        except Exception as e:
            logger.error(f"获取工具统计失败: {e}")
            return {}
            
    def cleanup_old_records(self, days: int = 90):
        """清理旧记录"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            initial_count = len(self.execution_records)
            
            self.execution_records = [
                record for record in self.execution_records 
                if record.timestamp > cutoff_time
            ]
            
            cleaned_count = initial_count - len(self.execution_records)
            if cleaned_count > 0:
                logger.info(f"清理了 {cleaned_count} 条过期记录")
                self._save_knowledge_base()
                
        except Exception as e:
            logger.error(f"清理记录失败: {e}")
            
    def save_knowledge(self):
        """手动保存知识库"""
        self._save_knowledge_base()
        
    def disable_learning(self):
        """禁用学习功能"""
        self.learning_enabled = False
        
    def enable_learning(self):
        """启用学习功能"""
        self.learning_enabled = True