"""
OSS Audit - 开源软件成熟度评估工具

一个用于评估开源项目成熟度的综合工具，支持14个维度的全面分析。
"""

__version__ = "1.0.0"
__author__ = "OSS Audit Team"
__email__ = "team@oss-audit.org"

from .core import main

__all__ = ["main"]
