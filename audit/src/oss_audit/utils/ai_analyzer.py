#!/usr/bin/env python3
"""
AI分析模块 - 使用AI技术分析项目成熟度
"""

import json
import re
import os
import yaml
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import hashlib
from .deterministic_cache import get_cached_ai_result, cache_ai_result

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class AIAnalyzer:
    """AI分析器 - 支持基于规则、Gemini AI和OpenAI/DeepSeek的智能分析"""

    def __init__(self, openai_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None, config_path: Optional[str] = None):
        self.analysis_rules = self._load_analysis_rules()
        self.maturity_patterns = self._load_maturity_patterns()

        # 加载配置文件
        self.config = self._load_config(config_path)

        # 检查AI全局启用状态
        self.ai_enabled = self.config.get('ai', {}).get('enabled', True)
        
        # 如果AI被禁用，强制使用规则分析
        if not self.ai_enabled:
            print("AI分析已禁用，使用基于规则的分析", flush=True)
            self.ai_priority = ['rules']
            self.use_openai = False
            self.use_gemini = False
            return

        # 获取AI优先级配置
        self.ai_priority = self.config.get('ai', {}).get('priority', ['openai', 'gemini', 'rules'])

        # 初始化OpenAI/DeepSeek/息壤平台客户端
        self.openai_api_key = (
            openai_api_key or
            self.config.get('ai', {}).get('openai', {}).get('api_key') or
            os.environ.get('OPENAI_API_KEY')
        )
        self.openai_config = self.config.get('ai', {}).get('openai', {})

        # 简化配置读取 - 只读取必要的配置
        self.openai_base_url = self.openai_config.get('base_url', 'https://api.openai.com/v1')
        self.openai_model = self.openai_config.get('model')  # 可选指定模型

        # 智能选择相关配置（可选）
        self.smart_model_selection = self.openai_config.get('smart_model_selection', True)
        self.selection_strategy = self.openai_config.get('selection_strategy', 'balanced')

        # 添加默认值
        self.model_timeout = 60  # 增加超时时间到60秒
        self.auto_fallback = True  # 默认启用自动回退

        self.use_openai = OPENAI_AVAILABLE and self.openai_api_key

        if self.use_openai:
            try:
                self.openai_client = OpenAI(
                    base_url=self.openai_base_url,
                    api_key=self.openai_api_key
                )
                print("AI分析已启用: OpenAI/DeepSeek/息壤平台", flush=True)

                # 简化模型选择逻辑
                if self.openai_model:
                    # 如果配置中指定了模型，直接使用
                    print(f"信息 使用指定模型: {self.openai_model}", flush=True)
                elif self.smart_model_selection:
                    # 启用智能选择
                    print(f"选择 启用智能模型选择 (策略: {self.selection_strategy})", flush=True)
                    self.openai_model = self._select_best_openai_model()
                else:
                    # 使用默认模型
                    self.openai_model = 'gpt-4o-mini'
                    print(f"信息 使用默认模型: {self.openai_model}", flush=True)

            except Exception as e:
                print(f"警告 OpenAI/DeepSeek/息壤平台 AI初始化失败: {e}", flush=True)
                self.use_openai = False

        # 初始化Gemini客户端
        self.gemini_api_key = (
            gemini_api_key or
            self.config.get('ai', {}).get('gemini', {}).get('api_key') or
            os.environ.get('GEMINI_API_KEY')
        )
        self.gemini_config = self.config.get('ai', {}).get('gemini', {})
        self.use_gemini = GEMINI_AVAILABLE and self.gemini_api_key

        if self.use_gemini:
            try:
                genai.configure(api_key=self.gemini_api_key)
                # 自动选择最佳Gemini模型
                gemini_model_name = self._select_best_gemini_model()
                self.gemini_model = genai.GenerativeModel(gemini_model_name)
                print("AI分析已启用: Gemini", flush=True)
            except Exception as e:
                print(f"警告 Gemini AI初始化失败: {e}", flush=True)
                self.use_gemini = False

        # 协同分析配置
        self.enable_collaborative_analysis = self.config.get('ai', {}).get('collaborative_analysis', {}).get('enabled', False)
        self.collaborative_strategy = self.config.get('ai', {}).get('collaborative_analysis', {}).get('strategy', 'ensemble')
        
        # 确定使用的AI方法
        if self.enable_collaborative_analysis:
            self.ai_method = 'collaborative'
            print(f"多模型协同分析已启用 (策略: {self.collaborative_strategy})", flush=True)
        else:
            self.ai_method = self._determine_ai_method()
            if self.ai_method == 'openai':
                print(f"使用OpenAI/DeepSeek AI分析 (模型: {self.openai_model})", flush=True)
            elif self.ai_method == 'gemini':
                print(f"使用Gemini AI分析 (模型: {self.gemini_model})", flush=True)
            else:
                print("使用基于规则的AI分析", flush=True)

    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """加载配置文件"""
        config = {}

        # 尝试加载配置文件
        possible_paths = []
        if config_path:
            possible_paths.append(config_path)

        # 默认配置文件路径
        current_dir = Path.cwd()
        possible_paths.extend([
            current_dir / "config.yaml",
            current_dir.parent / "config.yaml",
            Path("/app/config.yaml")  # Docker容器中的配置文件路径
        ])

        for path in possible_paths:
            if Path(path).exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f) or {}
                    print(f"已加载配置文件: {path}")
                    break
                except Exception as e:
                    print(f"配置文件加载失败 {path}: {e}")

        return config

    def _determine_ai_method(self) -> str:
        """确定使用的AI方法（先检查可用性，再按优先级选择）"""
        # 检查各AI服务的可用性
        openai_available = self.use_openai and self._test_openai_connection()
        gemini_available = self.use_gemini and self._test_gemini_connection()

        # 按优先级选择可用的AI方法
        for method in self.ai_priority:
            if method == 'openai' and openai_available:
                return 'openai'
            elif method == 'gemini' and gemini_available:
                return 'gemini'
            elif method == 'rules':
                return 'rules'
        return 'rules'  # 默认回退到规则分析

    def _select_best_openai_model(self) -> str:
        """简化版智能选择最佳OpenAI/DeepSeek模型"""
        # 获取当前任务信息
        task_info = self._get_current_task_info()

        # 智能模型选择
        print("AI 执行智能模型选择...")
        selected_model = self._intelligent_model_selection(task_info)

        return selected_model

    def _intelligent_model_selection(self, task_info: Dict) -> str:
        """增强版智能模型选择算法 - 根据策略优化选择标准"""
        base_url = self.openai_base_url
        task_type = task_info.get('task_type', 'general_analysis')
        strategy = self.selection_strategy

        print(f"\n选择 智能模型选择过程 (策略: {strategy})")
        print("=" * 60)

        # 1. 获取可用模型列表（实时发现）
        print("信息 步骤1: 获取可用模型列表")
        available_models = self._get_available_models(base_url)
        if not available_models:
            print("失败 未发现可用模型，使用备选模型")
            return self._get_fallback_model(base_url)

        print(f"成功 发现 {len(available_models)} 个可用模型")

        # 2. 根据选择策略过滤和排序模型
        print(f"\n信息 步骤2: 应用 {strategy} 策略过滤模型")
        filtered_models = self._filter_models_by_strategy_enhanced(available_models, task_info, strategy)
        if not filtered_models:
            print("警告 策略过滤后无可用模型，使用所有可用模型")
            filtered_models = available_models

        print(f"成功 策略过滤后剩余 {len(filtered_models)} 个候选模型")

        # 3. 获取模型性能历史数据
        print(f"\n信息 步骤3: 获取模型性能数据")
        performance_data = self._get_model_performance_history()

        # 4. 根据策略计算模型评分
        print(f"\n信息 步骤4: 计算模型评分 (策略: {strategy})")
        model_scores = {}
        for model in filtered_models:
            score = self._calculate_model_score_by_strategy(model, task_info, performance_data, strategy)
            model_scores[model] = score

        # 5. 根据策略选择最佳模型
        print(f"\n信息 步骤5: 选择最佳模型 (策略: {strategy})")
        if model_scores:
            best_model = self._select_best_model_by_strategy(model_scores, strategy)
            print(f"选择 最终选择: {best_model[0]} (评分: {best_model[1]:.2f})")

            # 显示选择原因
            self._show_selection_reason(best_model[0], best_model[1], strategy, task_info)

            return best_model[0]
        else:
            print("失败 无法计算模型评分，使用备选模型")
            return self._get_fallback_model(base_url)

    def _get_current_task_info(self) -> Dict:
        """获取当前任务信息"""
        # 这里可以从调用栈或上下文获取任务信息
        # 暂时返回默认值，实际使用时应该动态获取
        return {
            'task_type': 'general_analysis',
            'content_length': 5000,
            'complexity': 'medium',
            'priority': 'normal',
            'cost_sensitivity': 'medium',
            'quality_requirement': 'good'
        }

    def _check_task_mapping_consistency(self, selected_model: str, task_type: str):
        """检查选择的模型是否与任务映射一致"""
        if not self.task_model_mapping or task_type not in self.task_model_mapping:
            return

        preferred_models = self.task_model_mapping[task_type]
        if selected_model in preferred_models:
            print(f"成功 智能选择与任务映射一致: {selected_model}")
        else:
            print(f"💡 智能选择与任务映射不同: 选择了 {selected_model}，映射建议 {preferred_models}")

    def _prioritize_models_by_task(self, models: List[str], task_type: str) -> List[str]:
        """根据任务类型调整模型优先级（备选方案）"""
        if not self.task_model_mapping or task_type not in self.task_model_mapping:
            return models

        preferred_models = self.task_model_mapping[task_type]
        print(f"选择 任务类型 '{task_type}' 映射建议模型: {preferred_models}")

        # 将映射模型排在前面（作为备选优先级）
        prioritized = []

        # 1. 添加可用的映射模型
        for preferred_model in preferred_models:
            if preferred_model in models:
                prioritized.append(preferred_model)

        # 2. 添加其他可用模型
        for model in models:
            if model not in prioritized:
                prioritized.append(model)

        return prioritized

    def _test_model_availability(self, model: str) -> bool:
        """测试单个模型的可用性"""
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                timeout=self.model_timeout
            )
            return True
        except Exception:
            return False

    def _filter_models_by_strategy_enhanced(self, models: List[str], task_info: Dict, strategy: str) -> List[str]:
        """增强版策略过滤模型 - 根据策略优化选择标准"""

        if strategy == "performance":
            # 性能优先：选择响应时间快、吞吐量高的模型
            print("   更新 性能优先策略: 选择响应时间快、吞吐量高的模型")
            performance_models = [
                "gpt-4o-mini", "Qwen3-4B", "Qwen3-8B", "DeepSeek-R1-0528",
                "Qwen2.5-7B-Instruct", "Phi-3.5-3.8B-Instruct"
            ]
            filtered = [m for m in models if m in performance_models]
            if filtered:
                print(f"   成功 性能优先过滤: 从 {len(models)} 个模型中选择 {len(filtered)} 个高性能模型")
                return filtered
            else:
                print("   警告 未找到性能优先模型，使用所有可用模型")
                return models

        elif strategy == "cost":
            # 成本优先：选择经济实惠的模型
            print("   成本 成本优先策略: 选择经济实惠的模型")
            cost_models = [
                "DeepSeek-R1-0528", "Qwen3-4B", "Qwen3-8B", "Qwen2.5-7B-Instruct",
                "DeepSeek-R1", "gpt-3.5-turbo", "gpt-4o-mini"
            ]
            filtered = [m for m in models if m in cost_models]
            if filtered:
                print(f"   成功 成本优先过滤: 从 {len(models)} 个模型中选择 {len(filtered)} 个经济模型")
                return filtered
            else:
                print("   警告 未找到成本优先模型，使用所有可用模型")
                return models

        elif strategy == "quality":
            # 质量优先：选择高质量、高准确性的模型
            print("   质量 质量优先策略: 选择高质量、高准确性的模型")
            quality_models = [
                "DeepSeek-V3-0324", "DeepSeek-V3", "Qwen3-235B-A22B", "Qwen3-32B",
                "Qwen2.5-72B-Instruct", "glm-4", "gpt-4o", "gpt-4"
            ]
            filtered = [m for m in models if m in quality_models]
            if filtered:
                print(f"   成功 质量优先过滤: 从 {len(models)} 个模型中选择 {len(filtered)} 个高质量模型")
                return filtered
            else:
                print("   警告 未找到质量优先模型，使用所有可用模型")
                return models

        else:  # balanced
            # 平衡策略：综合考虑所有因素
            print("   平衡 平衡策略: 综合考虑性能、成本、质量")
            return models

    def _filter_models_by_strategy(self, models: List[str], task_info: Dict) -> List[str]:
        """根据选择策略过滤模型（保持向后兼容）"""
        return self._filter_models_by_strategy_enhanced(models, task_info, self.selection_strategy)

    def _get_available_models(self, base_url: str) -> List[str]:
        """动态获取可用模型列表"""
        available_models = []

        # 对于息壤一体智算平台，尝试实时获取模型列表
        if 'wishub-x1.ctyun.cn' in base_url or 'xiran' in base_url.lower():
            print("检测 检测到息壤一体智算平台，尝试实时获取可用模型列表...")

            # 首先尝试从API获取模型列表
            api_models = self._get_models_from_api()
            if api_models:
                print(f"信息 从息壤平台API获取到 {len(api_models)} 个模型")
                candidate_models = api_models
            else:
                print("警告 无法从API获取模型列表，使用预定义模型列表")
                candidate_models = self._get_xiran_models()

        # 对于OpenAI官方API，尝试动态获取模型列表
        elif 'openai.com' in base_url.lower():
            try:
                print("检测 尝试从OpenAI API获取可用模型列表...")
                # 使用OpenAI API获取模型列表
                models_response = self.openai_client.models.list()

                # 过滤出支持chat completions的模型
                chat_models = []
                for model in models_response.data:
                    if hasattr(model, 'id') and model.id:
                        # 只包含主要的chat模型，排除一些特殊用途的模型
                        if any(keyword in model.id.lower() for keyword in ['gpt-4', 'gpt-3.5']):
                            chat_models.append(model.id)

                if chat_models:
                    print(f"信息 从OpenAI API获取到 {len(chat_models)} 个可用模型")
                    # 按优先级排序模型
                    prioritized_models = self._prioritize_openai_models(chat_models)
                    candidate_models = prioritized_models
                else:
                    print("警告 无法获取OpenAI模型列表，使用预定义模型")
                    candidate_models = self._get_default_openai_models()

            except Exception as e:
                print(f"警告 获取OpenAI模型列表失败: {e}")
                print("回退 回退到预定义模型列表")
                candidate_models = self._get_default_openai_models()

        # 对于DeepSeek API，使用预定义列表
        elif 'deepseek' in base_url.lower():
            candidate_models = [
                "DeepSeek-V3-0324", "DeepSeek-R1", "DeepSeek-Coder",
                "DeepSeek-V2.5", "DeepSeek-V2", "DeepSeek-Coder-33B"
            ]

        # 对于其他API端点，使用通用列表
        else:
            candidate_models = [
                "gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo",
                "DeepSeek-V3-0324", "DeepSeek-R1", "DeepSeek-Coder"
            ]

        print(f"检测 开始测试 {len(candidate_models)} 个候选模型...")

        # 并行测试模型可用性
        import concurrent.futures
        import threading

        def test_model(model):
            try:
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5,
                    timeout=15  # 测试时使用较短的超时时间
                )
                return model
            except Exception as e:
                error_msg = str(e).lower()
                if 'quota' in error_msg or 'rate limit' in error_msg or '429' in str(e):
                    print(f"警告 模型 {model} 配额不足或限流")
                elif 'not found' in error_msg or 'invalid' in error_msg:
                    print(f"失败 模型 {model} 不存在或无效")
                elif 'timeout' in error_msg:
                    print(f"失败 模型 {model} 连接超时")
                else:
                    print(f"失败 模型 {model} 连接失败: {str(e)[:50]}...")
                return None

        # 使用线程池并行测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_model = {executor.submit(test_model, model): model for model in candidate_models}
            for future in concurrent.futures.as_completed(future_to_model, timeout=60):
                result = future.result()
                if result:
                    available_models.append(result)
                    print(f"成功 发现可用模型: {result}")

        print(f"统计 测试完成，发现 {len(available_models)} 个可用模型")
        return available_models

    def _get_models_from_api(self) -> List[str]:
        """从息壤平台API获取可用模型列表"""
        try:
            # 尝试调用models API获取模型列表
            models_response = self.openai_client.models.list()

            # 过滤和排序模型
            available_models = []
            for model in models_response.data:
                if hasattr(model, 'id') and model.id:
                    # 过滤出主要的模型，排除一些特殊用途的模型
                    if self._is_valid_model(model.id):
                        available_models.append(model.id)

            # 按优先级排序
            prioritized_models = self._prioritize_xiran_models(available_models)

            return prioritized_models

        except Exception as e:
            print(f"警告 从息壤平台API获取模型列表失败: {e}")
            return []

    def _is_valid_model(self, model_id: str) -> bool:
        """判断模型是否有效（用于过滤）"""
        # 排除一些特殊用途的模型
        exclude_keywords = ['embedding', 'whisper', 'dall-e', 'tts', 'moderation']
        if any(keyword in model_id.lower() for keyword in exclude_keywords):
            return False

        # 包含主要模型类型
        include_keywords = [
            'gpt-4', 'gpt-3.5', 'deepseek', 'qwen', 'glm', 'ernie',
            'llava', 'cogvlm', 'phi', 'tinyllama', 'codelama', 'wizardcoder'
        ]
        return any(keyword in model_id.lower() for keyword in include_keywords)

    def _prioritize_xiran_models(self, models: List[str]) -> List[str]:
        """对息壤平台模型按优先级排序"""
        # 定义模型优先级（从高到低）
        priority_order = [
            # 最新高质量模型（优先）
            "DeepSeek-V3-0324", "DeepSeek-V3", "DeepSeek-V3-0324-Preview",
            "DeepSeek-R1", "DeepSeek-R1-Preview",
            "DeepSeek-Coder", "DeepSeek-Coder-33B", "DeepSeek-Coder-6.7B",

            # GPT系列模型
            "gpt-4o", "gpt-4o-mini", "gpt-4o-2024-05-13",
            "gpt-4-turbo", "gpt-4-turbo-2024-04-09", "gpt-4-turbo-preview",
            "gpt-4-0125-preview", "gpt-4-1106-preview", "gpt-4-0613",
            "gpt-4", "gpt-4-0314",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-0301", "gpt-3.5-turbo-instruct", "gpt-3.5-turbo-16k-0613",

            # 其他高质量模型
            "Qwen2.5-72B-Instruct", "Qwen2.5-32B-Instruct", "Qwen2.5-14B-Instruct", "Qwen2.5-7B-Instruct",
            "Qwen2.5-72B-Chat", "Qwen2.5-32B-Chat", "Qwen2.5-14B-Chat", "Qwen2.5-7B-Chat",
            "Qwen2.5-72B", "Qwen2.5-32B", "Qwen2.5-14B", "Qwen2.5-7B",

            # 智谱系列模型
            "glm-4", "glm-4-9b", "glm-4v", "glm-4-air", "glm-4-airx",
            "glm-3-turbo", "glm-3-turbo-128k", "glm-3-turbo-1m",

            # 百度系列模型
            "ernie-bot-4", "ernie-bot", "ernie-bot-turbo",
            "ernie-speed", "ernie-lite", "ernie-tiny",

            # 阿里系列模型
            "qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext",
            "qwen-vl-plus", "qwen-vl-max",

            # 其他开源模型
            "Yi-VL-34B", "Yi-VL-6B", "Yi-34B-Chat", "Yi-6B-Chat",
            "Baichuan2-Turbo", "Baichuan2-Turbo-192k", "Baichuan2-Turbo-Max",
            "ChatGLM3-Turbo", "ChatGLM3-Turbo-128k", "ChatGLM3-Turbo-1m",
            "ChatGLM3-6B", "ChatGLM3-6B-32k",

            # 代码专用模型
            "CodeLlama-34B-Instruct", "CodeLlama-13B-Instruct", "CodeLlama-7B-Instruct",
            "WizardCoder-34B-V1.0", "WizardCoder-15B-V1.0", "WizardCoder-7B-V1.0",
            "CodeGeeX2-6B", "CodeGeeX2-13B",

            # 多模态模型
            "LLaVA-NeXT-34B", "LLaVA-NeXT-13B", "LLaVA-NeXT-7B",
            "CogVLM-17B", "CogVLM-6B", "CogVLM-3B",
            "InternLM-XComposer2-7B", "InternLM-XComposer2-4KHD-7B",

            # 轻量级模型
            "Phi-3.5-3.8B-Instruct", "Phi-3-3.8B-Instruct", "Phi-2-2.7B",
            "TinyLlama-1.1B-Chat-v1.0", "TinyLlama-1.1B-3T-v1.0",
            "Qwen1.5-0.5B-Chat", "Qwen1.5-1.8B-Chat", "Qwen1.5-4B-Chat",

            # 其他模型
            "DeepSeek-V2.5", "DeepSeek-V2", "DeepSeek-V1.5",
            "DeepSeek-MoE-16B", "DeepSeek-MoE-16B-Base",
            "DeepSeek-Coder-1.3B", "DeepSeek-Coder-6.7B-Base",
            "DeepSeek-Math-7B", "DeepSeek-Math-7B-Instruct",
            "DeepSeek-R1-InternLM2-20B", "DeepSeek-R1-InternLM2-7B"
        ]

        # 按优先级排序
        prioritized = []
        for priority_model in priority_order:
            if priority_model in models:
                prioritized.append(priority_model)

        # 添加其他未在优先级列表中的模型
        for model in models:
            if model not in prioritized:
                prioritized.append(model)

        return prioritized

    def _get_xiran_models(self) -> List[str]:
        """获取息壤一体智算平台的可用模型列表"""
        # 息壤平台包含几十个模型，按优先级排序
        return [
            # 最新高质量模型（优先）
            "DeepSeek-V3-0324", "DeepSeek-V3", "DeepSeek-V3-0324-Preview",
            "DeepSeek-R1", "DeepSeek-R1-Preview",
            "DeepSeek-Coder", "DeepSeek-Coder-33B", "DeepSeek-Coder-6.7B",

            # GPT系列模型
            "gpt-4o", "gpt-4o-mini", "gpt-4o-2024-05-13",
            "gpt-4-turbo", "gpt-4-turbo-2024-04-09", "gpt-4-turbo-preview",
            "gpt-4-0125-preview", "gpt-4-1106-preview", "gpt-4-0613",
            "gpt-4", "gpt-4-0314",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-0301", "gpt-3.5-turbo-instruct", "gpt-3.5-turbo-16k-0613",

            # 其他高质量模型
            "Qwen2.5-72B-Instruct", "Qwen2.5-32B-Instruct", "Qwen2.5-14B-Instruct", "Qwen2.5-7B-Instruct",
            "Qwen2.5-72B-Chat", "Qwen2.5-32B-Chat", "Qwen2.5-14B-Chat", "Qwen2.5-7B-Chat",
            "Qwen2.5-72B", "Qwen2.5-32B", "Qwen2.5-14B", "Qwen2.5-7B",

            # 智谱系列模型
            "glm-4", "glm-4-9b", "glm-4v", "glm-4-air", "glm-4-airx",
            "glm-3-turbo", "glm-3-turbo-128k", "glm-3-turbo-1m",

            # 百度系列模型
            "ernie-bot-4", "ernie-bot", "ernie-bot-turbo",
            "ernie-speed", "ernie-lite", "ernie-tiny",

            # 阿里系列模型
            "qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext",
            "qwen-vl-plus", "qwen-vl-max",

            # 其他开源模型
            "Yi-VL-34B", "Yi-VL-6B", "Yi-34B-Chat", "Yi-6B-Chat",
            "Baichuan2-Turbo", "Baichuan2-Turbo-192k", "Baichuan2-Turbo-Max",
            "ChatGLM3-Turbo", "ChatGLM3-Turbo-128k", "ChatGLM3-Turbo-1m",
            "ChatGLM3-6B", "ChatGLM3-6B-32k",

            # 代码专用模型
            "CodeLlama-34B-Instruct", "CodeLlama-13B-Instruct", "CodeLlama-7B-Instruct",
            "WizardCoder-34B-V1.0", "WizardCoder-15B-V1.0", "WizardCoder-7B-V1.0",
            "CodeGeeX2-6B", "CodeGeeX2-13B",

            # 多模态模型
            "LLaVA-NeXT-34B", "LLaVA-NeXT-13B", "LLaVA-NeXT-7B",
            "CogVLM-17B", "CogVLM-6B", "CogVLM-3B",
            "InternLM-XComposer2-7B", "InternLM-XComposer2-4KHD-7B",

            # 轻量级模型
            "Phi-3.5-3.8B-Instruct", "Phi-3-3.8B-Instruct", "Phi-2-2.7B",
            "TinyLlama-1.1B-Chat-v1.0", "TinyLlama-1.1B-3T-v1.0",
            "Qwen1.5-0.5B-Chat", "Qwen1.5-1.8B-Chat", "Qwen1.5-4B-Chat",

            # 其他模型
            "DeepSeek-V2.5", "DeepSeek-V2", "DeepSeek-V1.5",
            "DeepSeek-MoE-16B", "DeepSeek-MoE-16B-Base",
            "DeepSeek-Coder-1.3B", "DeepSeek-Coder-6.7B-Base",
            "DeepSeek-Math-7B", "DeepSeek-Math-7B-Instruct",
            "DeepSeek-R1-InternLM2-20B", "DeepSeek-R1-InternLM2-7B"
        ]

    def _prioritize_openai_models(self, models: List[str]) -> List[str]:
        """对OpenAI模型按优先级排序"""
        # 定义模型优先级（从高到低）
        priority_order = [
            # GPT-4o 系列（最新、最快、最经济）
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4o-2024-05-13",

            # GPT-4 Turbo 系列
            "gpt-4-turbo",
            "gpt-4-turbo-2024-04-09",
            "gpt-4-turbo-preview",
            "gpt-4-0125-preview",
            "gpt-4-1106-preview",
            "gpt-4-0613",

            # GPT-4 系列
            "gpt-4",
            "gpt-4-0314",

            # GPT-3.5 Turbo 系列
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-0301",

            # 其他模型
            "gpt-3.5-turbo-instruct",
            "gpt-3.5-turbo-16k-0613",
        ]

        # 按优先级排序
        prioritized = []
        for priority_model in priority_order:
            if priority_model in models:
                prioritized.append(priority_model)

        # 添加其他未在优先级列表中的模型
        for model in models:
            if model not in prioritized:
                prioritized.append(model)

        return prioritized

    def _get_default_openai_models(self) -> List[str]:
        """获取默认的OpenAI模型列表"""
        return [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
        ]

    def _get_model_performance_history(self) -> Dict:
        """获取模型性能历史数据"""
        # 这里应该从数据库或缓存中获取历史数据
        # 暂时返回模拟数据
        return {
            # DeepSeek 系列（息壤平台）
            "DeepSeek-V3-0324": {
                "avg_response_time": 2.8,
                "success_rate": 0.97,
                "avg_cost_per_request": 0.001,
                "quality_score": 8.8,
                "usage_count": 200
            },
            "DeepSeek-V3": {
                "avg_response_time": 2.9,
                "success_rate": 0.98,
                "avg_cost_per_request": 0.0012,
                "quality_score": 9.0,
                "usage_count": 180
            },
            "DeepSeek-R1": {
                "avg_response_time": 3.5,
                "success_rate": 0.96,
                "avg_cost_per_request": 0.0008,
                "quality_score": 8.2,
                "usage_count": 120
            },
            "DeepSeek-Coder": {
                "avg_response_time": 3.0,
                "success_rate": 0.98,
                "avg_cost_per_request": 0.0012,
                "quality_score": 8.5,
                "usage_count": 150
            },

            # GPT-4o 系列（息壤平台）
            "gpt-4o": {
                "avg_response_time": 2.8,
                "success_rate": 0.99,
                "avg_cost_per_request": 0.005,
                "quality_score": 9.5,
                "usage_count": 200
            },
            "gpt-4o-mini": {
                "avg_response_time": 2.5,
                "success_rate": 0.98,
                "avg_cost_per_request": 0.00015,
                "quality_score": 8.5,
                "usage_count": 150
            },

            # Qwen 系列（息壤平台）
            "Qwen2.5-72B-Instruct": {
                "avg_response_time": 4.2,
                "success_rate": 0.95,
                "avg_cost_per_request": 0.002,
                "quality_score": 8.8,
                "usage_count": 80
            },
            "Qwen2.5-32B-Instruct": {
                "avg_response_time": 3.8,
                "success_rate": 0.96,
                "avg_cost_per_request": 0.0015,
                "quality_score": 8.6,
                "usage_count": 100
            },
            "Qwen2.5-14B-Instruct": {
                "avg_response_time": 3.2,
                "success_rate": 0.97,
                "avg_cost_per_request": 0.001,
                "quality_score": 8.4,
                "usage_count": 120
            },
            "Qwen2.5-7B-Instruct": {
                "avg_response_time": 2.8,
                "success_rate": 0.98,
                "avg_cost_per_request": 0.0008,
                "quality_score": 8.2,
                "usage_count": 150
            },

            # 智谱系列（息壤平台）
            "glm-4": {
                "avg_response_time": 3.5,
                "success_rate": 0.96,
                "avg_cost_per_request": 0.002,
                "quality_score": 8.7,
                "usage_count": 90
            },
            "glm-3-turbo": {
                "avg_response_time": 2.5,
                "success_rate": 0.98,
                "avg_cost_per_request": 0.0008,
                "quality_score": 8.0,
                "usage_count": 180
            },

            # 百度系列（息壤平台）
            "ernie-bot-4": {
                "avg_response_time": 3.8,
                "success_rate": 0.95,
                "avg_cost_per_request": 0.0025,
                "quality_score": 8.5,
                "usage_count": 70
            },
            "ernie-bot": {
                "avg_response_time": 3.2,
                "success_rate": 0.97,
                "avg_cost_per_request": 0.0015,
                "quality_score": 8.2,
                "usage_count": 110
            },
            "ernie-bot-turbo": {
                "avg_response_time": 2.8,
                "success_rate": 0.98,
                "avg_cost_per_request": 0.001,
                "quality_score": 7.8,
                "usage_count": 140
            },

            # 阿里系列（息壤平台）
            "qwen-max": {
                "avg_response_time": 3.6,
                "success_rate": 0.96,
                "avg_cost_per_request": 0.002,
                "quality_score": 8.6,
                "usage_count": 85
            },
            "qwen-plus": {
                "avg_response_time": 3.0,
                "success_rate": 0.97,
                "avg_cost_per_request": 0.0012,
                "quality_score": 8.3,
                "usage_count": 115
            },
            "qwen-turbo": {
                "avg_response_time": 2.6,
                "success_rate": 0.98,
                "avg_cost_per_request": 0.0008,
                "quality_score": 7.9,
                "usage_count": 160
            },

            # 代码专用模型（息壤平台）
            "CodeLlama-34B-Instruct": {
                "avg_response_time": 4.0,
                "success_rate": 0.94,
                "avg_cost_per_request": 0.0022,
                "quality_score": 8.9,
                "usage_count": 75
            },
            "WizardCoder-34B-V1.0": {
                "avg_response_time": 3.8,
                "success_rate": 0.95,
                "avg_cost_per_request": 0.002,
                "quality_score": 8.7,
                "usage_count": 85
            },

            # 轻量级模型（息壤平台）
            "Phi-3.5-3.8B-Instruct": {
                "avg_response_time": 2.2,
                "success_rate": 0.99,
                "avg_cost_per_request": 0.0005,
                "quality_score": 7.5,
                "usage_count": 200
            },
            "Qwen1.5-4B-Chat": {
                "avg_response_time": 2.4,
                "success_rate": 0.98,
                "avg_cost_per_request": 0.0006,
                "quality_score": 7.8,
                "usage_count": 180
            },

            # 多模态模型（息壤平台）
            "LLaVA-NeXT-34B": {
                "avg_response_time": 4.5,
                "success_rate": 0.93,
                "avg_cost_per_request": 0.003,
                "quality_score": 8.8,
                "usage_count": 60
            },
            "CogVLM-17B": {
                "avg_response_time": 3.8,
                "success_rate": 0.95,
                "avg_cost_per_request": 0.0022,
                "quality_score": 8.5,
                "usage_count": 80
            }
        }

    def _calculate_model_score(self, model: str, task_info: Dict, performance_data: Dict) -> float:
        """计算模型的综合评分（改进版）"""
        if model not in performance_data:
            return 0.0

        perf = performance_data[model]
        capabilities = self._get_model_capabilities(model)
        task_type = task_info.get('task_type', 'general_analysis')

        # 根据任务类型动态调整权重
        weights = self._get_dynamic_weights(task_info, task_type)

        # 1. 性能评分
        performance_score = self._calculate_performance_score(perf, task_info)

        # 2. 成本评分
        cost_score = self._calculate_cost_score(perf, task_info, capabilities)

        # 3. 质量评分
        quality_score = self._calculate_quality_score(perf, task_info, capabilities)

        # 4. 任务适配评分（增强版）
        task_fit_score = self._calculate_enhanced_task_fit_score(model, task_info, capabilities)

        # 5. 多样性评分（避免总是选择同一个模型）
        diversity_score = self._calculate_diversity_score(model, task_type)

        # 综合评分
        total_score = (
            performance_score * weights['performance'] +
            cost_score * weights['cost'] +
            quality_score * weights['quality'] +
            task_fit_score * weights['task_fit'] +
            diversity_score * weights['diversity']
        )

        print(f"  统计 {model} 评分: 性能({performance_score:.2f}) 成本({cost_score:.2f}) 质量({quality_score:.2f}) 适配({task_fit_score:.2f}) 多样性({diversity_score:.2f}) = {total_score:.2f}")

        return total_score

    def _get_dynamic_weights(self, task_info: Dict, task_type: str) -> Dict[str, float]:
        """根据任务类型和特征动态调整权重"""
        base_weights = {
            'performance': 0.25,
            'cost': 0.20,
            'quality': 0.25,
            'task_fit': 0.25,
            'diversity': 0.05
        }

        # 根据任务类型调整权重
        if task_type == 'cost_sensitive':
            base_weights['cost'] = 0.35
            base_weights['performance'] = 0.20
            base_weights['quality'] = 0.20
            base_weights['task_fit'] = 0.20
        elif task_type == 'performance':
            base_weights['performance'] = 0.40
            base_weights['cost'] = 0.15
            base_weights['quality'] = 0.20
            base_weights['task_fit'] = 0.20
        elif task_type == 'high_quality':
            base_weights['quality'] = 0.40
            base_weights['performance'] = 0.20
            base_weights['cost'] = 0.15
            base_weights['task_fit'] = 0.20
        elif task_type == 'simple_tasks':
            base_weights['performance'] = 0.30
            base_weights['cost'] = 0.25
            base_weights['quality'] = 0.15
            base_weights['task_fit'] = 0.25
        elif task_type == 'chinese_content':
            base_weights['task_fit'] = 0.35
            base_weights['quality'] = 0.25
            base_weights['performance'] = 0.20
            base_weights['cost'] = 0.15

        # 根据成本敏感度调整
        cost_sensitivity = task_info.get('cost_sensitivity', 'medium')
        if cost_sensitivity == 'high':
            base_weights['cost'] += 0.10
            base_weights['performance'] -= 0.05
            base_weights['quality'] -= 0.05

        # 根据优先级调整
        priority = task_info.get('priority', 'normal')
        if priority == 'high':
            base_weights['performance'] += 0.10
            base_weights['cost'] -= 0.05
            base_weights['diversity'] -= 0.05

        return base_weights

    def _get_collaborative_models(self) -> Dict[str, List[str]]:
        """获取可用于协同分析的模型分类"""
        collaborative_models = {
            'performance': [],  # 性能优先模型
            'quality': [],      # 质量优先模型
            'cost': [],         # 成本优先模型
            'specialized': []   # 专业领域模型
        }
        
        # 获取所有可用模型
        all_models = []
        if self.use_openai:
            openai_models = self._get_available_models(self.openai_base_url)
            all_models.extend(openai_models)
        
        # 根据模型特性分类
        for model in all_models:
            capabilities = self._get_model_capabilities(model)
            
            # 性能优先模型（响应快、吞吐量高）
            if any(keyword in model.lower() for keyword in ['mini', 'turbo', 'fast', '4b', '8b']):
                collaborative_models['performance'].append(model)
            
            # 质量优先模型（高精度、大参数）
            elif any(keyword in model.lower() for keyword in ['4o', '32b', '72b', '235b', 'v3']):
                collaborative_models['quality'].append(model)
            
            # 成本优先模型（经济实惠）
            elif any(keyword in model.lower() for keyword in ['r1', '3.5', '7b', 'distill']):
                collaborative_models['cost'].append(model)
            
            # 专业领域模型（特定任务优化）
            elif any(keyword in model.lower() for keyword in ['code', 'math', 'reasoning', 'vision']):
                collaborative_models['specialized'].append(model)
            
            # 默认分类
            else:
                collaborative_models['quality'].append(model)
        
        return collaborative_models

    def _select_collaborative_models(self, task_info: Dict) -> List[str]:
        """选择用于协同分析的模型组合（优化版）"""
        print("\n协同 协同分析模型选择")
        print("=" * 50)
        
        collaborative_models = self._get_collaborative_models()
        selected_models = []
        
        # 根据任务类型和复杂度选择模型组合
        task_type = task_info.get('task_type', 'general_analysis')
        complexity = task_info.get('complexity', 'medium')
        
        print(f"信息 任务信息: {task_type} (复杂度: {complexity})")
        
        # 基础模型组合（每个类别选择最优的一个）
        base_models = []
        for category, models in collaborative_models.items():
            if models:
                # 选择该类别中评分最高的模型
                best_model = self._select_best_model_in_category(models, task_info, category)
                if best_model:
                    base_models.append(best_model)
                    print(f"成功 {category}: {best_model}")
        
        # 根据协同策略和任务特征调整模型组合
        if self.collaborative_strategy == 'ensemble':
            # 集成策略：根据任务复杂度动态调整
            if complexity == 'high':
                # 高复杂度任务：选择更多高质量模型
                priority_categories = ['quality', 'performance', 'specialized']
                max_models = 4
            elif complexity == 'low':
                # 低复杂度任务：选择成本效益好的模型
                priority_categories = ['cost', 'performance', 'quality']
                max_models = 2
            else:
                # 中等复杂度任务：平衡选择
                priority_categories = ['quality', 'performance', 'cost']
                max_models = 3
            
            for category in priority_categories:
                if category in collaborative_models and collaborative_models[category]:
                    best_model = self._select_best_model_in_category(collaborative_models[category], task_info, category)
                    if best_model and best_model not in selected_models and len(selected_models) < max_models:
                        selected_models.append(best_model)
        
        elif self.collaborative_strategy == 'weighted':
            # 加权策略：根据任务类型选择权重模型
            if task_type == 'code_analysis':
                # 代码分析：质量型 + 专业型
                categories = ['quality', 'specialized']
            elif task_type == 'chinese_content':
                # 中文内容：质量型 + 性能型
                categories = ['quality', 'performance']
            else:
                # 通用任务：质量型 + 性能型
                categories = ['quality', 'performance']
            
            for category in categories:
                if category in collaborative_models and collaborative_models[category]:
                    best_model = self._select_best_model_in_category(collaborative_models[category], task_info, category)
                    if best_model and best_model not in selected_models:
                        selected_models.append(best_model)
        
        elif self.collaborative_strategy == 'consensus':
            # 共识策略：选择多样化的模型组合
            if complexity == 'high':
                # 高复杂度：更多模型以获得更好的共识
                categories = ['quality', 'performance', 'specialized', 'cost']
                max_models = 4
            else:
                # 低/中等复杂度：平衡的模型组合
                categories = ['quality', 'performance', 'cost']
                max_models = 3
            
            for category in categories:
                if category in collaborative_models and collaborative_models[category]:
                    best_model = self._select_best_model_in_category(collaborative_models[category], task_info, category)
                    if best_model and best_model not in selected_models and len(selected_models) < max_models:
                        selected_models.append(best_model)
        
        elif self.collaborative_strategy == 'specialized':
            # 专业策略：根据任务类型选择专门的模型
            if task_type == 'code_analysis':
                # 代码分析任务：优先选择代码专用模型
                priority_categories = ['specialized', 'quality', 'performance']
            elif task_type == 'chinese_content':
                # 中文内容：优先选择中文优化模型
                priority_categories = ['quality', 'performance', 'cost']
            elif task_type == 'creative_writing':
                # 创意写作：优先选择创意型模型
                priority_categories = ['quality', 'specialized', 'performance']
            else:
                # 通用任务：平衡选择
                priority_categories = ['quality', 'performance', 'cost']
            
            for category in priority_categories:
                if category in collaborative_models and collaborative_models[category]:
                    best_model = self._select_best_model_in_category(collaborative_models[category], task_info, category)
                    if best_model and best_model not in selected_models:
                        selected_models.append(best_model)
        
        # 确保至少有一个模型
        if not selected_models and base_models:
            selected_models = [base_models[0]]
        
        print(f"\n选择 最终选择 {len(selected_models)} 个协同模型:")
        for i, model in enumerate(selected_models, 1):
            print(f"   {i}. {model}")
        
        return selected_models

    def _select_best_model_in_category(self, models: List[str], task_info: Dict, category: str) -> Optional[str]:
        """在指定类别中选择最佳模型"""
        if not models:
            return None
        
        best_model = None
        best_score = -1
        
        for model in models:
            try:
                score = self._calculate_model_score_by_strategy(model, task_info, {}, category)
                if score > best_score:
                    best_score = score
                    best_model = model
            except:
                continue
        
        return best_model

    def _collaborative_analysis(self, prompt: str, context: Dict) -> Dict:
        """多模型协同分析（性能优化版）"""
        print("\n协同 开始多模型协同分析")
        print("=" * 60)
        
        # 获取任务信息
        task_info = self._get_current_task_info()
        
        # 选择协同模型
        collaborative_models = self._select_collaborative_models(task_info)
        
        if not collaborative_models:
            print("失败 无可用协同模型，回退到单模型分析")
            return self._single_model_analysis(prompt, context)
        
        # 使用并发执行多个模型分析
        import concurrent.futures
        import time
        
        start_time = time.time()
        results = []
        
        print(f"执行 开始并发执行 {len(collaborative_models)} 个模型分析...")
        
        # 使用线程池执行并发分析（减少并发数量避免API限制）
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(collaborative_models), 2)) as executor:
            # 提交所有任务
            future_to_model = {
                executor.submit(self._analyze_with_model, model, prompt, context): model 
                for model in collaborative_models
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    results.append({
                        'model': model,
                        'result': result,
                        'status': 'success'
                    })
                    print(f"成功 {model} 分析完成")
                except Exception as e:
                    print(f"失败 {model} 分析失败: {e}")
                    results.append({
                        'model': model,
                        'result': None,
                        'status': 'failed',
                        'error': str(e)
                    })
        
        execution_time = time.time() - start_time
        print(f"时间 并发执行完成，耗时: {execution_time:.2f}秒")
        
        # 根据协同策略合并结果
        final_result = self._merge_collaborative_results(results, task_info)
        
        successful_count = len([r for r in results if r['status'] == 'success'])
        print(f"\n选择 协同分析完成，成功使用 {successful_count}/{len(collaborative_models)} 个模型")
        
        return final_result

    def _analyze_with_model(self, model: str, prompt: str, context: Dict) -> Dict:
        """使用指定模型进行分析"""
        # 根据模型类型选择分析方式
        if 'gpt' in model.lower() or 'deepseek' in model.lower() or 'qwen' in model.lower():
            return self._analyze_with_openai_model(model, prompt, context)
        elif 'gemini' in model.lower():
            return self._analyze_with_gemini_model(model, prompt, context)
        else:
            # 默认使用OpenAI方式
            return self._analyze_with_openai_model(model, prompt, context)

    def _analyze_with_openai_model(self, model: str, prompt: str, context: Dict) -> Dict:
        """使用OpenAI模型进行分析（优化版，支持缓存）"""
        # 检查缓存
        cache_context = {'model': model, 'temperature': 0.1}
        cached_result = get_cached_ai_result(prompt, cache_context)
        if cached_result is not None:
            print(f"AI缓存命中: {model}")
            return cached_result
        
        try:
            # 设置超时时间
            timeout = getattr(self, 'model_timeout', 60)
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的开源项目成熟度分析专家。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.1,
                timeout=timeout
            )
            
            result = {
                'content': response.choices[0].message.content,
                'model': model,
                'usage': response.usage.dict() if response.usage else {},
                'response_time': getattr(response, 'response_time', 0)
            }
            
            # 缓存结果
            cache_ai_result(prompt, result, model, cache_context)
            
            return result
        except Exception as e:
            # 记录错误并尝试重试
            print(f"警告 {model} 分析失败: {e}")
            if hasattr(self, 'auto_fallback') and self.auto_fallback:
                # 自动回退到备用模型
                return self._fallback_analysis(prompt, context, model)
            else:
                raise Exception(f"OpenAI模型 {model} 分析失败: {e}")
    
    def _fallback_analysis(self, prompt: str, context: Dict, failed_model: str) -> Dict:
        """备用分析方案"""
        print(f"回退 尝试备用分析方案...")
        
        # 尝试使用其他可用模型
        try:
            available_models = self._get_available_models(self.openai_base_url)
            fallback_models = [m for m in available_models if m != failed_model][:2]  # 最多尝试2个备用模型
            
            for fallback_model in fallback_models:
                try:
                    print(f"   回退 尝试备用模型: {fallback_model}")
                    return self._analyze_with_openai_model(fallback_model, prompt, context)
                except Exception as e:
                    print(f"   失败 备用模型 {fallback_model} 也失败: {e}")
                    continue
        except Exception as e:
            print(f"   失败 获取备用模型失败: {e}")
        
        # 所有模型都失败，返回默认响应
        return {
            'content': f"分析失败，无法使用模型 {failed_model} 进行分析。建议检查网络连接和API配置。",
            'model': 'fallback',
            'usage': {},
            'response_time': 0
        }

    def _analyze_with_gemini_model(self, model: str, prompt: str, context: Dict) -> Dict:
        """使用Gemini模型进行分析"""
        try:
            model_obj = genai.GenerativeModel(model)
            response = model_obj.generate_content(prompt)
            
            return {
                'content': response.text,
                'model': model,
                'usage': {}
            }
        except Exception as e:
            raise Exception(f"Gemini模型 {model} 分析失败: {e}")

    def _single_model_analysis(self, prompt: str, context: Dict) -> Dict:
        """单模型分析（回退方案）"""
        print("回退 尝试单模型分析...")
        
        # 按优先级尝试不同的AI方法
        if self.use_openai and self.openai_model:
            try:
                return self._analyze_with_openai_model(self.openai_model, prompt, context)
            except Exception as e:
                print(f"失败 OpenAI单模型分析失败: {e}")
        
        if self.use_gemini and self.gemini_model:
            try:
                return self._analyze_with_gemini_model(self.gemini_model, prompt, context)
            except Exception as e:
                print(f"失败 Gemini单模型分析失败: {e}")
        
        # 所有AI方法都失败，返回默认结果
        return {
            'content': "无法使用AI进行分析，请检查配置和网络连接。",
            'model': 'none',
            'usage': {},
            'response_time': 0
        }

    def _merge_collaborative_results(self, results: List[Dict], task_info: Dict) -> Dict:
        """合并协同分析结果"""
        successful_results = [r for r in results if r['status'] == 'success']
        
        if not successful_results:
            print("失败 所有协同模型分析都失败了，尝试单模型回退...")
            # 尝试使用单模型分析作为回退
            try:
                return self._single_model_analysis("请分析这个开源项目的成熟度", task_info)
            except Exception as e:
                print(f"失败 单模型回退也失败了: {e}")
                # 返回默认分析结果
                return {
                    'content': "由于所有AI模型都无法访问，无法进行AI分析。建议检查网络连接和API配置。",
                    'model': 'fallback',
                    'usage': {},
                    'response_time': 0,
                    'ai_confidence': 0.0,
                    'suggestions': ["检查网络连接", "验证API密钥", "确认模型可用性"]
                }
        
        if len(successful_results) == 1:
            # 只有一个成功结果，直接返回
            return successful_results[0]['result']
        
        # 多个结果，根据策略合并
        if self.collaborative_strategy == 'ensemble':
            return self._ensemble_merge(successful_results, task_info)
        elif self.collaborative_strategy == 'weighted':
            return self._weighted_merge(successful_results, task_info)
        else:
            return self._consensus_merge(successful_results, task_info)

    def _ensemble_merge(self, results: List[Dict], task_info: Dict) -> Dict:
        """集成合并策略"""
        print("回退 使用集成合并策略")
        
        # 提取所有分析内容
        contents = [r['result']['content'] for r in results]
        models = [r['model'] for r in results]
        
        # 创建集成提示
        ensemble_prompt = f"""
请综合分析以下多个AI模型的分析结果，生成一个综合的、高质量的最终分析：

模型分析结果：
{chr(10).join([f"模型 {i+1} ({models[i]}): {content}" for i, content in enumerate(contents)])}

请提供一个综合的分析结果，应该：
1. 整合所有模型的观点
2. 突出共识和分歧
3. 提供更全面和准确的评估
4. 保持客观和专业性

综合分析结果：
"""
        
        # 使用质量最高的模型进行最终整合
        best_model = self._select_best_model_in_category(models, task_info, 'quality')
        if not best_model:
            best_model = models[0]
        
        final_result = self._analyze_with_model(best_model, ensemble_prompt, {})
        
        return {
            'content': final_result['content'],
            'model': f"ensemble({', '.join(models)})",
            'usage': final_result.get('usage', {}),
            'collaborative_models': models
        }

    def _weighted_merge(self, results: List[Dict], task_info: Dict) -> Dict:
        """加权合并策略（优化版）"""
        print("回退 使用加权合并策略")
        
        # 根据任务类型和模型特性动态计算权重
        weights = []
        total_weight = 0
        task_type = task_info.get('task_type', 'general_analysis')
        
        for result in results:
            model = result['model']
            capabilities = self._get_model_capabilities(model)
            
            # 基础权重：模型质量
            base_weight = capabilities.get('quality', 5) / 10.0
            
            # 任务适配权重
            task_weight = 1.0
            if task_type == 'code_analysis':
                # 代码分析任务：优先选择代码专用模型
                if 'code' in model.lower() or 'wizard' in model.lower():
                    task_weight = 1.5
            elif task_type == 'chinese_content':
                # 中文内容：优先选择中文优化模型
                if 'qwen' in model.lower() or 'chinese' in model.lower():
                    task_weight = 1.3
            elif task_type == 'creative_writing':
                # 创意写作：优先选择创意型模型
                if 'creative' in model.lower() or 'gpt' in model.lower():
                    task_weight = 1.4
            
            # 性能权重：响应时间和成功率
            performance_weight = 1.0
            if capabilities.get('avg_response_time', 5) < 3:
                performance_weight = 1.2
            if capabilities.get('success_rate', 0.9) > 0.95:
                performance_weight *= 1.1
            
            # 综合权重
            final_weight = base_weight * task_weight * performance_weight
            weights.append(final_weight)
            total_weight += final_weight
        
        # 归一化权重
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(results)] * len(results)
        
        print(f"   统计 模型权重: {dict(zip([r['model'] for r in results], [f'{w:.3f}' for w in weights]))}")
        
        # 加权合并内容（选择权重最高的模型作为主要结果）
        best_model_idx = weights.index(max(weights))
        best_result = results[best_model_idx]
        
        return {
            'content': best_result['result']['content'],
            'model': f"weighted({', '.join([r['model'] for r in results])})",
            'usage': best_result['result'].get('usage', {}),
            'collaborative_models': [r['model'] for r in results],
            'weights': weights
        }

    def _consensus_merge(self, results: List[Dict], task_info: Dict) -> Dict:
        """共识合并策略"""
        print("回退 使用共识合并策略")
        
        # 选择最一致的结果
        contents = [r['result']['content'] for r in results]
        
        # 简单的相似度计算（实际可以使用更复杂的NLP方法）
        similarities = []
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                similarity = self._calculate_text_similarity(contents[i], contents[j])
                similarities.append(similarity)
        
        # 选择与其他结果最相似的结果作为共识
        if similarities:
            avg_similarities = []
            for i in range(len(contents)):
                similarity_sum = 0
                count = 0
                for j in range(len(contents)):
                    if i != j:
                        similarity_sum += similarities[min(i, j) * len(contents) + max(i, j) - min(i, j) - 1]
                        count += 1
                avg_similarities.append(similarity_sum / count if count > 0 else 0)
            
            best_idx = avg_similarities.index(max(avg_similarities))
            best_result = results[best_idx]
        else:
            best_result = results[0]
        
        return {
            'content': best_result['result']['content'],
            'model': f"consensus({', '.join([r['model'] for r in results])})",
            'usage': best_result['result'].get('usage', {}),
            'collaborative_models': [r['model'] for r in results]
        }

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版本）"""
        # 使用简单的词汇重叠度
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def _single_model_analysis(self, prompt: str, context: Dict) -> Dict:
        """单模型分析（回退方法）"""
        if self.ai_method == 'openai':
            return self._analyze_with_openai_model(self.openai_model, prompt, context)
        elif self.ai_method == 'gemini':
            return self._analyze_with_gemini_model(self.gemini_model, prompt, context)
        else:
            return self._rule_based_analysis(prompt, context)

    def _calculate_model_score_by_strategy(self, model: str, task_info: Dict, performance_data: Dict, strategy: str) -> float:
        """根据策略计算模型评分"""
        if model not in performance_data:
            return 0.0

        perf = performance_data[model]
        capabilities = self._get_model_capabilities(model)
        task_type = task_info.get('task_type', 'general_analysis')

        # 根据策略调整权重
        weights = self._get_strategy_weights(strategy, task_info)

        # 计算各项评分
        performance_score = self._calculate_performance_score(perf, task_info)
        cost_score = self._calculate_cost_score(perf, task_info, capabilities)
        quality_score = self._calculate_quality_score(perf, task_info, capabilities)
        task_fit_score = self._calculate_enhanced_task_fit_score(model, task_info, capabilities)
        diversity_score = self._calculate_diversity_score(model, task_type)

        # 根据策略调整评分
        if strategy == "performance":
            # 性能优先：强调响应时间和吞吐量
            performance_score *= 1.5
            cost_score *= 0.8
        elif strategy == "cost":
            # 成本优先：强调经济性
            cost_score *= 1.5
            performance_score *= 0.8
        elif strategy == "quality":
            # 质量优先：强调准确性和质量
            quality_score *= 1.5
            cost_score *= 0.7

        # 综合评分
        total_score = (
            performance_score * weights['performance'] +
            cost_score * weights['cost'] +
            quality_score * weights['quality'] +
            task_fit_score * weights['task_fit'] +
            diversity_score * weights['diversity']
        )

        # 显示详细评分
        print(f"   统计 {model}: 性能({performance_score:.2f}) 成本({cost_score:.2f}) 质量({quality_score:.2f}) 适配({task_fit_score:.2f}) 多样性({diversity_score:.2f}) = {total_score:.2f}")

        return total_score

    def _get_strategy_weights(self, strategy: str, task_info: Dict) -> Dict[str, float]:
        """根据策略获取权重配置"""
        if strategy == "performance":
            return {
                'performance': 0.40,
                'cost': 0.15,
                'quality': 0.20,
                'task_fit': 0.20,
                'diversity': 0.05
            }
        elif strategy == "cost":
            return {
                'performance': 0.15,
                'cost': 0.40,
                'quality': 0.15,
                'task_fit': 0.25,
                'diversity': 0.05
            }
        elif strategy == "quality":
            return {
                'performance': 0.15,
                'cost': 0.10,
                'quality': 0.40,
                'task_fit': 0.25,
                'diversity': 0.10
            }
        else:  # balanced
            return {
                'performance': 0.25,
                'cost': 0.20,
                'quality': 0.25,
                'task_fit': 0.25,
                'diversity': 0.05
            }

    def _select_best_model_by_strategy(self, model_scores: Dict[str, float], strategy: str) -> tuple:
        """根据策略选择最佳模型"""
        if not model_scores:
            return ("", 0.0)

        if strategy == "performance":
            # 性能优先：选择性能评分最高的模型
            best_model = max(model_scores.items(), key=lambda x: x[1])
            print(f"   最佳 性能优先选择: {best_model[0]} (评分: {best_model[1]:.2f})")
        elif strategy == "cost":
            # 成本优先：选择成本评分最高的模型
            best_model = max(model_scores.items(), key=lambda x: x[1])
            print(f"   最佳 成本优先选择: {best_model[0]} (评分: {best_model[1]:.2f})")
        elif strategy == "quality":
            # 质量优先：选择质量评分最高的模型
            best_model = max(model_scores.items(), key=lambda x: x[1])
            print(f"   最佳 质量优先选择: {best_model[0]} (评分: {best_model[1]:.2f})")
        else:  # balanced
            # 平衡策略：选择综合评分最高的模型
            best_model = max(model_scores.items(), key=lambda x: x[1])
            print(f"   最佳 平衡策略选择: {best_model[0]} (评分: {best_model[1]:.2f})")

        return best_model

    def _show_selection_reason(self, model: str, score: float, strategy: str, task_info: Dict):
        """显示选择原因"""
        print(f"\n信息 选择原因分析:")
        print(f"   选择 策略: {strategy}")
        print(f"   统计 综合评分: {score:.2f}")

        # 获取模型能力信息
        capabilities = self._get_model_capabilities(model)
        print(f"   🔧 模型能力:")
        print(f"      - 最大token: {capabilities.get('max_tokens', 'N/A')}")
        print(f"      - 速度: {capabilities.get('speed', 'N/A')}")
        print(f"      - 质量: {capabilities.get('quality', 'N/A')}")
        print(f"      - 最佳用途: {capabilities.get('best_use', 'N/A')}")

        # 根据策略显示特定优势
        if strategy == "performance":
            print(f"   性能 性能优势: 响应速度快，适合实时交互")
        elif strategy == "cost":
            print(f"   成本 成本优势: 经济实惠，适合大规模使用")
        elif strategy == "quality":
            print(f"   质量 质量优势: 输出质量高，适合复杂任务")
        else:
            print(f"   平衡 平衡优势: 综合考虑各项指标")

        print(f"   📝 任务类型: {task_info.get('task_type', 'N/A')}")
        print(f"   选择 任务复杂度: {task_info.get('complexity', 'N/A')}")

    def _calculate_enhanced_task_fit_score(self, model: str, task_info: Dict, capabilities: Dict) -> float:
        """增强的任务适配评分"""
        task_type = task_info.get('task_type', 'general_analysis')
        content_length = task_info.get('content_length', 5000)
        complexity = task_info.get('complexity', 'medium')

        # 基础任务适配评分
        base_score = self._calculate_task_fit_score(model, task_info, capabilities)

        # 任务类型特定加分
        task_bonus = 0.0

        if task_type == 'code_analysis':
            if 'code' in model.lower() or 'coder' in model.lower():
                task_bonus += 2.0
        elif task_type == 'chinese_content':
            if any(keyword in model.lower() for keyword in ['glm', 'ernie', 'qwen']):
                task_bonus += 2.0
        elif task_type == 'cost_sensitive':
            if any(keyword in model.lower() for keyword in ['r1', 'turbo', 'mini']):
                task_bonus += 1.5
        elif task_type == 'performance':
            if any(keyword in model.lower() for keyword in ['mini', 'turbo', 'fast']):
                task_bonus += 1.5
        elif task_type == 'high_quality':
            if any(keyword in model.lower() for keyword in ['v3', '72b', '4']):
                task_bonus += 2.0

        return min(base_score + task_bonus, 10.0)

    def _calculate_diversity_score(self, model: str, task_type: str) -> float:
        """计算多样性评分，避免总是选择同一个模型"""
        # 这里可以基于历史选择记录来计算
        # 暂时返回一个基于模型名称的随机性评分
        hash_value = int(hashlib.md5(f"{model}_{task_type}".encode()).hexdigest()[:8], 16)
        return (hash_value % 100) / 10.0  # 0-10的随机评分

    def _calculate_performance_score(self, perf: Dict, task_info: Dict) -> float:
        """计算性能评分"""
        # 响应时间评分 (越快越好)
        response_time_score = max(0, 10 - perf.get('avg_response_time', 5))

        # 成功率评分
        success_rate_score = perf.get('success_rate', 0.9) * 10

        # 根据任务优先级调整
        priority_multiplier = {
            'high': 1.2,
            'normal': 1.0,
            'low': 0.8
        }.get(task_info.get('priority', 'normal'), 1.0)

        return (response_time_score + success_rate_score) / 2 * priority_multiplier

    def _calculate_cost_score(self, perf: Dict, task_info: Dict, capabilities: Dict) -> float:
        """计算成本评分"""
        cost_per_request = perf.get('avg_cost_per_request', 0.005)

        # 基础成本评分 (成本越低越好)
        base_cost_score = max(0, 10 - cost_per_request * 1000)

        # 根据成本敏感度调整
        sensitivity_multiplier = {
            'high': 1.3,
            'medium': 1.0,
            'low': 0.7
        }.get(task_info.get('cost_sensitivity', 'medium'), 1.0)

        return base_cost_score * sensitivity_multiplier

    def _calculate_quality_score(self, perf: Dict, task_info: Dict, capabilities: Dict) -> float:
        """计算质量评分"""
        # 历史质量评分
        historical_quality = perf.get('quality_score', 7.0)

        # 模型能力质量
        model_quality = {
            'excellent': 9.5,
            'good': 8.0,
            'medium': 6.5,
            'poor': 4.0
        }.get(capabilities.get('quality', 'good'), 7.0)

        # 根据质量要求调整
        quality_requirement = task_info.get('quality_requirement', 'good')
        requirement_multiplier = {
            'excellent': 1.2,
            'good': 1.0,
            'basic': 0.8
        }.get(quality_requirement, 1.0)

        return (historical_quality + model_quality) / 2 * requirement_multiplier

    def _calculate_task_fit_score(self, model: str, task_info: Dict, capabilities: Dict) -> float:
        """计算任务适配评分"""
        task_type = task_info.get('task_type', 'general_analysis')
        content_length = task_info.get('content_length', 5000)
        complexity = task_info.get('complexity', 'medium')

        # 任务类型适配
        best_for = capabilities.get('best_for', [])
        type_match = 0.0
        if task_type in best_for:
            type_match = 10.0
        elif any(keyword in task_type for keyword in best_for):
            type_match = 8.0
        else:
            type_match = 5.0

        # 内容长度适配
        max_tokens = capabilities.get('max_tokens', 16385)
        length_ratio = min(content_length / max_tokens, 1.0)
        length_score = 10.0 if length_ratio < 0.8 else (10.0 - (length_ratio - 0.8) * 20)

        # 复杂度适配
        complexity_score = 10.0
        if complexity == 'high' and capabilities.get('quality') == 'excellent':
            complexity_score = 10.0
        elif complexity == 'medium' and capabilities.get('quality') in ['excellent', 'good']:
            complexity_score = 9.0
        elif complexity == 'low':
            complexity_score = 8.0

        return (type_match + length_score + complexity_score) / 3

    def _get_fallback_model(self, base_url: str) -> str:
        """获取备用模型"""
        if 'wishub-x1.ctyun.cn' in base_url or 'deepseek' in base_url.lower():
            return "DeepSeek-V3-0324"
        elif 'openai' in base_url.lower():
            return "gpt-4o-mini"
        else:
            return "gpt-4o-mini"

    def _update_model_performance(self, model: str, response_time: float, success: bool, cost: float, quality_score: float):
        """更新模型性能数据"""
        # 这里应该将性能数据保存到数据库或缓存中
        # 用于下次智能选择时参考
        print(f"更新 更新模型性能数据: {model} - 响应时间:{response_time:.2f}s, 成功:{success}, 成本:${cost:.4f}, 质量:{quality_score:.1f}")

        # 实际实现中应该：
        # 1. 保存到数据库
        # 2. 更新缓存
        # 3. 触发重新评估

    def _select_model_by_task_complexity(self, task_type: str, content_length: int) -> str:
        """根据任务复杂度和内容长度智能选择模型"""
        # 任务复杂度评估
        if task_type in ['code_analysis', 'security_audit', 'complex_review']:
            # 复杂任务：需要高质量模型
            if content_length > 10000:
                return "gpt-4o"  # 长内容+复杂任务
            else:
                return "gpt-4o-mini"  # 短内容+复杂任务
        elif task_type in ['simple_analysis', 'basic_review']:
            # 简单任务：可以使用经济模型
            if content_length > 5000:
                return "gpt-4o-mini"  # 长内容+简单任务
            else:
                return "gpt-3.5-turbo"  # 短内容+简单任务
        else:
            # 默认选择
            return "gpt-4o-mini"

    def _get_model_capabilities(self, model_name: str) -> Dict:
        """获取模型能力信息"""
        capabilities = {
            # DeepSeek 系列（息壤平台）
            "DeepSeek-V3-0324": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0001,
                "speed": "fast",
                "quality": "excellent",
                "best_for": ["code_analysis", "chinese_content", "cost_effective", "complex_analysis"]
            },
            "DeepSeek-V3": {
                "max_tokens": 128000,
                "cost_per_1k": 0.00012,
                "speed": "fast",
                "quality": "excellent",
                "best_for": ["code_analysis", "chinese_content", "complex_analysis"]
            },
            "DeepSeek-R1": {
                "max_tokens": 128000,
                "cost_per_1k": 0.00008,
                "speed": "medium",
                "quality": "good",
                "best_for": ["general_analysis", "stable", "cost_effective"]
            },
            "DeepSeek-Coder": {
                "max_tokens": 128000,
                "cost_per_1k": 0.00012,
                "speed": "fast",
                "quality": "excellent",
                "best_for": ["code_analysis", "programming", "technical_content"]
            },

            # GPT-4o 系列（息壤平台）
            "gpt-4o": {
                "max_tokens": 128000,
                "cost_per_1k": 0.005,
                "speed": "fast",
                "quality": "excellent",
                "best_for": ["complex_analysis", "long_content", "high_quality", "code_analysis"]
            },
            "gpt-4o-mini": {
                "max_tokens": 128000,
                "cost_per_1k": 0.00015,
                "speed": "very_fast",
                "quality": "good",
                "best_for": ["general_analysis", "cost_effective", "fast_response", "simple_analysis"]
            },

            # Qwen 系列（息壤平台）
            "Qwen2.5-72B-Instruct": {
                "max_tokens": 128000,
                "cost_per_1k": 0.002,
                "speed": "slow",
                "quality": "excellent",
                "best_for": ["complex_analysis", "high_quality", "long_content"]
            },
            "Qwen2.5-32B-Instruct": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0015,
                "speed": "medium",
                "quality": "excellent",
                "best_for": ["complex_analysis", "high_quality"]
            },
            "Qwen2.5-14B-Instruct": {
                "max_tokens": 128000,
                "cost_per_1k": 0.001,
                "speed": "fast",
                "quality": "good",
                "best_for": ["general_analysis", "balanced"]
            },
            "Qwen2.5-7B-Instruct": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0008,
                "speed": "very_fast",
                "quality": "good",
                "best_for": ["simple_analysis", "cost_effective", "fast_response"]
            },

            # 智谱系列（息壤平台）
            "glm-4": {
                "max_tokens": 128000,
                "cost_per_1k": 0.002,
                "speed": "medium",
                "quality": "excellent",
                "best_for": ["complex_analysis", "chinese_content", "high_quality"]
            },
            "glm-3-turbo": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0008,
                "speed": "fast",
                "quality": "good",
                "best_for": ["general_analysis", "chinese_content", "cost_effective"]
            },

            # 百度系列（息壤平台）
            "ernie-bot-4": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0025,
                "speed": "medium",
                "quality": "excellent",
                "best_for": ["complex_analysis", "chinese_content", "high_quality"]
            },
            "ernie-bot": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0015,
                "speed": "fast",
                "quality": "good",
                "best_for": ["general_analysis", "chinese_content"]
            },
            "ernie-bot-turbo": {
                "max_tokens": 128000,
                "cost_per_1k": 0.001,
                "speed": "very_fast",
                "quality": "good",
                "best_for": ["simple_analysis", "chinese_content", "cost_effective"]
            },

            # 阿里系列（息壤平台）
            "qwen-max": {
                "max_tokens": 128000,
                "cost_per_1k": 0.002,
                "speed": "medium",
                "quality": "excellent",
                "best_for": ["complex_analysis", "chinese_content", "high_quality"]
            },
            "qwen-plus": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0012,
                "speed": "fast",
                "quality": "good",
                "best_for": ["general_analysis", "chinese_content"]
            },
            "qwen-turbo": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0008,
                "speed": "very_fast",
                "quality": "good",
                "best_for": ["simple_analysis", "chinese_content", "cost_effective"]
            },

            # 代码专用模型（息壤平台）
            "CodeLlama-34B-Instruct": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0022,
                "speed": "slow",
                "quality": "excellent",
                "best_for": ["code_analysis", "programming", "technical_content"]
            },
            "WizardCoder-34B-V1.0": {
                "max_tokens": 128000,
                "cost_per_1k": 0.002,
                "speed": "slow",
                "quality": "excellent",
                "best_for": ["code_analysis", "programming", "technical_content"]
            },

            # 轻量级模型（息壤平台）
            "Phi-3.5-3.8B-Instruct": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0005,
                "speed": "very_fast",
                "quality": "good",
                "best_for": ["simple_analysis", "cost_effective", "fast_response"]
            },
            "Qwen1.5-4B-Chat": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0006,
                "speed": "very_fast",
                "quality": "good",
                "best_for": ["simple_analysis", "chinese_content", "cost_effective"]
            },

            # 多模态模型（息壤平台）
            "LLaVA-NeXT-34B": {
                "max_tokens": 128000,
                "cost_per_1k": 0.003,
                "speed": "slow",
                "quality": "excellent",
                "best_for": ["multimodal_analysis", "image_understanding", "complex_analysis"]
            },
            "CogVLM-17B": {
                "max_tokens": 128000,
                "cost_per_1k": 0.0022,
                "speed": "medium",
                "quality": "excellent",
                "best_for": ["multimodal_analysis", "image_understanding", "general_analysis"]
            }
        }
        return capabilities.get(model_name, capabilities["gpt-4o-mini"])

    def _select_best_gemini_model(self) -> str:
        """自动选择最佳Gemini模型"""
        # 预定义的模型优先级（按性能、配额、稳定性排序）
        model_priority = [
            "gemini-1.5-flash",      # 快速、高配额
            "gemini-1.5-pro",        # 高质量
            "gemini-2.0-flash",      # 新版本
            "gemini-1.5-flash-latest", # 最新版本
        ]

        # 如果配置中指定了模型，优先使用
        configured_model = self.gemini_config.get('model')
        if configured_model:
            print(f"信息 使用配置指定的Gemini模型: {configured_model}")
            return configured_model

        # 自动测试模型可用性
        print("检测 自动选择最佳Gemini模型...")
        for model_name in model_priority:
            try:
                model = genai.GenerativeModel(model_name)
                # 简单的连接测试
                response = model.generate_content("test")
                print(f"成功 选择Gemini模型: {model_name}")
                return model_name
            except Exception as e:
                print(f"失败 模型 {model_name} 不可用: {str(e)[:50]}...")
                continue

        # 如果所有模型都不可用，尝试获取可用模型列表
        try:
            models = genai.list_models()
            available_models = [model.name for model in models if 'generateContent' in model.supported_generation_methods]
            if available_models:
                # 选择第一个可用的模型
                fallback_model = available_models[0].replace('models/', '')
                print(f"警告 使用备用Gemini模型: {fallback_model}")
                return fallback_model
        except Exception as e:
            print(f"警告 无法获取可用模型列表: {e}")

        # 最后的备用方案
        default_model = "gemini-1.5-flash"
        print(f"警告 使用默认Gemini模型: {default_model}")
        return default_model

    def _test_openai_connection(self) -> bool:
        """测试OpenAI/DeepSeek连接是否可用"""
        try:
            # 简单的连接测试
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            print(f"警告 OpenAI/DeepSeek连接测试失败: {e}")
            return False

    def _test_gemini_connection(self) -> bool:
        """测试Gemini连接是否可用"""
        try:
            # 简单的连接测试
            response = self.gemini_model.generate_content("test")
            return True
        except Exception as e:
            print(f"警告 Gemini连接测试失败: {e}")
            return False

    def _load_analysis_rules(self) -> Dict:
        """加载分析规则"""
        return {
            'code_quality': {
                'excellent': {'score_range': (85, 100), 'indicators': ['pylint_score > 90', 'sonarqube_score > 85']},
                'good': {'score_range': (70, 85), 'indicators': ['pylint_score > 70', 'sonarqube_score > 70']},
                'fair': {'score_range': (50, 70), 'indicators': ['pylint_score > 50', 'sonarqube_score > 50']},
                'poor': {'score_range': (0, 50), 'indicators': ['pylint_score < 50', 'sonarqube_score < 50']}
            },
            'test_coverage': {
                'excellent': {'score_range': (90, 100), 'indicators': ['coverage > 90%', 'test_files > 10']},
                'good': {'score_range': (70, 90), 'indicators': ['coverage > 70%', 'test_files > 5']},
                'fair': {'score_range': (50, 70), 'indicators': ['coverage > 50%', 'test_files > 2']},
                'poor': {'score_range': (0, 50), 'indicators': ['coverage < 50%', 'test_files < 2']}
            },
            'security': {
                'excellent': {'score_range': (90, 100), 'indicators': ['security_issues = 0', 'has_security_config']},
                'good': {'score_range': (70, 90), 'indicators': ['security_issues < 5', 'has_security_config']},
                'fair': {'score_range': (50, 70), 'indicators': ['security_issues < 10']},
                'poor': {'score_range': (0, 50), 'indicators': ['security_issues > 10']}
            },
            'documentation': {
                'excellent': {'score_range': (85, 100), 'indicators': ['readme_quality > 80', 'doc_files > 5']},
                'good': {'score_range': (70, 85), 'indicators': ['readme_quality > 60', 'doc_files > 3']},
                'fair': {'score_range': (50, 70), 'indicators': ['readme_quality > 40', 'doc_files > 1']},
                'poor': {'score_range': (0, 50), 'indicators': ['readme_quality < 40', 'doc_files = 0']}
            },
            'build_reproducibility': {
                'excellent': {'score_range': (85, 100), 'indicators': ['docker_support', 'build_scripts', 'dependency_management']},
                'good': {'score_range': (70, 85), 'indicators': ['docker_support', 'basic_build_scripts']},
                'fair': {'score_range': (50, 70), 'indicators': ['basic_build_scripts']},
                'poor': {'score_range': (0, 50), 'indicators': ['no_build_system']}
            },
            'dependencies_license': {
                'excellent': {'score_range': (85, 100), 'indicators': ['license_file', 'dependency_management', 'license_compliance']},
                'good': {'score_range': (70, 85), 'indicators': ['license_file', 'dependency_management']},
                'fair': {'score_range': (50, 70), 'indicators': ['license_file']},
                'poor': {'score_range': (0, 50), 'indicators': ['no_license']}
            },
            'cicd': {
                'excellent': {'score_range': (85, 100), 'indicators': ['automated_tests', 'deployment_pipeline', 'quality_gates']},
                'good': {'score_range': (70, 85), 'indicators': ['automated_tests', 'basic_pipeline']},
                'fair': {'score_range': (50, 70), 'indicators': ['basic_ci']},
                'poor': {'score_range': (0, 50), 'indicators': ['no_automation']}
            }
        }

    def _load_maturity_patterns(self) -> Dict:
        """加载成熟度模式"""
        return {
            'enterprise_ready': {
                'min_score': 80,
                'required_dimensions': ['code_quality', 'test_coverage', 'security', 'ci_cd'],
                'indicators': ['docker_support', 'automated_tests', 'security_scanning', 'documentation']
            },
            'production_ready': {
                'min_score': 70,
                'required_dimensions': ['code_quality', 'test_coverage', 'documentation'],
                'indicators': ['test_coverage', 'documentation', 'license']
            },
            'development_ready': {
                'min_score': 50,
                'required_dimensions': ['code_quality'],
                'indicators': ['basic_structure', 'readme']
            },
            'experimental': {
                'min_score': 30,
                'required_dimensions': [],
                'indicators': ['basic_code']
            }
        }

    def analyze_dimension_with_openai(self, dimension_name: str, dimension_data: Dict) -> Dict:
        """使用OpenAI/DeepSeek AI分析单个维度"""
        prompt = self._create_dimension_prompt(dimension_name, dimension_data)

        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            stream=self.openai_config.get('stream', False)
        )

        # 获取响应内容
        if self.openai_config.get('stream', False):
            content = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content += chunk.choices[0].delta.content
        else:
            content = response.choices[0].message.content

        # 解析OpenAI响应
        analysis = self._parse_openai_response(content, dimension_name)
        return analysis

    def _parse_openai_response(self, response_text: str, dimension_name: str) -> Dict:
        """解析OpenAI/DeepSeek响应"""
        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    'quality_level': analysis.get('quality_level', 'fair'),
                    'score_analysis': analysis.get('score_analysis', ''),
                    'suggestions': analysis.get('suggestions', []),
                    'improvement_path': analysis.get('improvement_path', {}),
                    'ai_confidence': analysis.get('ai_confidence', 0.8)
                }
        except Exception as e:
            print(f"警告 解析OpenAI/DeepSeek响应失败: {e}")

        # 回退到规则分析
        return self.analyze_dimension_with_rules(dimension_name, {})

    def analyze_dimension_with_gemini(self, dimension_name: str, dimension_data: Dict) -> Dict:
        """使用Gemini AI分析单个维度"""
        prompt = self._create_dimension_prompt(dimension_name, dimension_data)
        response = self.gemini_model.generate_content(prompt)

        # 解析Gemini响应
        analysis = self._parse_gemini_response(response.text, dimension_name)
        return analysis

    def _create_dimension_prompt(self, dimension_name: str, dimension_data: Dict) -> str:
        """创建维度分析提示"""
        score = dimension_data.get('score', 0)
        details = dimension_data.get('details', {})
        tool_execution_results = dimension_data.get('tool_execution_results', {})

        # 构建工具执行结果摘要
        tool_results_summary = ""
        if tool_execution_results:
            tool_results_summary = "\n\n工具执行结果详情：\n"
            for tool_name, tool_result in tool_execution_results.items():
                if tool_result.get('success', False):
                    # 工具执行成功，提供详细结果
                    execution_time = tool_result.get('execution_time', 0)
                    result_data = tool_result.get('result', {})
                    
                    tool_results_summary += f"""
