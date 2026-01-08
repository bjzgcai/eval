#!/usr/bin/env python3
"""
Plugin System for OSS Audit 2.0
Provides language-specific analysis capabilities through a plugin architecture
"""

from .base import LanguagePlugin, PluginResult, PluginError
from .registry import PluginRegistry, get_plugin_registry, reset_plugin_registry
from .result_validator import PluginResultValidator, ResultStandardizer, validate_and_standardize_result

__all__ = [
    'LanguagePlugin',
    'PluginResult', 
    'PluginError',
    'PluginRegistry',
    'get_plugin_registry',
    'reset_plugin_registry',
    'PluginResultValidator',
    'ResultStandardizer',
    'validate_and_standardize_result'
]