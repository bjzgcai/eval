#!/usr/bin/env python3
"""
简单机器学习模型 - 用于工具效果预测和策略优化
为智能决策代理提供预测支持组件
"""

import logging
import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from collections import defaultdict
import pickle

from .project_detector import ProjectInfo, ProjectType
from .tool_registry import Tool

logger = logging.getLogger(__name__)


@dataclass
class FeatureVector:
    """特征向量"""
    project_size_category: int       # 0-3 (small, medium, large, huge)
    project_type_id: int            # 项目类型ID
    language_diversity: float       # 语言多样性 0-1
    dependency_complexity: float    # 依赖复杂度 0-1
    risk_score: float              # 风险分数 0-1
    build_complexity: float        # 构建复杂度 0-1
    
    def to_list(self) -> List[float]:
        """转换为列表"""
        return [
            float(self.project_size_category),
            float(self.project_type_id), 
            self.language_diversity,
            self.dependency_complexity,
            self.risk_score,
            self.build_complexity
        ]


@dataclass
class PredictionResult:
    """预测结果"""
    tool_name: str
    predicted_effectiveness: float  # 预测效果 0-1
    confidence: float              # 预测信心度 0-1
    execution_time_estimate: float # 预估执行时间
    success_probability: float     # 成功概率 0-1
    feature_importance: Dict[str, float]  # 特征重要性