- {tool_name} (✅ 执行成功, 耗时: {execution_time:.2f}s):
  工具检测结果: {json.dumps(result_data, ensure_ascii=False, indent=4) if result_data else '无具体数据'}
"""
                else:
                    # 工具执行失败，提供错误信息
                    error_msg = tool_result.get('error', '未知错误')
                    return_code = tool_result.get('return_code', -1)
                    
                    tool_results_summary += f"""
- {tool_name} (❌ 执行失败, 退出码: {return_code}):
  错误信息: {error_msg}
"""

        prompt = f"""
请基于工具执行结果分析这个开源项目的{dimension_name}维度。

维度基础信息：
- 维度名称：{dimension_name}
- 评分：{score}/100
- 状态：{dimension_data.get('status', 'N/A')}
- 使用工具：{', '.join(dimension_data.get('tools_used', []))}

基础分析数据：{json.dumps(details, ensure_ascii=False, indent=2)}
{tool_results_summary}

请基于上述工具执行结果进行专业分析，特别关注：
1. 成功执行的工具检测出的具体问题和指标
2. 失败工具可能对分析准确性的影响
3. 根据工具检测的具体结果调整评估

请提供以下分析（用JSON格式返回）：
{{
    "quality_level": "excellent/good/fair/poor",
    "score_analysis": "结合工具检测结果的详细分析，重点分析具体检测出的问题和指标",
    "suggestions": ["基于工具检测结果的具体改进建议1", "改进建议2", "改进建议3"],
    "improvement_path": {{
        "current_state": "基于工具检测结果的当前状态描述",
        "target_state": "目标状态描述",
        "steps": ["基于检测结果的具体步骤1", "步骤2", "步骤3"]
    }},
    "tool_insights": "对工具执行结果的综合洞察和解读",
    "ai_confidence": 0.85
}}

