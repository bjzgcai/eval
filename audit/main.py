#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSS Audit 2.0 - 开源软件成熟度评估工具

主入口脚本（开发和直接运行使用）
提供命令行接口，支持零配置智能分析。

使用方法:
  python main.py <项目路径> [输出目录]
  
示例:
  python main.py ./my-project
  python main.py ./my-project ./reports
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from oss_audit.core.audit_runner import main

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