@dataclass
class TrainingExample:
    """训练样本"""
    features: FeatureVector
    tool_name: str
    actual_effectiveness: float    # 实际效果 0-1
    actual_execution_time: float   # 实际执行时间
    success: bool                  # 是否成功执行
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class SimpleMLModel:
    """
    简单机器学习模型 - 基于历史数据预测工具效果
    
    使用简单的线性回归和决策规则，避免复杂依赖
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or self._get_default_model_path()
        
        # 模型参数
        self.effectiveness_model = {}    # 工具效果预测模型
        self.time_model = {}            # 执行时间预测模型
        self.success_model = {}         # 成功概率预测模型
        
        # 训练数据
        self.training_examples: List[TrainingExample] = []
        
        # 特征映射
        self.project_type_mapping = self._create_project_type_mapping()
        
        # 模型状态
        self.is_trained = False
        self.last_training_time = 0
        
        self._load_model()
        self._initialize_baseline_models()
        
    def _get_default_model_path(self) -> str:
        """获取默认模型路径"""
        return str(Path.home() / ".oss-audit" / "ml_model.pkl")
    
    def _create_project_type_mapping(self) -> Dict[ProjectType, int]:
        """创建项目类型到ID的映射"""
        return {
            ProjectType.LIBRARY: 0,
            ProjectType.WEB_APPLICATION: 1,
            ProjectType.CLI_TOOL: 2,
            ProjectType.DATA_SCIENCE: 3,
            ProjectType.DESKTOP_APP: 4,
            ProjectType.MOBILE_APP: 5,
            ProjectType.GAME: 6,
            ProjectType.UNKNOWN: 7
        }
    
    def _load_model(self):
        """加载模型"""
        try:
            if Path(self.model_path).exists():
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    
                self.effectiveness_model = model_data.get('effectiveness_model', {})
                self.time_model = model_data.get('time_model', {})
                self.success_model = model_data.get('success_model', {})
                self.training_examples = model_data.get('training_examples', [])
                self.is_trained = model_data.get('is_trained', False)
                self.last_training_time = model_data.get('last_training_time', 0)
                
                logger.info(f"模型加载完成: {len(self.training_examples)} 个训练样本")
                
        except Exception as e:
            logger.warning(f"模型加载失败: {e}, 使用默认模型")
    
    def _save_model(self):
        """保存模型"""
        try:
            Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
            
            model_data = {
                'effectiveness_model': self.effectiveness_model,
                'time_model': self.time_model,
                'success_model': self.success_model,
                'training_examples': self.training_examples[-1000:],  # 只保留最新1000个
                'is_trained': self.is_trained,
                'last_training_time': self.last_training_time,
                'version': '1.0',
                'timestamp': time.time()
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
                
            logger.debug("模型保存完成")
            
        except Exception as e:
            logger.error(f"模型保存失败: {e}")
    
    def _initialize_baseline_models(self):
        """初始化基线模型"""
        if not self.effectiveness_model:
            # 基于工具类型和项目类型的基线预测
            self.effectiveness_model = {
                'pylint': {
                    'base_effectiveness': 0.8,
                    'project_type_multipliers': {0: 1.2, 1: 1.0, 2: 1.1},  # library, web, cli
                    'size_impact': -0.1,  # 大项目效果稍降
                    'complexity_threshold': 0.7
                },
                'bandit': {
                    'base_effectiveness': 0.75,
                    'project_type_multipliers': {1: 1.3, 5: 1.2},  # web, api更重要
                    'risk_boost': 0.2,
                    'complexity_threshold': 0.5
                },
                'eslint': {
                    'base_effectiveness': 0.85,
                    'project_type_multipliers': {1: 1.2, 4: 1.1},  # web, desktop
                    'language_dependency': 0.9,
                    'complexity_threshold': 0.6
                },
                'checkstyle': {
                    'base_effectiveness': 0.7,
                    'project_type_multipliers': {0: 1.1, 5: 1.2},  # library, api
                    'size_boost': 0.1,  # 大项目更有用
                    'complexity_threshold': 0.8
                }
            }
        
        if not self.time_model:
            # 基于项目规模的时间预测模型
            self.time_model = {
                'base_times': {
                    'pylint': 30, 'bandit': 20, 'eslint': 25, 'checkstyle': 45,
                    'safety': 15, 'npm-audit': 10, 'gitleaks': 20, 'semgrep': 60
                },
                'size_multipliers': [1.0, 1.5, 2.5, 4.0],  # small, medium, large, huge
                'complexity_factor': 1.2  # 复杂项目额外20%时间
            }
        
        if not self.success_model:
            # 工具成功率预测
            self.success_model = {
                'base_success_rates': {
                    'pylint': 0.95, 'bandit': 0.9, 'eslint': 0.9, 'checkstyle': 0.85,
                    'safety': 0.95, 'npm-audit': 0.9, 'gitleaks': 0.95, 'semgrep': 0.8
                },
                'complexity_penalty': 0.1,  # 复杂项目成功率降低
                'dependency_factor': 0.05   # 依赖多成功率稍降
            }
    
    def extract_features(self, project_info: ProjectInfo, risk_score: float = 0.0) -> FeatureVector:
        """从项目信息提取特征向量"""
        try:
            # 项目规模分类
            code_lines = project_info.size_metrics.code_lines
            if code_lines < 1000:
                size_category = 0  # small
            elif code_lines < 10000:
                size_category = 1  # medium
            elif code_lines < 100000:
                size_category = 2  # large
            else:
                size_category = 3  # huge
            
            # 项目类型ID
            project_type = project_info.project_type
            if hasattr(project_type, 'value'):
                project_type_enum = ProjectType(project_type.value)
            else:
                project_type_enum = ProjectType.LIBRARY
            
            project_type_id = self.project_type_mapping.get(project_type_enum, 0)
            
            # 语言多样性
            languages = project_info.languages
            language_diversity = min(1.0, len(languages) / 5.0)  # 归一化到0-1
            
            # 依赖复杂度
            total_deps = sum(len(deps) for deps in project_info.dependencies.values())
            dependency_complexity = min(1.0, total_deps / 100.0)  # 归一化到0-1
            
            # 构建复杂度
            build_tools_count = len(project_info.build_tools)
            build_complexity = min(1.0, build_tools_count / 5.0)
            
            return FeatureVector(
                project_size_category=size_category,
                project_type_id=project_type_id,
                language_diversity=language_diversity,
                dependency_complexity=dependency_complexity,
                risk_score=min(1.0, risk_score / 100.0),  # 归一化到0-1
                build_complexity=build_complexity
            )
            
        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            # 返回默认特征
            return FeatureVector(
                project_size_category=1,
                project_type_id=0,
                language_diversity=0.2,
                dependency_complexity=0.3,
                risk_score=0.3,
                build_complexity=0.2
            )
    
    def predict_tool_effectiveness(self, tool_name: str, features: FeatureVector) -> PredictionResult:
        """预测工具效果"""
        try:
            # 获取工具基线模型
            tool_model = self.effectiveness_model.get(tool_name)
            
            if tool_model:
                # 基于模型预测
                base_effectiveness = tool_model.get('base_effectiveness', 0.5)
                
                # 项目类型调整
                type_multipliers = tool_model.get('project_type_multipliers', {})
                type_multiplier = type_multipliers.get(features.project_type_id, 1.0)
                
                # 规模影响
                size_impact = tool_model.get('size_impact', 0.0)
                size_adjustment = size_impact * features.project_size_category
                
                # 复杂度阈值
                complexity_threshold = tool_model.get('complexity_threshold', 0.5)
                complexity_penalty = max(0, (features.dependency_complexity - complexity_threshold) * 0.2)
                
                # 风险加成
                risk_boost = tool_model.get('risk_boost', 0.0) * features.risk_score
                
                predicted_effectiveness = (
                    base_effectiveness * type_multiplier +
                    size_adjustment +
                    risk_boost -
                    complexity_penalty
                )
                
                predicted_effectiveness = max(0.1, min(1.0, predicted_effectiveness))
                confidence = 0.8  # 有模型的情况下信心度较高
                
            else:
                # 没有模型时的启发式预测
                predicted_effectiveness = self._heuristic_effectiveness_prediction(tool_name, features)
                confidence = 0.4  # 启发式预测信心度较低
            
            # 预测执行时间
            execution_time_estimate = self._predict_execution_time(tool_name, features)
            
            # 预测成功概率
            success_probability = self._predict_success_probability(tool_name, features)
            
            # 计算特征重要性
            feature_importance = self._calculate_feature_importance(tool_name, features)
            
            return PredictionResult(
                tool_name=tool_name,
                predicted_effectiveness=predicted_effectiveness,
                confidence=confidence,
                execution_time_estimate=execution_time_estimate,
                success_probability=success_probability,
                feature_importance=feature_importance
            )
            
        except Exception as e:
            logger.error(f"工具效果预测失败 {tool_name}: {e}")
            # 返回默认预测
            return PredictionResult(
                tool_name=tool_name,
                predicted_effectiveness=0.5,
                confidence=0.3,
                execution_time_estimate=60.0,
                success_probability=0.8,
                feature_importance={}
            )
    
    def _heuristic_effectiveness_prediction(self, tool_name: str, features: FeatureVector) -> float:
        """启发式效果预测"""
        base_score = 0.5
        
        # 基于工具名称的启发式规则
        if 'lint' in tool_name.lower():
            base_score = 0.7
        elif 'security' in tool_name.lower() or 'bandit' in tool_name.lower():
            base_score = 0.6 + features.risk_score * 0.3
        elif 'test' in tool_name.lower():
            base_score = 0.65
        
        # 项目类型调整
        if features.project_type_id == 1:  # web application
            if 'security' in tool_name.lower():
                base_score += 0.1
        elif features.project_type_id == 0:  # library
            if 'quality' in tool_name.lower() or 'lint' in tool_name.lower():
                base_score += 0.1
        
        return max(0.1, min(1.0, base_score))
    
    def _predict_execution_time(self, tool_name: str, features: FeatureVector) -> float:
        """预测执行时间"""
        try:
            # 基础时间
            base_times = self.time_model.get('base_times', {})
            base_time = base_times.get(tool_name, 45.0)  # 默认45秒
            
            # 规模倍数
            size_multipliers = self.time_model.get('size_multipliers', [1.0, 1.5, 2.5, 4.0])
            size_multiplier = size_multipliers[min(features.project_size_category, len(size_multipliers)-1)]
            
            # 复杂度影响
            complexity_factor = self.time_model.get('complexity_factor', 1.2)
            complexity_multiplier = 1.0 + features.dependency_complexity * (complexity_factor - 1.0)
            
            predicted_time = base_time * size_multiplier * complexity_multiplier
            
            return max(5.0, predicted_time)  # 最少5秒
            
        except Exception as e:
            logger.error(f"执行时间预测失败: {e}")
            return 45.0
    
    def _predict_success_probability(self, tool_name: str, features: FeatureVector) -> float:
        """预测成功概率"""
        try:
            # 基础成功率
            base_rates = self.success_model.get('base_success_rates', {})
            base_rate = base_rates.get(tool_name, 0.85)
            
            # 复杂度惩罚
            complexity_penalty = self.success_model.get('complexity_penalty', 0.1)
            complexity_reduction = features.dependency_complexity * complexity_penalty
            
            # 依赖因素
            dependency_factor = self.success_model.get('dependency_factor', 0.05)
            dependency_reduction = features.dependency_complexity * dependency_factor
            
            success_prob = base_rate - complexity_reduction - dependency_reduction
            
            return max(0.1, min(1.0, success_prob))
            
        except Exception as e:
            logger.error(f"成功概率预测失败: {e}")
            return 0.8
    
    def _calculate_feature_importance(self, tool_name: str, features: FeatureVector) -> Dict[str, float]:
        """计算特征重要性"""
        # 简单的特征重要性计算
        importance = {
            'project_size': 0.25,
            'project_type': 0.20,
            'language_diversity': 0.15,
            'dependency_complexity': 0.20,
            'risk_score': 0.15,
            'build_complexity': 0.05
        }
        
        # 基于工具类型调整重要性
        if 'security' in tool_name.lower():
            importance['risk_score'] = 0.3
            importance['project_type'] = 0.25
        elif 'quality' in tool_name.lower() or 'lint' in tool_name.lower():
            importance['project_size'] = 0.3
            importance['dependency_complexity'] = 0.25
        
        return importance
    
    def add_training_example(self, features: FeatureVector, tool_name: str,
                           actual_effectiveness: float, actual_execution_time: float,
                           success: bool):
        """添加训练样本"""
        try:
            example = TrainingExample(
                features=features,
                tool_name=tool_name,
                actual_effectiveness=actual_effectiveness,
                actual_execution_time=actual_execution_time,
                success=success
            )
            
            self.training_examples.append(example)
            
            # 限制训练样本数量
            if len(self.training_examples) > 1000:
                self.training_examples = self.training_examples[-1000:]
            
            logger.debug(f"添加训练样本: {tool_name}, 效果={actual_effectiveness:.2f}")
            
            # 定期重新训练
            if len(self.training_examples) % 50 == 0:
                self._incremental_training()
                
        except Exception as e:
            logger.error(f"添加训练样本失败: {e}")
    
    def _incremental_training(self):
        """增量训练"""
        try:
            logger.info("开始增量训练...")
            
            # 按工具分组训练样本
            tool_examples = defaultdict(list)
            for example in self.training_examples[-200:]:  # 使用最新200个样本
                tool_examples[example.tool_name].append(example)
            
            # 更新每个工具的模型
            for tool_name, examples in tool_examples.items():
                if len(examples) < 5:  # 样本太少跳过
                    continue
                
                self._update_tool_model(tool_name, examples)
            
            self.is_trained = True
            self.last_training_time = time.time()
            
            # 保存更新后的模型
            self._save_model()
            
            logger.info(f"增量训练完成: 更新了{len(tool_examples)}个工具模型")
            
        except Exception as e:
            logger.error(f"增量训练失败: {e}")
    
    def _update_tool_model(self, tool_name: str, examples: List[TrainingExample]):
        """更新单个工具的模型"""
        try:
            # 计算平均效果
            avg_effectiveness = sum(ex.actual_effectiveness for ex in examples) / len(examples)
            
            # 计算项目类型相关性
            type_effectiveness = defaultdict(list)
            for ex in examples:
                type_effectiveness[ex.features.project_type_id].append(ex.actual_effectiveness)
            
            type_multipliers = {}
            for type_id, effectivenesses in type_effectiveness.items():
                if len(effectivenesses) >= 2:  # 至少2个样本
                    avg_type_effectiveness = sum(effectivenesses) / len(effectivenesses)
                    multiplier = avg_type_effectiveness / max(avg_effectiveness, 0.1)
                    type_multipliers[type_id] = max(0.5, min(2.0, multiplier))
            
            # 更新模型
            if tool_name not in self.effectiveness_model:
                self.effectiveness_model[tool_name] = {}
            
            # 使用指数移动平均更新
            alpha = 0.3  # 学习率
            current_model = self.effectiveness_model[tool_name]
            
            old_base = current_model.get('base_effectiveness', 0.5)
            new_base = old_base * (1 - alpha) + avg_effectiveness * alpha
            current_model['base_effectiveness'] = new_base
            
            if type_multipliers:
                current_model['project_type_multipliers'] = type_multipliers
            
            logger.debug(f"更新工具模型 {tool_name}: 基础效果={new_base:.3f}")
            
        except Exception as e:
            logger.error(f"工具模型更新失败 {tool_name}: {e}")
    
    def predict_batch(self, tools: List[Tool], features: FeatureVector) -> Dict[str, PredictionResult]:
        """批量预测工具效果"""
        predictions = {}
        
        for tool in tools:
            try:
                prediction = self.predict_tool_effectiveness(tool.name, features)
                predictions[tool.name] = prediction
            except Exception as e:
                logger.error(f"批量预测失败 {tool.name}: {e}")
                # 提供默认预测
                predictions[tool.name] = PredictionResult(
                    tool_name=tool.name,
                    predicted_effectiveness=0.5,
                    confidence=0.2,
                    execution_time_estimate=tool.estimated_time,
                    success_probability=0.8,
                    feature_importance={}
                )
        
        return predictions
    
    def get_model_stats(self) -> Dict[str, Any]:
        """获取模型统计信息"""
        try:
            stats = {
                'total_training_examples': len(self.training_examples),
                'trained_tools': len(self.effectiveness_model),
                'is_trained': self.is_trained,
                'last_training_time': self.last_training_time,
                'model_age_hours': (time.time() - self.last_training_time) / 3600 if self.last_training_time > 0 else 0
            }
            
            # 工具训练样本分布
            tool_counts = defaultdict(int)
            for example in self.training_examples:
                tool_counts[example.tool_name] += 1
            
            stats['tool_sample_distribution'] = dict(tool_counts)
            
            # 平均预测信心度
            if self.is_trained and self.training_examples:
                recent_examples = self.training_examples[-100:]
                avg_accuracy = sum(ex.actual_effectiveness for ex in recent_examples) / len(recent_examples)
                stats['recent_avg_accuracy'] = avg_accuracy
            
            return stats
            
        except Exception as e:
            logger.error(f"获取模型统计失败: {e}")
            return {'error': str(e)}
    
    def reset_model(self):
        """重置模型"""
        self.effectiveness_model = {}
        self.time_model = {}
        self.success_model = {}
        self.training_examples = []
        self.is_trained = False
        self.last_training_time = 0
        
        self._initialize_baseline_models()
        logger.info("模型已重置")
    
    def export_model_data(self) -> Dict[str, Any]:
        """导出模型数据（用于分析和调试）"""
        try:
            return {
                'effectiveness_model': self.effectiveness_model,
                'time_model': self.time_model,
                'success_model': self.success_model,
                'training_examples': [asdict(ex) for ex in self.training_examples[-50:]],  # 最新50个
                'model_stats': self.get_model_stats(),
                'export_time': time.time()
            }
        except Exception as e:
            logger.error(f"模型数据导出失败: {e}")
            return {'error': str(e)}