请确保返回的是有效的JSON格式。
"""
        return prompt

    def _parse_gemini_response(self, response_text: str, dimension_name: str) -> Dict:
        """解析Gemini响应"""
        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    'quality_level': analysis.get('quality_level', 'fair'),
                    'score_analysis': analysis.get('score_analysis', ''),
                    'suggestions': analysis.get('suggestions', []),
                    'improvement_path': analysis.get('improvement_path', {}),
                    'ai_confidence': analysis.get('ai_confidence', 0.8)
                }
        except Exception as e:
            print(f"警告 解析Gemini响应失败: {e}")

        # 回退到规则分析
        return self.analyze_dimension_with_rules(dimension_name, {})

    def analyze_dimension_with_rules(self, dimension_name: str, dimension_data: Dict) -> Dict:
        """使用规则分析单个维度"""
        score = dimension_data.get('score', 0)
        details = dimension_data.get('details', {})

        # 获取维度规则
        rules = self.analysis_rules.get(dimension_name, {})

        # 确定质量等级
        quality_level = 'poor'
        for level, rule in rules.items():
            if rule['score_range'][0] <= score <= rule['score_range'][1]:
                quality_level = level
                break

        # 生成AI分析建议
        suggestions = self._generate_suggestions(dimension_name, score, details, quality_level)

        # 生成改进路径
        improvement_path = self._generate_improvement_path(dimension_name, score, quality_level)

        return {
            'quality_level': quality_level,
            'score_analysis': self._analyze_score(score, dimension_name),
            'suggestions': suggestions,
            'improvement_path': improvement_path,
            'ai_confidence': self._calculate_confidence(score, details)
        }

    def analyze_dimension(self, dimension_name: str, dimension_data: Dict) -> Dict:
        """分析单个维度（支持协同分析）"""
        if self.ai_method == 'collaborative':
            try:
                print(f"      使用多模型协同分析...")
                return self.analyze_dimension_with_collaborative(dimension_name, dimension_data)
            except Exception as e:
                print(f"      警告 协同分析失败，回退到单模型分析: {e}")
                # 回退到单模型分析
                self.ai_method = self._determine_ai_method()
        
        # 单模型分析（按优先级尝试AI方法）
        for method in self.ai_priority:
            if method == 'openai' and self.use_openai:
                try:
                    print(f"      AI 使用OpenAI/DeepSeek分析...")
                    return self.analyze_dimension_with_openai(dimension_name, dimension_data)
                except Exception as e:
                    print(f"      警告 OpenAI/DeepSeek分析失败，尝试下一个AI方法: {e}")
                    continue
            elif method == 'gemini' and self.use_gemini:
                try:
                    print(f"      AI 使用Gemini分析...")
                    return self.analyze_dimension_with_gemini(dimension_name, dimension_data)
                except Exception as e:
                    print(f"      警告 Gemini分析失败，尝试下一个AI方法: {e}")
                    continue
            elif method == 'rules':
                print(f"      AI 使用规则分析...")
                return self.analyze_dimension_with_rules(dimension_name, dimension_data)

        # 如果所有方法都失败，回退到规则分析
        print(f"      AI 回退到规则分析...")
        return self.analyze_dimension_with_rules(dimension_name, dimension_data)

    def analyze_dimension_with_collaborative(self, dimension_name: str, dimension_data: Dict) -> Dict:
        """使用多模型协同分析单个维度"""
        # 构建分析提示
        prompt = self._build_dimension_prompt(dimension_name, dimension_data)
        
        # 执行协同分析
        result = self._collaborative_analysis(prompt, dimension_data)
        
        # 解析分析结果
        analysis_result = self._parse_ai_analysis_result(result['content'], dimension_name)
        
        # 添加协同分析信息
        analysis_result['collaborative_info'] = {
            'strategy': self.collaborative_strategy,
            'models_used': result.get('collaborative_models', []),
            'model': result.get('model', 'collaborative'),
            'usage': result.get('usage', {})
        }
        
        return analysis_result

    def _build_dimension_prompt(self, dimension_name: str, dimension_data: Dict) -> str:
        """构建维度分析提示"""
        tool_execution_results = dimension_data.get('tool_execution_results', {})
        
        # 构建工具执行结果摘要
        tool_results_summary = ""
        if tool_execution_results:
            tool_results_summary = "\n\n工具执行结果详情：\n"
            for tool_name, tool_result in tool_execution_results.items():
                if tool_result.get('success', False):
                    # 工具执行成功，提供详细结果
                    execution_time = tool_result.get('execution_time', 0)
                    result_data = tool_result.get('result', {})
                    
                    tool_results_summary += f"""
