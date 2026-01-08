#!/usr/bin/env python3
"""
Base classes for language-specific analysis plugins
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import pathlib

from ..core.tool_registry import Tool
from ..core.tool_executor import ToolResult
from ..core.project_detector import ProjectInfo

logger = logging.getLogger(__name__)


class PluginPriority(Enum):
    """Plugin priority levels"""
    CRITICAL = 1    # Core language features, must run
    HIGH = 2        # Important quality checks
    MEDIUM = 3      # Standard analysis tools
    LOW = 4         # Optional/supplementary tools


class PluginCategory(Enum):
    """Plugin analysis categories"""
    SYNTAX = "syntax"           # Syntax checking
    QUALITY = "quality"         # Code quality analysis  
    SECURITY = "security"       # Security vulnerability detection
    TESTING = "testing"         # Test-related analysis
    FORMATTING = "formatting"   # Code formatting and style
    DEPENDENCIES = "dependencies"  # Dependency analysis
    PERFORMANCE = "performance"    # Performance analysis
    DOCUMENTATION = "documentation"  # Documentation analysis


@dataclass
class PluginError(Exception):
    """Plugin-specific error with isolation context"""
    plugin_name: str
    error_type: str
    message: str
    recoverable: bool = True
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self):
        return f"[{self.plugin_name}] {self.error_type}: {self.message}"


@dataclass
class PluginResult:
    """Result from plugin analysis"""
    plugin_name: str
    language: str
    success: bool
    execution_time: float = 0.0
    
    # Analysis results
    tool_results: Dict[str, ToolResult] = field(default_factory=dict)
    quality_score: float = 0.0
    issues_found: int = 0
    
    # Metadata
    tools_executed: List[str] = field(default_factory=list)
    tools_skipped: List[str] = field(default_factory=list)
    errors: List[PluginError] = field(default_factory=list)
    
    # Plugin-specific data
    plugin_data: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: PluginError):
        """Add error to result"""
        self.errors.append(error)
        if not error.recoverable:
            self.success = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            'plugin_name': self.plugin_name,
            'language': self.language,
            'success': self.success,
            'execution_time': self.execution_time,
            'quality_score': self.quality_score,
            'issues_found': self.issues_found,
            'tools_executed': self.tools_executed,
            'tools_skipped': self.tools_skipped,
            'tool_results': {name: result.to_dict() for name, result in self.tool_results.items()},
            'errors': [str(error) for error in self.errors],
            'plugin_data': self.plugin_data
        }


@dataclass 
class PluginCapability:
    """Describes what a plugin can analyze"""
    languages: Set[str]                    # Supported languages
    file_extensions: Set[str]              # File extensions it can handle
    categories: Set[PluginCategory]        # Analysis categories
    required_tools: List[str]              # Tools that must be available
    optional_tools: List[str]              # Tools that enhance analysis
    min_confidence_threshold: float = 0.1  # Minimum language confidence to run
    
    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """Check if plugin can analyze this project"""
        # Check if any supported language is in project
        project_languages = set(project_info.languages.keys())
        if not self.languages.intersection(project_languages):
            return False
            
        # Check confidence threshold
        max_confidence = max(
            (project_info.languages.get(lang, 0) for lang in self.languages),
            default=0
        )
        
        return max_confidence >= self.min_confidence_threshold


class LanguagePlugin(ABC):
    """
    Base class for language-specific analysis plugins
    
    Each plugin handles analysis for one or more programming languages,
    providing tool selection, execution, and result interpretation.
    """
    
    def __init__(self, name: str):
        """
        Initialize plugin
        
        Args:
            name: Plugin identifier name
        """
        self.name = name
        self.logger = logging.getLogger(f"plugin.{name}")
        self._initialized = False
    
    @property
    @abstractmethod
    def capability(self) -> PluginCapability:
        """Return plugin capabilities"""
        pass
    
    @property  
    @abstractmethod
    def priority(self) -> PluginPriority:
        """Return plugin priority level"""
        pass
    
    def initialize(self) -> bool:
        """
        Initialize plugin (called once during registration)
        
        Returns:
            True if initialization successful
        """
        try:
            self._do_initialization()
            self._initialized = True
            self.logger.info(f"Plugin {self.name} initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Plugin {self.name} initialization failed: {e}")
            return False
    
    def _do_initialization(self):
        """Override this method for plugin-specific initialization"""
        pass
    
    def can_analyze(self, project_info: ProjectInfo) -> bool:
        """
        Check if this plugin can analyze the given project
        
        Args:
            project_info: Project information
            
        Returns:
            True if plugin can analyze this project
        """
        return self.capability.can_analyze(project_info)
    
    def analyze(self, project_path: str, project_info: ProjectInfo, 
               available_tools: List[Tool]) -> PluginResult:
        """
        Perform language-specific analysis
        
        Args:
            project_path: Path to project directory
            project_info: Project information from detection
            available_tools: Available analysis tools
            
        Returns:
            Analysis results
        """
        if not self._initialized:
            raise PluginError(
                plugin_name=self.name,
                error_type="NotInitialized",
                message="Plugin not initialized",
                recoverable=False
            )
        
        result = PluginResult(
            plugin_name=self.name,
            language=self._get_primary_language(project_info),
            success=True
        )
        
        try:
            import time
            start_time = time.time()
            
            # Select tools for this analysis
            selected_tools = self.select_tools(project_info, available_tools)
            
            # Execute analysis
            self._execute_analysis(project_path, project_info, selected_tools, result)
            
            # Calculate execution time
            result.execution_time = time.time() - start_time
            
            # Post-process results
            self._post_process_results(result, project_info)
            
            # Validate and standardize results
            result = self._validate_and_standardize_result(result)
            
        except PluginError as e:
            result.add_error(e)
            self.logger.warning(f"Plugin error in {self.name}: {e}")
        except Exception as e:
            error = PluginError(
                plugin_name=self.name,
                error_type="UnexpectedError",
                message=str(e),
                recoverable=False
            )
            result.add_error(error)
            self.logger.error(f"Unexpected error in {self.name}: {e}")
        
        return result
    
    def select_tools(self, project_info: ProjectInfo, available_tools: List[Tool]) -> List[Tool]:
        """
        Select tools for analysis based on project characteristics
        
        Args:
            project_info: Project information
            available_tools: Available tools
            
        Returns:
            Selected tools for this plugin
        """
        # Filter tools that match plugin languages
        plugin_languages = self.capability.languages
        compatible_tools = []
        
        for tool in available_tools:
            # Tool matches plugin language
            if tool.language in plugin_languages:
                compatible_tools.append(tool)
            # Universal tool that supports plugin languages  
            elif (tool.language == 'universal' and 
                  (not tool.supports or 
                   any(lang in tool.supports for lang in plugin_languages) or
                   'all' in tool.supports)):
                compatible_tools.append(tool)
        
        # Use smart tool selector for optimal selection
        try:
            from ..core.smart_tool_selector import create_smart_tool_selector
            smart_selector = create_smart_tool_selector()
            selected = smart_selector.select_optimal_tools(
                compatible_tools, 
                project_info, 
                max_tools_per_dimension=1
            )
            self.logger.debug(f"Smart selection: {len(selected)} tools from {len(compatible_tools)} compatible tools for {self.name}")
        except Exception as e:
            # Fallback to basic selection on any error
            selected = compatible_tools
            selected.sort(key=lambda t: (t.priority, t.estimated_time))
            self.logger.debug(f"Basic selection (fallback): {len(selected)} tools for {self.name}")
        
        return selected
    
    @abstractmethod
    def _execute_analysis(self, project_path: str, project_info: ProjectInfo, 
                         tools: List[Tool], result: PluginResult):
        """
        Execute the actual analysis (implemented by each plugin)
        
        Args:
            project_path: Project directory path
            project_info: Project information 
            tools: Selected tools to run
            result: Result object to populate
        """
        pass
    
    def _post_process_results(self, result: PluginResult, project_info: ProjectInfo):
        """
        Post-process analysis results (can be overridden)
        
        Args:
            result: Analysis results
            project_info: Project information
        """
        # Calculate overall quality score
        if result.tool_results:
            scores = []
            for tool_result in result.tool_results.values():
                if tool_result.success and tool_result.result:
                    tool_score = tool_result.result.get('score', 60)
                    scores.append(tool_score)
            
            result.quality_score = sum(scores) / len(scores) if scores else 50.0
        elif result.quality_score == 0.0:  # Only set default if not already set
            result.quality_score = 50.0  # Neutral score if no tools ran
        
        # Count total issues
        result.issues_found = sum(
            tool_result.result.get('issues_count', 0)
            for tool_result in result.tool_results.values()
            if tool_result.success and tool_result.result
        )
    
    def _get_primary_language(self, project_info: ProjectInfo) -> str:
        """Get the primary language this plugin handles for this project"""
        plugin_languages = self.capability.languages
        
        # Find the highest confidence language that this plugin supports
        best_lang = None
        best_confidence = 0
        
        for lang, confidence in project_info.languages.items():
            if lang in plugin_languages and confidence > best_confidence:
                best_lang = lang
                best_confidence = confidence
        
        return best_lang or list(plugin_languages)[0]
    
    def _validate_and_standardize_result(self, result: PluginResult) -> PluginResult:
        """Validate and standardize plugin result"""
        try:
            from .result_validator import validate_and_standardize_result
            
            standardized_result, validation_errors = validate_and_standardize_result(result)
            
            # Log validation errors
            for error in validation_errors:
                if error.severity == "error":
                    self.logger.error(f"Result validation error in {error.field}: {error.message}")
                else:
                    self.logger.debug(f"Result validation warning in {error.field}: {error.message}")
            
            return standardized_result
            
        except ImportError:
            self.logger.debug("Result validator not available, skipping validation")
            return result
        except Exception as e:
            self.logger.warning(f"Result validation failed: {e}")
            return result
    
    def cleanup(self):
        """Cleanup plugin resources (override if needed)"""
        pass
    
    def __str__(self):
        return f"{self.__class__.__name__}({self.name})"
    
    def __repr__(self):
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"languages={self.capability.languages}, "
                f"priority={self.priority.name})")