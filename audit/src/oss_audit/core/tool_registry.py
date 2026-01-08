#!/usr/bin/env python3
"""
Tool Registry - 工具注册表核心类
负责加载和管理工具配置，替代硬编码的工具配置
"""

import os
import yaml
import pathlib
import subprocess
import sys
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具分类枚举"""
    QUALITY = "quality"
    SECURITY = "security"  
    TEST = "testing"
    FORMAT = "format"
    DEPENDENCIES = "dependencies"
    COVERAGE = "coverage"
    STYLE = "style"
    TYPING = "typing"


@dataclass
class Tool:
    """工具配置数据类"""
    name: str
    command: List[str]
    args: List[str]
    language: str
    install: List[str]
    priority: int = 1
    estimated_time: int = 60
    categories: List[str] = None
    timeout: int = 120
    output_format: str = "text"
    severity_levels: Dict[str, int] = None
    score_weights: Dict[str, float] = None
    requires_dependencies: bool = False
    requires_config: bool = False
    supports: List[str] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.severity_levels is None:
            self.severity_levels = {}
        if self.score_weights is None:
            self.score_weights = {}
        if self.supports is None:
            self.supports = []
    
    def get_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            'name': self.name,
            'language': self.language,
            'categories': self.categories,
            'estimated_time': self.estimated_time,
            'priority': self.priority,
            'output_format': self.output_format
        }


class ToolRegistry:
    """工具注册表管理器"""
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        初始化工具注册表
        
        Args:
            registry_path: 工具注册表配置文件路径
        """
        self.registry_path = registry_path or self._get_default_registry_path()
        self.tools: Dict[str, Dict[str, List[Tool]]] = {}
        self.universal_tools: Dict[str, List[Tool]] = {}
        self.installation_scripts: Dict[str, List[str]] = {}
        self._load_registry()
    
    def _get_default_registry_path(self) -> str:
        """获取默认的工具注册表路径"""
        current_dir = pathlib.Path(__file__).parent
        config_dir = current_dir.parent / 'config'
        return str(config_dir / 'tools_registry.yaml')
    
    def _load_registry(self):
        """加载工具注册表配置"""
        try:
            if not os.path.exists(self.registry_path):
                logger.error(f"工具注册表文件不存在: {self.registry_path}")
                return
            
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self._parse_language_tools(config.get('languages', {}))
            self._parse_universal_tools(config.get('universal_tools', {}))
            self.installation_scripts = config.get('installation_scripts', {})
            
            logger.info(f"成功加载工具注册表: {len(self.tools)} 种语言, {len(self.universal_tools)} 类通用工具")
            
        except Exception as e:
            logger.error(f"加载工具注册表失败: {e}")
            self.tools = {}
            self.universal_tools = {}
    
    def _parse_language_tools(self, languages_config: Dict[str, Any]):
        """解析语言特定工具配置"""
        for language, lang_config in languages_config.items():
            self.tools[language] = {}
            
            for category, tools_list in lang_config.items():
                if not isinstance(tools_list, list):
                    continue
                    
                self.tools[language][category] = []
                
                for tool_config in tools_list:
                    try:
                        tool = Tool(
                            name=tool_config['name'],
                            command=tool_config['command'],
                            args=tool_config.get('args', []),
                            language=language,
                            install=tool_config.get('install', []),
                            priority=tool_config.get('priority', 1),
                            estimated_time=tool_config.get('estimated_time', 60),
                            categories=tool_config.get('categories', []),
                            timeout=tool_config.get('timeout', 120),
                            output_format=tool_config.get('output_format', 'text'),
                            severity_levels=tool_config.get('severity_levels', {}),
                            score_weights=tool_config.get('score_weights', {}),
                            requires_dependencies=tool_config.get('requires_dependencies', False),
                            requires_config=tool_config.get('requires_config', False)
                        )
                        self.tools[language][category].append(tool)
                    except Exception as e:
                        logger.warning(f"解析工具配置失败 {language}.{tool_config.get('name', 'unknown')}: {e}")
    
    def _parse_universal_tools(self, universal_config: Dict[str, Any]):
        """解析通用工具配置"""
        for category, tools_list in universal_config.items():
            self.universal_tools[category] = []
            
            for tool_config in tools_list:
                try:
                    tool = Tool(
                        name=tool_config['name'],
                        command=tool_config['command'],
                        args=tool_config.get('args', []),
                        language='universal',
                        install=tool_config.get('install', []),
                        priority=tool_config.get('priority', 1),
                        estimated_time=tool_config.get('estimated_time', 60),
                        categories=tool_config.get('categories', []),
                        timeout=tool_config.get('timeout', 120),
                        output_format=tool_config.get('output_format', 'text'),
                        severity_levels=tool_config.get('severity_levels', {}),
                        score_weights=tool_config.get('score_weights', {}),
                        supports=tool_config.get('supports', [])
                    )
                    self.universal_tools[category].append(tool)
                except Exception as e:
                    logger.warning(f"解析通用工具配置失败 {tool_config.get('name', 'unknown')}: {e}")
    
    def get_language_tools(self, language: str, category: Optional[str] = None) -> List[Tool]:
        """
        获取指定语言的工具列表
        
        Args:
            language: 编程语言
            category: 工具分类 (可选)
            
        Returns:
            工具列表
        """
        if language not in self.tools:
            return []
        
        if category:
            return self.tools[language].get(category, [])
        else:
            # 返回该语言的所有工具
            all_tools = []
            for tools_list in self.tools[language].values():
                all_tools.extend(tools_list)
            return all_tools
    
    def get_universal_tools(self, category: Optional[str] = None, 
                          language: Optional[str] = None) -> List[Tool]:
        """
        获取通用工具列表
        
        Args:
            category: 工具分类 (可选)
            language: 过滤支持的语言 (可选)
            
        Returns:
            工具列表
        """
        if category:
            tools = self.universal_tools.get(category, [])
        else:
            tools = []
            for tools_list in self.universal_tools.values():
                tools.extend(tools_list)
        
        # 按语言过滤
        if language:
            filtered_tools = []
            for tool in tools:
                if not tool.supports or language in tool.supports or 'all' in tool.supports:
                    filtered_tools.append(tool)
            return filtered_tools
        
        return tools
    
    def get_all_tools_for_languages(self, languages: List[str], 
                                  include_universal: bool = True) -> List[Tool]:
        """
        获取多种语言的所有适用工具
        
        Args:
            languages: 语言列表
            include_universal: 是否包含通用工具
            
        Returns:
            工具列表
        """
        all_tools = []
        
        # 添加语言特定工具
        for language in languages:
            all_tools.extend(self.get_language_tools(language))
        
        # 添加通用工具
        if include_universal:
            for language in languages:
                all_tools.extend(self.get_universal_tools(language=language))
        
        # 去重并按优先级排序
        unique_tools = {}
        for tool in all_tools:
            key = f"{tool.name}_{tool.language}"
            if key not in unique_tools or tool.priority < unique_tools[key].priority:
                unique_tools[key] = tool
        
        return sorted(unique_tools.values(), key=lambda x: (x.priority, x.estimated_time))
    
    def get_tools_by_category(self, category: ToolCategory, 
                            languages: Optional[List[str]] = None) -> List[Tool]:
        """
        按分类获取工具
        
        Args:
            category: 工具分类
            languages: 限制的语言列表 (可选)
            
        Returns:
            工具列表
        """
        tools = []
        category_name = category.value
        
        # 获取语言特定工具
        if languages:
            for language in languages:
                tools.extend(self.get_language_tools(language, category_name))
        else:
            for language_tools in self.tools.values():
                tools.extend(language_tools.get(category_name, []))
        
        # 获取通用工具
        universal_tools = self.get_universal_tools(category_name)
        if languages:
            # 过滤支持的语言
            for tool in universal_tools:
                if not tool.supports or any(lang in tool.supports for lang in languages) or 'all' in tool.supports:
                    tools.append(tool)
        else:
            tools.extend(universal_tools)
        
        return sorted(tools, key=lambda x: (x.priority, x.estimated_time))
    
    def is_tool_available(self, tool: Tool) -> bool:
        """
        检查工具是否可用
        
        Args:
            tool: 工具对象
            
        Returns:
            是否可用
        """
        try:
            # 基本的命令可用性检查
            base_command = tool.command[0] if tool.command else tool.name
            
            # 特殊处理一些工具
            if tool.name in ['python', 'node', 'npm', 'java', 'javac', 'mvn', 'gradle', 'go', 'cargo', 'rustc']:
                # 这些是基础命令，直接检查
                try:
                    result = subprocess.run(
                        [base_command, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    available = result.returncode == 0
                    if available:
                        logger.debug(f"基础工具可用: {tool.name}")
                    return available
                except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                    logger.debug(f"基础工具不可用: {tool.name}")
                    return False
            
            # Python模块工具检查
            if tool.language == 'python' and tool.command and tool.command[0] == 'python':
                if len(tool.command) >= 3 and tool.command[1] == '-m':
                    module_name = tool.command[2]
                    try:
                        # 检查Python模块是否可导入
                        result = subprocess.run(
                            ['python', '-c', f'import {module_name}'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        available = result.returncode == 0
                        if available:
                            logger.debug(f"Python模块可用: {module_name}")
                        else:
                            logger.debug(f"Python模块不可用: {module_name}")
                        return available
                    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                        logger.debug(f"Python模块检查失败: {module_name}")
                        return False
            
            # NPX工具检查
            if base_command == 'npx':
                if len(tool.command) >= 2:
                    npm_package = tool.command[1]
                    try:
                        # 简单检查npx是否可用
                        result = subprocess.run(
                            ['npx', '--version'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            logger.debug(f"npx工具可能可用: {npm_package}")
                            return True  # 假设npx包可以按需安装
                    except:
                        pass
            
            # 通用工具检查（semgrep, gitleaks等）
            if tool.language == 'universal':
                # 对于通用工具，采用宽松的检查策略
                try:
                    result = subprocess.run(
                        [base_command, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        logger.debug(f"通用工具可用: {base_command}")
                        return True
                except:
                    pass
                
                # 检查是否可以通过which/where找到
                try:
                    which_cmd = 'where' if os.name == 'nt' else 'which'
                    result = subprocess.run(
                        [which_cmd, base_command],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    available = result.returncode == 0 and result.stdout.strip()
                    if available:
                        logger.debug(f"通过{which_cmd}找到工具: {base_command}")
                    return available
                except:
                    pass
            
            # 默认检查策略
            try:
                # 尝试运行命令检查可用性
                version_flags = ['--version', '-v', '--help']
                
                for flag in version_flags:
                    try:
                        test_cmd = [base_command, flag]
                        result = subprocess.run(
                            test_cmd,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        # 成功执行认为可用
                        if result.returncode == 0:
                            logger.debug(f"工具可用: {base_command} {flag}")
                            return True
                            
                        # 对于--help，返回码1但有输出也认为可用
                        if flag == '--help' and result.stderr:
                            logger.debug(f"工具可用(通过help): {base_command}")
                            return True
                            
                    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                        continue
                
                logger.debug(f"工具不可用: {base_command}")
                return False
                
            except Exception as e:
                logger.debug(f"工具可用性检查异常: {base_command} - {e}")
                return False
            
        except Exception as e:
            logger.debug(f"工具可用性检查失败 {tool.name}: {e}")
            return False
    
    def get_available_tools(self, languages: List[str]) -> List[Tool]:
        """
        获取可用的工具列表
        
        Args:
            languages: 语言列表
            
        Returns:
            可用工具列表
        """
        all_tools = self.get_all_tools_for_languages(languages)
        available_tools = []
        
        for tool in all_tools:
            if self.is_tool_available(tool):
                available_tools.append(tool)
            else:
                logger.debug(f"工具不可用: {tool.name}")
        
        return available_tools
    
    def get_installation_script(self, script_name: str) -> List[str]:
        """
        获取工具安装脚本
        
        Args:
            script_name: 脚本名称
            
        Returns:
            安装命令列表
        """
        return self.installation_scripts.get(script_name, [])
    
    def install_tool(self, tool: Tool) -> bool:
        """
        安装工具
        
        Args:
            tool: 工具对象
            
        Returns:
            是否安装成功
        """
        if not tool.install:
            logger.info(f"工具 {tool.name} 无需安装")
            return True
        
        try:
            # 如果安装命令是脚本名称，则执行脚本
            if len(tool.install) == 1 and tool.install[0] in self.installation_scripts:
                script_commands = self.get_installation_script(tool.install[0])
                for cmd in script_commands:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.error(f"安装脚本执行失败: {cmd}")
                        return False
                return True
            else:
                # 直接执行安装命令
                result = subprocess.run(
                    tool.install,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                
                if result.returncode == 0:
                    logger.info(f"工具 {tool.name} 安装成功")
                    return True
                else:
                    logger.error(f"工具 {tool.name} 安装失败: {result.stderr}")
                    return False
                    
        except Exception as e:
            logger.error(f"安装工具 {tool.name} 时发生异常: {e}")
            return False
    
    def create_tool_command(self, tool: Tool, project_path: str, 
                          additional_args: Optional[List[str]] = None) -> List[str]:
        """
        创建工具执行命令
        
        Args:
            tool: 工具对象
            project_path: 项目路径
            additional_args: 额外参数
            
        Returns:
            完整的命令列表
        """
        cmd = tool.command.copy()
        cmd.extend(tool.args)
        
        if additional_args:
            cmd.extend(additional_args)
        
        # 某些工具需要指定项目路径
        if tool.name in ['pylint', 'flake8', 'bandit', 'mypy']:
            # 这些工具通常以目录作为参数
            if '.' not in tool.args and project_path not in cmd:
                cmd.append('.')
        
        return cmd
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的编程语言列表"""
        return list(self.tools.keys())
    
    def get_tool_categories(self, language: Optional[str] = None) -> List[str]:
        """
        获取工具分类列表
        
        Args:
            language: 指定语言 (可选)
            
        Returns:
            分类列表
        """
        categories = set()
        
        if language:
            if language in self.tools:
                categories.update(self.tools[language].keys())
        else:
            for lang_tools in self.tools.values():
                categories.update(lang_tools.keys())
        
        # 添加通用工具分类
        categories.update(self.universal_tools.keys())
        
        return sorted(list(categories))
    
    def reload(self):
        """重新加载工具注册表"""
        self.tools.clear()
        self.universal_tools.clear()
        self.installation_scripts.clear()
        self._load_registry()


# 单例模式
_registry_instance: Optional[ToolRegistry] = None

def get_tool_registry(registry_path: Optional[str] = None) -> ToolRegistry:
    """
    获取工具注册表单例实例
    
    Args:
        registry_path: 注册表配置文件路径
        
    Returns:
        ToolRegistry实例
    """
    global _registry_instance
    
    if _registry_instance is None or registry_path:
        _registry_instance = ToolRegistry(registry_path)
    
    return _registry_instance