- {tool_name} (✅ 执行成功, 耗时: {execution_time:.2f}s):
  检测结果: {json.dumps(result_data, ensure_ascii=False, indent=4) if result_data else '无具体数据'}
"""
                else:
                    # 工具执行失败，提供错误信息
                    error_msg = tool_result.get('error', '未知错误')
                    return_code = tool_result.get('return_code', -1)
                    
                    tool_results_summary += f"""
- {tool_name} (❌ 执行失败, 退出码: {return_code}):
  错误信息: {error_msg}
"""

        prompt = f"""
请基于工具执行结果分析以下开源项目的{dimension_name}维度：

项目信息：
- 项目名称：{dimension_data.get('project_name', 'Unknown')}
- 项目路径：{dimension_data.get('project_path', 'Unknown')}
- 评分：{dimension_data.get('score', 0)}/100
- 使用工具：{', '.join(dimension_data.get('tools_used', []))}

维度基础数据：
{json.dumps(dimension_data.get('details', {}), ensure_ascii=False, indent=2)}
{tool_results_summary}

请基于工具检测结果进行分析，特别关注：
1. 成功执行的工具检测出的具体问题和指标
2. 失败工具可能对分析准确性的影响
3. 根据工具检测的具体结果进行状态评估

请从以下方面进行分析：
1. 当前状态评估（优秀/良好/一般/较差） - 基于工具检测结果
2. 具体得分（0-100分） - 结合工具检测调整
3. 优势分析 - 基于工具成功检测的良好指标
4. 问题识别 - 基于工具检测的具体问题
5. 改进建议（3-5条具体建议） - 基于工具检测结果
6. 改进路径（短期、中期、长期目标）

