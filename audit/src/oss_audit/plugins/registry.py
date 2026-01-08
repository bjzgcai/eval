#!/usr/bin/env python3
"""
Plugin Registry - 插件注册表和管理器
负责插件的注册、加载、生命周期管理和错误隔离
"""

import os
import sys
import importlib
import importlib.util
import threading
from typing import Dict, List, Optional, Set, Type, Any
from dataclasses import dataclass
import logging
import traceback
from pathlib import Path

from .base import LanguagePlugin, PluginResult, PluginError, PluginPriority
from ..core.project_detector import ProjectInfo

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Plugin registration information"""
    name: str
    plugin_class: Type[LanguagePlugin]
    instance: Optional[LanguagePlugin] = None
    initialized: bool = False
    load_error: Optional[str] = None
    
    def create_instance(self) -> LanguagePlugin:
        """Create plugin instance"""
        if self.instance is None:
            self.instance = self.plugin_class(self.name)
        return self.instance


class PluginRegistry:
    """
    Plugin registry and manager
    Handles plugin discovery, loading, lifecycle management, and error isolation
    """
    
    def __init__(self):
        self._plugins: Dict[str, PluginInfo] = {}
        self._language_mapping: Dict[str, List[str]] = {}  # language -> plugin names
        self._loaded_modules: Set[str] = set()
        self._lock = threading.RLock()
        
    def register_plugin(self, name: str, plugin_class: Type[LanguagePlugin]) -> bool:
        """
        Register a plugin class
        
        Args:
            name: Plugin name
            plugin_class: Plugin class
            
        Returns:
            True if registration successful
        """
        with self._lock:
            try:
                # Validate plugin class
                if not issubclass(plugin_class, LanguagePlugin):
                    logger.error(f"Plugin {name} does not inherit from LanguagePlugin")
                    return False
                
                # Create plugin info
                plugin_info = PluginInfo(name=name, plugin_class=plugin_class)
                
                # Try to create instance and initialize
                try:
                    instance = plugin_info.create_instance()
                    plugin_info.initialized = instance.initialize()
                    
                    if plugin_info.initialized:
                        # Update language mapping
                        for lang in instance.capability.languages:
                            if lang not in self._language_mapping:
                                self._language_mapping[lang] = []
                            self._language_mapping[lang].append(name)
                        
                        self._plugins[name] = plugin_info
                        logger.info(f"Plugin {name} registered successfully for languages: {instance.capability.languages}")
                        return True
                    else:
                        logger.error(f"Plugin {name} initialization failed")
                        return False
                        
                except Exception as e:
                    plugin_info.load_error = str(e)
                    logger.error(f"Plugin {name} registration failed: {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to register plugin {name}: {e}")
                return False
    
    def discover_plugins(self, plugin_dirs: Optional[List[str]] = None) -> int:
        """
        Discover and load plugins from directories
        
        Args:
            plugin_dirs: List of directories to search for plugins
            
        Returns:
            Number of plugins successfully loaded
        """
        if plugin_dirs is None:
            plugin_dirs = self._get_default_plugin_dirs()
        
        loaded_count = 0
        
        for plugin_dir in plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue
                
            logger.debug(f"Discovering plugins in {plugin_dir}")
            loaded_count += self._load_plugins_from_directory(plugin_dir)
        
        logger.info(f"Plugin discovery complete: {loaded_count} plugins loaded")
        return loaded_count
    
    def _get_default_plugin_dirs(self) -> List[str]:
        """Get default plugin directories"""
        current_dir = Path(__file__).parent
        return [
            str(current_dir / "language_plugins"),  # Built-in plugins
            str(current_dir / "../../plugins"),     # User plugins
        ]
    
    def _load_plugins_from_directory(self, plugin_dir: str) -> int:
        """Load plugins from a specific directory"""
        loaded_count = 0
        plugin_path = Path(plugin_dir)
        
        if not plugin_path.exists():
            return 0
        
        # Look for Python files
        for py_file in plugin_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
                
            try:
                plugin_name = py_file.stem
                if self._load_plugin_from_file(str(py_file), plugin_name):
                    loaded_count += 1
            except Exception as e:
                logger.warning(f"Failed to load plugin from {py_file}: {e}")
        
        return loaded_count
    
    def _load_plugin_from_file(self, file_path: str, plugin_name: str) -> bool:
        """Load plugin from Python file"""
        try:
            # Avoid loading the same module multiple times
            module_name = f"oss_audit_plugin_{plugin_name}"
            if module_name in self._loaded_modules:
                return False
            
            # Load module from file
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                logger.error(f"Could not load spec for {file_path}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules to support relative imports
            sys.modules[module_name] = module
            self._loaded_modules.add(module_name)
            
            # Execute module
            spec.loader.exec_module(module)
            
            # Look for plugin classes
            found_plugins = 0
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # Check if it's a LanguagePlugin subclass (but not the base class)
                if (isinstance(attr, type) and 
                    issubclass(attr, LanguagePlugin) and 
                    attr != LanguagePlugin):
                    
                    # Use class name as plugin name if not specified
                    final_plugin_name = plugin_name if plugin_name != attr.__name__.lower() else attr.__name__
                    
                    if self.register_plugin(final_plugin_name, attr):
                        found_plugins += 1
            
            return found_plugins > 0
            
        except Exception as e:
            logger.error(f"Error loading plugin from {file_path}: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def get_plugin(self, name: str) -> Optional[LanguagePlugin]:
        """Get plugin instance by name"""
        with self._lock:
            plugin_info = self._plugins.get(name)
            if plugin_info and plugin_info.initialized:
                return plugin_info.instance
            return None
    
    def get_plugins_for_language(self, language: str) -> List[LanguagePlugin]:
        """Get all plugins that support a specific language"""
        with self._lock:
            plugin_names = self._language_mapping.get(language, [])
            plugins = []
            
            for name in plugin_names:
                plugin = self.get_plugin(name)
                if plugin:
                    plugins.append(plugin)
            
            # Sort by priority
            plugins.sort(key=lambda p: p.priority.value)
            return plugins
    
    def get_plugins_for_project(self, project_info: ProjectInfo) -> List[LanguagePlugin]:
        """Get all plugins that can analyze the given project"""
        with self._lock:
            applicable_plugins = []
            
            for plugin_info in self._plugins.values():
                if plugin_info.initialized and plugin_info.instance:
                    if plugin_info.instance.can_analyze(project_info):
                        applicable_plugins.append(plugin_info.instance)
            
            # Sort by priority (critical first)
            applicable_plugins.sort(key=lambda p: p.priority.value)
            return applicable_plugins
    
    def execute_plugins_safely(self, plugins: List[LanguagePlugin], 
                             project_path: str, project_info: ProjectInfo,
                             available_tools: List) -> Dict[str, PluginResult]:
        """
        Execute plugins with error isolation
        
        Args:
            plugins: List of plugins to execute
            project_path: Project path
            project_info: Project information
            available_tools: Available analysis tools
            
        Returns:
            Plugin execution results
        """
        results = {}
        
        for plugin in plugins:
            try:
                logger.info(f"Executing plugin: {plugin.name}")
                result = plugin.analyze(project_path, project_info, available_tools)
                results[plugin.name] = result
                
                if result.success:
                    logger.debug(f"Plugin {plugin.name} completed successfully")
                else:
                    logger.warning(f"Plugin {plugin.name} completed with errors")
                    
            except Exception as e:
                # Create error result for failed plugin
                error_result = PluginResult(
                    plugin_name=plugin.name,
                    language=list(plugin.capability.languages)[0],
                    success=False
                )
                error_result.add_error(PluginError(
                    plugin_name=plugin.name,
                    error_type="ExecutionError",
                    message=str(e),
                    recoverable=False
                ))
                results[plugin.name] = error_result
                
                logger.error(f"Plugin {plugin.name} execution failed: {e}")
                logger.debug(traceback.format_exc())
        
        return results
    
    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a plugin"""
        with self._lock:
            plugin_info = self._plugins.get(name)
            if not plugin_info:
                return None
                
            info = {
                'name': plugin_info.name,
                'initialized': plugin_info.initialized,
                'load_error': plugin_info.load_error,
                'class_name': plugin_info.plugin_class.__name__
            }
            
            if plugin_info.instance:
                info.update({
                    'languages': list(plugin_info.instance.capability.languages),
                    'priority': plugin_info.instance.priority.name,
                    'categories': [cat.value for cat in plugin_info.instance.capability.categories]
                })
            
            return info
    
    def list_plugins(self) -> Dict[str, Dict[str, Any]]:
        """List all registered plugins with their info"""
        with self._lock:
            return {name: self.get_plugin_info(name) for name in self._plugins.keys()}
    
    def cleanup(self):
        """Cleanup all plugins"""
        with self._lock:
            for plugin_info in self._plugins.values():
                if plugin_info.instance:
                    try:
                        plugin_info.instance.cleanup()
                    except Exception as e:
                        logger.warning(f"Error cleaning up plugin {plugin_info.name}: {e}")
            
            self._plugins.clear()
            self._language_mapping.clear()
            
            # Remove loaded modules
            for module_name in self._loaded_modules:
                if module_name in sys.modules:
                    del sys.modules[module_name]
            self._loaded_modules.clear()
    
    def reload_plugin(self, name: str) -> bool:
        """Reload a specific plugin"""
        with self._lock:
            # Remove existing plugin
            if name in self._plugins:
                plugin_info = self._plugins[name]
                if plugin_info.instance:
                    plugin_info.instance.cleanup()
                
                # Remove from language mapping
                for lang, plugin_names in self._language_mapping.items():
                    if name in plugin_names:
                        plugin_names.remove(name)
                
                del self._plugins[name]
            
            # Rediscover plugins
            return self.discover_plugins() > 0


# Global plugin registry instance
_plugin_registry: Optional[PluginRegistry] = None
_registry_lock = threading.Lock()


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance"""
    global _plugin_registry
    
    with _registry_lock:
        if _plugin_registry is None:
            _plugin_registry = PluginRegistry()
            # Auto-discover plugins
            _plugin_registry.discover_plugins()
        
        return _plugin_registry


def reset_plugin_registry():
    """Reset the global plugin registry (mainly for testing)"""
    global _plugin_registry
    
    with _registry_lock:
        if _plugin_registry:
            _plugin_registry.cleanup()
        _plugin_registry = None