请以JSON格式返回分析结果，包含以下字段：
- score: 得分（0-100）
- quality_level: 质量等级（excellent/good/fair/poor）
- analysis: 详细分析（结合工具检测结果）
- strengths: 优势列表
- issues: 问题列表（基于工具检测）
- suggestions: 改进建议列表（基于工具检测结果）
- improvement_path: 改进路径
- tool_insights: 工具检测结果的综合洞察

分析结果：
"""
        return prompt

    def _parse_ai_analysis_result(self, content: str, dimension_name: str) -> Dict:
        """解析AI分析结果"""
        try:
            # 尝试解析JSON
            if '{' in content and '}' in content:
                start = content.find('{')
                end = content.rfind('}') + 1
                json_str = content[start:end]
                result = json.loads(json_str)
                
                # 验证必要字段
                if 'score' not in result:
                    result['score'] = 50.0
                if 'quality_level' not in result:
                    result['quality_level'] = 'fair'
                if 'analysis' not in result:
                    result['analysis'] = content
                
                return result
        except Exception as e:
            print(f"      警告 JSON解析失败，使用文本分析: {e}")
        
        # 如果JSON解析失败，使用文本分析
        return self._parse_text_analysis(content, dimension_name)

    def _parse_text_analysis(self, content: str, dimension_name: str) -> Dict:
        """解析文本分析结果"""
        # 简单的文本解析逻辑
        score = 50.0  # 默认分数
        quality_level = 'fair'
        
        # 尝试从文本中提取分数
        import re
        score_match = re.search(r'(\d+(?:\.\d+)?)\s*分', content)
        if score_match:
            score = float(score_match.group(1))
        
        # 根据分数确定质量等级
        if score >= 85:
            quality_level = 'excellent'
        elif score >= 70:
            quality_level = 'good'
        elif score >= 50:
            quality_level = 'fair'
        else:
            quality_level = 'poor'
        
        return {
            'score': score,
            'quality_level': quality_level,
            'analysis': content,
            'strengths': [],
            'issues': [],
            'suggestions': [],
            'improvement_path': {}
        }

    def _generate_suggestions(self, dimension_name: str, score: float, details: Dict, quality_level: str) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if dimension_name == "代码结构与可维护性":
            if score < 70:
                suggestions.extend([
                    "增加代码质量检查工具配置",
                    "优化项目目录结构",
                    "添加代码规范文档"
                ])
            elif score < 85:
                suggestions.extend([
                    "提高代码覆盖率",
                    "优化代码复杂度",
                    "加强代码审查流程"
                ])

        elif dimension_name == "测试覆盖与质量保障":
            if score < 70:
                suggestions.extend([
                    "增加单元测试覆盖率",
                    "添加集成测试",
                    "建立测试自动化流程"
                ])
            elif score < 85:
                suggestions.extend([
                    "提高测试覆盖率到90%以上",
                    "添加性能测试",
                    "建立测试报告机制"
                ])

        elif dimension_name == "构建与工程可重复性":
            if score < 70:
                suggestions.extend([
                    "添加Docker容器化支持",
                    "建立自动化构建脚本",
                    "完善依赖管理"
                ])
            elif score < 85:
                suggestions.extend([
                    "优化构建流程",
                    "添加多环境支持",
                    "建立构建缓存机制"
                ])

        # 通用建议
        if score < 50:
            suggestions.append("该维度需要重点关注和改进")
        elif score < 70:
            suggestions.append("该维度有改进空间，建议逐步优化")
        else:
            suggestions.append("该维度表现良好，建议保持并进一步提升")

        return suggestions[:5]  # 限制建议数量

    def _generate_improvement_path(self, dimension_name: str, score: float, quality_level: str) -> Dict:
        """生成改进路径"""
        if score < 50:
            return {
                'current_state': f"{dimension_name}基础薄弱，需要系统性改进",
                'target_state': f"建立完善的{dimension_name}体系",
                'steps': [
                    "制定改进计划",
                    "实施基础改进",
                    "建立监控机制"
                ]
            }
        elif score < 70:
            return {
                'current_state': f"{dimension_name}基本达标，有改进空间",
                'target_state': f"优化{dimension_name}达到优秀水平",
                'steps': [
                    "识别改进点",
                    "实施优化措施",
                    "持续监控改进"
                ]
            }
        else:
            return {
                'current_state': f"{dimension_name}表现优秀",
                'target_state': f"保持{dimension_name}的领先地位",
                'steps': [
                    "持续监控",
                    "定期评估",
                    "探索创新"
                ]
            }

    def _analyze_score(self, score: float, dimension_name: str) -> str:
        """分析评分"""
        if score >= 90:
            return f"{dimension_name}表现卓越，符合企业级标准"
        elif score >= 80:
            return f"{dimension_name}表现良好，基本满足生产环境要求"
        elif score >= 70:
            return f"{dimension_name}表现一般，需要进一步改进"
        elif score >= 50:
            return f"{dimension_name}表现较差，需要重点关注"
        else:
            return f"{dimension_name}表现极差，需要系统性改进"

    def _calculate_confidence(self, score: float, details: Dict) -> float:
        """计算AI置信度"""
        # 基于数据完整性和评分合理性计算置信度
        data_completeness = len(details) / 10.0  # 假设完整数据有10个字段
        score_consistency = 1.0 if 0 <= score <= 100 else 0.5

        confidence = (data_completeness + score_consistency) / 2.0
        return min(max(confidence, 0.5), 1.0)  # 限制在0.5-1.0之间

    def analyze_project_maturity_with_openai(self, all_results: List[Dict]) -> Dict:
        """使用OpenAI/DeepSeek AI分析项目整体成熟度"""
        prompt = self._create_project_prompt(all_results)

        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            stream=self.openai_config.get('stream', False)
        )

        # 获取响应内容
        if self.openai_config.get('stream', False):
            content = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content += chunk.choices[0].delta.content
        else:
            content = response.choices[0].message.content

        # 解析OpenAI响应
        analysis = self._parse_project_openai_response(content)
        return analysis

    def _parse_project_openai_response(self, response_text: str) -> Dict:
        """解析OpenAI/DeepSeek项目分析响应"""
        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    'maturity_level': analysis.get('maturity_level', 'experimental'),
                    'ai_confidence': analysis.get('ai_confidence', 0.8),
                    'overall_suggestions': analysis.get('overall_suggestions', []),
                    'improvement_roadmap': analysis.get('improvement_roadmap', {})
                }
        except Exception as e:
            print(f"警告 解析OpenAI/DeepSeek项目响应失败: {e}")

        # 回退到规则分析
        return self.analyze_project_maturity_with_rules([])

    def analyze_project_maturity_with_gemini(self, all_results: List[Dict]) -> Dict:
        """使用Gemini AI分析项目整体成熟度"""
        prompt = self._create_project_prompt(all_results)
        response = self.gemini_model.generate_content(prompt)

        # 解析Gemini响应
        analysis = self._parse_project_gemini_response(response.text)
        return analysis

    def _create_project_prompt(self, all_results: List[Dict]) -> str:
        """创建项目分析提示"""
        prompt = f"""
请分析这个开源项目的整体成熟度。

项目评估结果：
{json.dumps(all_results, ensure_ascii=False, indent=2)}

请提供以下分析（用JSON格式返回）：
{{
    "maturity_level": "enterprise_ready/production_ready/development_ready/experimental",
    "ai_confidence": 0.85,
    "overall_suggestions": ["建议1", "建议2", "建议3"],
    "improvement_roadmap": {{
        "current_level": "experimental",
        "next_level": "development_ready",
        "phases": [
            {{
                "priority": "高优先级",
                "focus": "重点改进内容",
                "scope": "改进范围"
            }}
        ]
    }}
}}

请确保返回的是有效的JSON格式。
"""
        return prompt

    def _parse_project_gemini_response(self, response_text: str) -> Dict:
        """解析Gemini项目分析响应"""
        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    'maturity_level': analysis.get('maturity_level', 'experimental'),
                    'ai_confidence': analysis.get('ai_confidence', 0.8),
                    'overall_suggestions': analysis.get('overall_suggestions', []),
                    'improvement_roadmap': analysis.get('improvement_roadmap', {})
                }
        except Exception as e:
            print(f"警告 解析Gemini项目响应失败: {e}")

        # 回退到规则分析
        return self.analyze_project_maturity_with_rules([])

    def analyze_project_maturity_with_rules(self, all_results: List[Dict]) -> Dict:
        """使用规则分析项目整体成熟度"""
        if not all_results:
            return {
                'maturity_level': 'experimental',
                'ai_confidence': 0.5,
                'overall_suggestions': ['数据不足，无法进行完整分析'],
                'improvement_roadmap': {
                    'current_level': 'experimental',
                    'next_level': 'development_ready',
                    'phases': []
                }
            }

        # 计算平均分数
        scores = [result.get('score', 0) for result in all_results]
        avg_score = sum(scores) / len(scores)

        # 确定成熟度级别
        maturity_level = 'experimental'
        if avg_score >= 80:
            maturity_level = 'enterprise_ready'
        elif avg_score >= 70:
            maturity_level = 'production_ready'
        elif avg_score >= 50:
            maturity_level = 'development_ready'

        # 生成整体建议
        overall_suggestions = self._generate_overall_suggestions(all_results, avg_score)

        # 生成改进路线图
        improvement_roadmap = self._generate_overall_roadmap(maturity_level, avg_score)

        return {
            'maturity_level': maturity_level,
            'ai_confidence': self._calculate_overall_confidence(all_results),
            'overall_suggestions': overall_suggestions,
            'improvement_roadmap': improvement_roadmap
        }

    def analyze_project_maturity(self, all_results: List[Dict]) -> Dict:
        """分析项目整体成熟度（按优先级尝试AI方法）"""
        # 按优先级尝试AI方法
        for method in self.ai_priority:
            if method == 'openai' and self.use_openai:
                try:
                    print(f"      AI 使用OpenAI/DeepSeek进行项目整体分析...")
                    return self.analyze_project_maturity_with_openai(all_results)
                except Exception as e:
                    print(f"      警告 OpenAI/DeepSeek项目分析失败，尝试下一个AI方法: {e}")
                    continue
            elif method == 'gemini' and self.use_gemini:
                try:
                    print(f"      AI 使用Gemini进行项目整体分析...")
                    return self.analyze_project_maturity_with_gemini(all_results)
                except Exception as e:
                    print(f"      警告 Gemini项目分析失败，尝试下一个AI方法: {e}")
                    continue
            elif method == 'rules':
                print(f"      AI 使用规则进行项目整体分析...")
                return self.analyze_project_maturity_with_rules(all_results)

        # 如果所有方法都失败，回退到规则分析
        print(f"      AI 回退到规则进行项目整体分析...")
        return self.analyze_project_maturity_with_rules(all_results)

    def _generate_overall_suggestions(self, all_results: List[Dict], avg_score: float) -> List[str]:
        """生成整体改进建议"""
        suggestions = []

        # 找出薄弱维度
        weak_dimensions = [r for r in all_results if r.get('score', 0) < 60]
        if weak_dimensions:
            weak_names = [r.get('dimension_name', '') for r in weak_dimensions[:3]]
            suggestions.append(f"重点关注薄弱维度：{', '.join(weak_names)}")

        # 找出优势维度
        strong_dimensions = [r for r in all_results if r.get('score', 0) >= 80]
        if strong_dimensions:
            strong_names = [r.get('dimension_name', '') for r in strong_dimensions[:5]]
            suggestions.append(f"优势维度：{', '.join(strong_names)}，可作为项目亮点")

        # 基于平均分数给出建议
        if avg_score < 60:
            suggestions.append("项目整体成熟度较低，需要系统性改进")
        elif avg_score < 75:
            suggestions.append("项目成熟度良好，建议持续改进以达企业级标准")
        else:
            suggestions.append("项目成熟度优秀，建议保持并探索创新")

        return suggestions

    def _generate_overall_roadmap(self, current_level: str, avg_score: float) -> Dict:
        """生成整体改进路线图"""
        level_progression = {
            'experimental': 'development_ready',
            'development_ready': 'production_ready',
            'production_ready': 'enterprise_ready',
            'enterprise_ready': 'enterprise_ready'
        }

        next_level = level_progression.get(current_level, 'development_ready')

        phases = []
        if current_level == 'experimental':
            phases = [
                {'priority': '高优先级', 'focus': '基础代码质量和文档', 'scope': '核心功能完善'},
                {'priority': '中优先级', 'focus': '测试覆盖和构建系统', 'scope': '质量保障'},
                {'priority': '标准优先级', 'focus': 'CI/CD和安全合规', 'scope': '自动化流程'}
            ]
        elif current_level == 'development_ready':
            phases = [
                {'priority': '高优先级', 'focus': '提高测试覆盖率', 'scope': '测试质量'},
                {'priority': '中优先级', 'focus': '完善CI/CD流程', 'scope': '开发效率'},
                {'priority': '标准优先级', 'focus': '安全扫描和合规检查', 'scope': '安全保障'}
            ]
        elif current_level == 'production_ready':
            phases = [
                {'priority': '高优先级', 'focus': '性能优化和监控', 'scope': '运营支持'},
                {'priority': '中优先级', 'focus': '企业级安全标准', 'scope': '安全合规'},
                {'priority': '标准优先级', 'focus': '社区治理和文档完善', 'scope': '长期维护'}
            ]

        return {
            'current_level': current_level,
            'next_level': next_level,
            'phases': phases
        }

    def _calculate_overall_confidence(self, all_results: List[Dict]) -> float:
        """计算整体分析置信度"""
        if not all_results:
            return 0.5

        # 基于数据完整性和评分一致性计算置信度
        data_completeness = len(all_results) / 14.0  # 假设有14个维度
        score_variance = 1.0 - (max(r.get('score', 0) for r in all_results) - min(r.get('score', 0) for r in all_results)) / 100.0

        confidence = (data_completeness + score_variance) / 2.0
        return min(max(confidence, 0.5), 1.0)
    
    def analyze_dimension(self, dimension_data: Dict[str, Any]) -> str:
        """分析维度数据并生成智能评估"""
        try:
            dimension_name = dimension_data.get('dimension_name', '未知维度')
            project_info = dimension_data.get('project_info', {})
            issues_summary = dimension_data.get('issues_summary', {})
            
            prompt = f"""
作为专业的代码质量分析师，请分析项目"{project_info.get('name', '未知项目')}"的{dimension_name}维度：

项目特征：
- 编程语言: {', '.join(project_info.get('languages', {}).keys())}
- 项目类型: {project_info.get('project_type', '未知')}
- 项目规模: {project_info.get('size', '未知')}

问题统计：
- 总问题数: {issues_summary.get('total', 0)}
- 关键问题: {issues_summary.get('by_severity', {}).get('critical', 0)}个
- 高优先级: {issues_summary.get('by_severity', {}).get('high', 0)}个
- 中等优先级: {issues_summary.get('by_severity', {}).get('medium', 0)}个

请提供专业的{dimension_name}评估分析（200字以内）：
1. 当前状态评估
2. 主要风险点识别  
3. 核心改进方向

请用专业、简洁的中文回答。
"""
            
            response = self._call_ai_api(prompt)
            return response.strip()
            
        except Exception as e:
            print(f"AI维度分析失败: {e}")
            return f"基于检测结果，{dimension_data.get('dimension_name', '该维度')}存在{dimension_data.get('issues_summary', {}).get('total', 0)}个问题，建议重点关注高优先级问题的解决。"
    
    def generate_recommendations(self, dimension_data: Dict[str, Any]) -> List[str]:
        """生成维度改进建议"""
        try:
            dimension_name = dimension_data.get('dimension_name', '未知维度')
            issues_summary = dimension_data.get('issues_summary', {})
            
            prompt = f"""
针对{dimension_name}维度的分析结果，请提供3-5条具体的改进建议：

问题分布：
- 关键问题: {issues_summary.get('by_severity', {}).get('critical', 0)}个
- 高优先级: {issues_summary.get('by_severity', {}).get('high', 0)}个
- 中等优先级: {issues_summary.get('by_severity', {}).get('medium', 0)}个

请提供具体可执行的改进建议，每条建议一行，格式如：
- 建议内容

请确保建议具体、可操作，避免泛泛而谈。
"""
            
            response = self._call_ai_api(prompt)
            
            # 解析建议列表
            recommendations = []
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    recommendations.append(line[1:].strip())
                elif line and not line.endswith('：') and not line.endswith(':'):
                    recommendations.append(line)
            
            return recommendations[:5]  # 最多返回5条建议
            
        except Exception as e:
            print(f"AI建议生成失败: {e}")
            return [
                "优先解决关键和高优先级问题",
                "建立定期代码审查机制", 
                "完善自动化检测工具配置",
                "制定相应的最佳实践规范",
                "持续监控和改进相关指标"
            ]
    
    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API进行分析"""
        try:
            # 按优先级尝试不同的AI方法
            for method in self.ai_priority:
                if method == 'openai' and self.use_openai:
                    try:
                        response = self.openai_client.chat.completions.create(
                            model=self.openai_model,
                            messages=[
                                {"role": "system", "content": "你是一个专业的开源项目成熟度分析专家。"},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=1000,
                            temperature=0.1,
                            timeout=self.model_timeout
                        )
                        return response.choices[0].message.content
                    except Exception as e:
                        print(f"OpenAI/DeepSeek API调用失败: {e}")
                        continue
                        
                elif method == 'gemini' and self.use_gemini:
                    try:
                        response = self.gemini_model.generate_content(prompt)
                        return response.text
                    except Exception as e:
                        print(f"Gemini API调用失败: {e}")
                        continue
                        
                elif method == 'rules':
                    # 规则分析作为最后的回退
                    return self._rule_based_analysis(prompt)
            
            # 如果所有AI方法都失败，返回规则分析结果
            return self._rule_based_analysis(prompt)
            
        except Exception as e:
            print(f"AI API调用失败: {e}")
            return self._rule_based_analysis(prompt)
    
    def _rule_based_analysis(self, prompt: str) -> str:
        """基于规则的分析回退方案"""
        if "维度" in prompt and "分析" in prompt:
            return "基于规则分析，该维度需要关注代码质量和最佳实践的落实。建议定期评估和改进。"
        elif "建议" in prompt:
            return "建议参考行业最佳实践，建立持续改进机制。"
        else:
            return "建议参考相关文档和最佳实践进行改进。"
    
    def analyze_overall_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析项目整体情况 - 增强版本提供更详细的分析"""
        try:
            project_info = project_data.get('project_info', {})
            project_name = project_info.get('name', '未知项目')
            overall_score = project_data.get('overall_score', 0)
            overall_status = project_data.get('overall_status', 'UNKNOWN')
            dimensions_summary = project_data.get('dimensions_summary', [])
            summary = project_data.get('summary', {})
            
            # 分析维度得分分布
            passed_dims = [d for d in dimensions_summary if d.get('status') == 'PASS']
            warned_dims = [d for d in dimensions_summary if d.get('status') == 'WARN']
            failed_dims = [d for d in dimensions_summary if d.get('status') == 'FAIL']
            
            # 找出最高分和最低分的维度
            highest_dim = max(dimensions_summary, key=lambda d: d.get('score', 0)) if dimensions_summary else None
            lowest_dim = min(dimensions_summary, key=lambda d: d.get('score', 0)) if dimensions_summary else None
            
            # 构建更详细的分析上下文
            failed_dimensions = [d for d in dimensions_summary if d.get('status') == 'FAIL']
            critical_dimensions = sorted(dimensions_summary, key=lambda d: d.get('score', 0))[:3]
            excellent_dimensions = [d for d in dimensions_summary if d.get('score', 0) >= 90]
            
            # 构建详细分析提示
            prompt = f"""
请对开源项目"{project_name}"进行深度综合评估分析：

项目基本信息：
- 项目名称: {project_name}
- 项目类型: {project_info.get('project_type', '未知')}
- 项目结构: {project_info.get('structure_type', '未知')}
- 主要语言: {', '.join(project_info.get('languages', {}).keys()) if project_info.get('languages') else '未知'}
- 语言分布: {project_info.get('languages', {})}
- 项目规模: {project_info.get('size', '未知')} ({summary.get('code_lines', 0):,} 行代码)
- 测试文件: {project_info.get('test_files', 0)} 个
- 构建工具: {project_info.get('build_tools', [])}
- 整体得分: {overall_score:.1f}/100 ({overall_status})

维度分析深入洞察：
- 总计 {len(dimensions_summary)} 个维度评估
- 通过维度: {len(passed_dims)} 个 | 警告维度: {len(warned_dims)} 个 | 失败维度: {len(failed_dims)} 个
- 最高得分维度: {highest_dim['name']}({highest_dim['score']:.1f}分) - 项目强项
- 最低得分维度: {lowest_dim['name']}({lowest_dim['score']:.1f}分) - 关键短板
- 表现优异维度({len(excellent_dimensions)}个): {', '.join([d['name'] + f"({d['score']:.0f}分)" for d in excellent_dimensions])}
- 需重点关注维度: {', '.join([d['name'] + f"({d['score']:.0f}分)" for d in critical_dimensions])}

项目分析详情：
- 检测语言: {', '.join(project_info.get('languages', {}).keys())}
- 项目规模: {project_info.get('size', '未知')} ({project_info.get('code_lines', 0)} 行代码)
- 项目类型: {project_info.get('project_type', '未知')}

项目特征分析：
- 代码-测试比: {summary.get('code_lines', 0)}:{project_info.get('test_files', 0)*50} (假设每个测试文件50行)
- 依赖情况: {len(project_info.get('dependencies', {}))} 种语言的依赖管理
- 置信度: {project_info.get('confidence', 0):.1f} - 项目识别的准确性

作为资深开源软件质量评估专家，请基于上述数据进行深度分析：

1. 项目整体成熟度评价（200字）：
   结合得分分布、工具执行情况、项目结构特征，深入评价项目的技术成熟度、工程化水平和开发规范程度。重点分析为何整体得分为{overall_score:.1f}分。

2. 核心优势与竞争力分析（150字）：
   基于高分维度和项目特征，深入分析项目的技术优势、架构特色和开发亮点，突出其在同类项目中的差异化竞争力。

3. 关键改进路径与优先级（200字）：
   基于失败和低分维度，制定具体的3-5阶段改进计划，包含技术手段、预期效果和实施优先级，确保建议具备可操作性和针对性。

4. 风险识别与防控建议（120字）：
   从技术债务、安全漏洞、合规性、可维护性等角度识别潜在风险，提供预防性措施和监控策略。

请用专业、数据驱动的语言进行深度分析，避免泛泛而谈。
"""
            
            response = self._call_ai_api(prompt)
            
            # 解析AI响应，尝试提取结构化信息
            lines = response.strip().split('\n')
            analysis_parts = {
                'overall_assessment': '',
                'strengths': '',
                'recommendations': '',
                'risks': ''
            }
            
            current_section = 'overall_assessment'
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 根据关键词判断所属部分
                if '项目整体成熟度' in line or '成熟度评价' in line or '1.' in line:
                    current_section = 'overall_assessment'
                elif '主要优势' in line or '优势分析' in line or '优点' in line or '2.' in line:
                    current_section = 'strengths'
                elif '关键改进' in line or '改进建议' in line or '建议' in line or '3.' in line:
                    current_section = 'recommendations'  
                elif '潜在风险' in line or '风险提示' in line or '风险' in line or '4.' in line:
                    current_section = 'risks'
                else:
                    # 添加所有非空行到当前部分
                    analysis_parts[current_section] += line + ' '
            
            # 如果解析失败，使用完整响应
            if not any(analysis_parts.values()):
                analysis_parts['overall_assessment'] = response
            
            return analysis_parts
            
        except Exception as e:
            print(f"项目整体AI分析失败: {e}")
            return {
                'overall_assessment': f"基于{overall_score:.1f}分的评估结果，项目整体表现{'良好' if overall_score >= 70 else '需要改进'}。",
                'strengths': "项目具备基础的开源项目结构。",
                'recommendations': "建议重点关注评分较低的维度，制定针对性改进计划。",
                'risks': "需要持续关注代码质量和安全合规性。"
            }
