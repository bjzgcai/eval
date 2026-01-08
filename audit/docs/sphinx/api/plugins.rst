插件系统 (oss_audit.plugins)
=============================

插件系统为OSS Audit 2.0提供了灵活的扩展能力，支持自定义工具、语言检测器、结果处理器等。

插件基类和接口
--------------

.. automodule:: oss_audit.plugins.base
   :members:
   :undoc-members:
   :show-inheritance:

插件注册表
----------

.. automodule:: oss_audit.plugins.registry
   :members:
   :undoc-members:
   :show-inheritance:

结果验证器
----------

.. automodule:: oss_audit.plugins.result_validator
   :members:
   :undoc-members:
   :show-inheritance:

创建自定义插件
--------------

工具插件开发
~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.plugins.base import BaseToolPlugin
   from oss_audit.core.tool_registry import Tool
   from typing import Dict, List, Any
   import subprocess
   import json
   
   class ESLintPlugin(BaseToolPlugin):
       """ESLint工具插件示例"""
       
       def get_name(self) -> str:
           return "eslint"
       
       def get_version(self) -> str:
           return "1.0.0"
       
       def get_description(self) -> str:
           return "ESLint JavaScript代码质量检查工具"
       
       def get_supported_languages(self) -> List[str]:
           return ["javascript", "typescript"]
       
       def is_available(self) -> bool:
           """检查ESLint是否可用"""
           try:
               result = subprocess.run(
                   ["eslint", "--version"],
                   capture_output=True,
                   text=True,
                   timeout=10
               )
               return result.returncode == 0
           except (subprocess.TimeoutExpired, FileNotFoundError):
               return False
       
       def execute(self, project_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
           """执行ESLint分析"""
           try:
               # 构建ESLint命令
               cmd = [
                   "eslint",
                   project_path,
                   "--format=json",
                   "--no-error-on-unmatched-pattern"
               ]
               
               # 添加配置参数
               if config.get("config_file"):
                   cmd.extend(["-c", config["config_file"]])
               
               if config.get("ignore_pattern"):
                   cmd.extend(["--ignore-pattern", config["ignore_pattern"]])
               
               # 执行命令
               result = subprocess.run(
                   cmd,
                   capture_output=True,
                   text=True,
                   timeout=config.get("timeout", 300)
               )
               
               # 解析结果
               if result.stdout:
                   eslint_results = json.loads(result.stdout)
                   return self._parse_eslint_output(eslint_results)
               else:
                   return {
                       "success": True,
                       "score": 100,
                       "issues_found": [],
                       "message": "No issues found"
                   }
                   
           except subprocess.TimeoutExpired:
               return {
                   "success": False,
                   "error": "ESLint execution timeout",
                   "score": 0
               }
           except Exception as e:
               return {
                   "success": False,
                   "error": f"ESLint execution failed: {str(e)}",
                   "score": 0
               }
       
       def _parse_eslint_output(self, eslint_results: List[Dict]) -> Dict[str, Any]:
           """解析ESLint输出"""
           issues = []
           total_errors = 0
           total_warnings = 0
           
           for file_result in eslint_results:
               file_path = file_result.get("filePath", "")
               
               for message in file_result.get("messages", []):
                   severity = "high" if message["severity"] == 2 else "medium"
                   
                   issues.append({
                       "file": file_path,
                       "line": message.get("line"),
                       "column": message.get("column"),
                       "rule": message.get("ruleId"),
                       "message": message.get("message"),
                       "severity": severity
                   })
                   
                   if message["severity"] == 2:
                       total_errors += 1
                   else:
                       total_warnings += 1
           
           # 计算分数 (100分制)
           score = max(0, 100 - (total_errors * 5) - (total_warnings * 2))
           
           return {
               "success": True,
               "score": score,
               "issues_found": issues,
               "statistics": {
                   "total_files": len(eslint_results),
                   "total_errors": total_errors,
                   "total_warnings": total_warnings
               }
           }

语言检测插件
~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.plugins.base import BaseLanguageDetector
   import pathlib
   from typing import Dict, List
   
   class RustDetector(BaseLanguageDetector):
       """Rust语言检测插件"""
       
       def get_name(self) -> str:
           return "rust_detector"
       
       def get_supported_extensions(self) -> List[str]:
           return [".rs", ".toml"]
       
       def get_build_files(self) -> List[str]:
           return ["Cargo.toml", "Cargo.lock"]
       
       def detect_language(self, project_path: str) -> Dict[str, Any]:
           """检测Rust项目"""
           project_root = pathlib.Path(project_path)
           
           # 查找Cargo.toml
           cargo_toml = project_root / "Cargo.toml"
           if not cargo_toml.exists():
               return {"confidence": 0.0, "evidence": []}
           
           evidence = ["Found Cargo.toml"]
           confidence = 0.8
           
           # 查找src目录和main.rs
           src_dir = project_root / "src"
           if src_dir.exists():
               evidence.append("Found src/ directory")
               confidence += 0.1
               
               if (src_dir / "main.rs").exists():
                   evidence.append("Found src/main.rs")
                   confidence += 0.05
               
               if (src_dir / "lib.rs").exists():
                   evidence.append("Found src/lib.rs")
                   confidence += 0.05
           
           # 统计Rust文件
           rust_files = list(project_root.rglob("*.rs"))
           if rust_files:
               evidence.append(f"Found {len(rust_files)} .rs files")
               confidence = min(1.0, confidence + len(rust_files) * 0.01)
           
           return {
               "confidence": min(1.0, confidence),
               "evidence": evidence,
               "files_found": len(rust_files),
               "build_system": "cargo"
           }

结果后处理插件
~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.plugins.base import BaseResultProcessor
   from typing import Dict, Any, List
   import statistics
   
   class StatisticalProcessor(BaseResultProcessor):
       """统计分析结果处理器"""
       
       def get_name(self) -> str:
           return "statistical_processor"
       
       def process(self, results: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
           """对审计结果进行统计分析"""
           processed_results = results.copy()
           
           # 收集所有工具的分数
           scores = []
           issue_counts = []
           execution_times = []
           
           for tool_name, tool_result in results.items():
               if isinstance(tool_result, dict):
                   if "score" in tool_result:
                       scores.append(tool_result["score"])
                   
                   if "issues_found" in tool_result:
                       issue_counts.append(len(tool_result["issues_found"]))
                   
                   if "execution_time" in tool_result:
                       execution_times.append(tool_result["execution_time"])
           
           # 计算统计指标
           stats = {}
           
           if scores:
               stats["score_statistics"] = {
                   "mean": statistics.mean(scores),
                   "median": statistics.median(scores),
                   "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0,
                   "min": min(scores),
                   "max": max(scores),
                   "count": len(scores)
               }
           
           if issue_counts:
               stats["issue_statistics"] = {
                   "total_issues": sum(issue_counts),
                   "mean_issues_per_tool": statistics.mean(issue_counts),
                   "max_issues_per_tool": max(issue_counts)
               }
           
           if execution_times:
               stats["performance_statistics"] = {
                   "total_time": sum(execution_times),
                   "mean_time": statistics.mean(execution_times),
                   "slowest_tool": max(execution_times)
               }
           
           processed_results["_statistics"] = stats
           
           # 添加质量等级评估
           if scores:
               mean_score = statistics.mean(scores)
               if mean_score >= 90:
                   quality_level = "Excellent"
               elif mean_score >= 80:
                   quality_level = "Good"
               elif mean_score >= 70:
                   quality_level = "Fair"
               elif mean_score >= 60:
                   quality_level = "Poor"
               else:
                   quality_level = "Critical"
               
               processed_results["_quality_assessment"] = {
                   "level": quality_level,
                   "score": mean_score,
                   "recommendation": self._get_recommendation(quality_level)
               }
           
           return processed_results
       
       def _get_recommendation(self, quality_level: str) -> str:
           """根据质量等级提供建议"""
           recommendations = {
               "Excellent": "项目质量优秀，建议保持当前标准",
               "Good": "项目质量良好，可以考虑小幅改进",
               "Fair": "项目质量一般，建议重点关注主要问题",
               "Poor": "项目质量较差，需要系统性改进",
               "Critical": "项目质量严重不足，需要立即采取行动"
           }
           return recommendations.get(quality_level, "需要进一步评估")

插件注册和管理
--------------

注册插件
~~~~~~~~

.. code-block:: python

   from oss_audit.plugins.registry import PluginRegistry
   
   # 创建插件注册表
   registry = PluginRegistry()
   
   # 注册工具插件
   eslint_plugin = ESLintPlugin()
   registry.register_tool_plugin(eslint_plugin)
   
   # 注册语言检测器
   rust_detector = RustDetector()
   registry.register_language_detector(rust_detector)
   
   # 注册结果处理器
   stats_processor = StatisticalProcessor()
   registry.register_result_processor(stats_processor)
   
   print(f"已注册 {registry.get_plugin_count()} 个插件")

自动发现插件
~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.plugins.discovery import PluginDiscovery
   
   # 创建插件发现器
   discovery = PluginDiscovery()
   
   # 从指定目录发现插件
   plugins = discovery.discover_plugins("./plugins")
   
   for plugin in plugins:
       print(f"发现插件: {plugin.get_name()} v{plugin.get_version()}")
       
       # 自动注册
       if plugin.is_available():
           registry.register_plugin(plugin)
           print(f"  -> 已注册")
       else:
           print(f"  -> 不可用，跳过注册")

插件配置
~~~~~~~~

.. code-block:: python

   from oss_audit.plugins.config import PluginConfig
   
   # 创建插件配置
   config = PluginConfig()
   
   # 配置特定插件
   config.configure_plugin("eslint", {
       "config_file": ".eslintrc.json",
       "ignore_pattern": "node_modules/*",
       "timeout": 120,
       "max_warnings": 50
   })
   
   # 启用/禁用插件
   config.enable_plugin("rust_detector")
   config.disable_plugin("old_plugin")
   
   # 获取插件配置
   eslint_config = config.get_plugin_config("eslint")
   print(f"ESLint配置: {eslint_config}")

插件生命周期管理
~~~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.plugins.manager import PluginManager
   
   # 创建插件管理器
   manager = PluginManager()
   
   # 加载所有插件
   manager.load_all_plugins()
   
   # 验证插件兼容性
   compatibility_report = manager.check_compatibility()
   
   for plugin_name, status in compatibility_report.items():
       if status["compatible"]:
           print(f"✓ {plugin_name}: 兼容")
       else:
           print(f"✗ {plugin_name}: {status['reason']}")
   
   # 更新插件
   manager.update_plugin("eslint_plugin", "2.0.0")
   
   # 卸载插件
   manager.uninstall_plugin("unused_plugin")

高级插件开发
------------

异步工具插件
~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from oss_audit.plugins.base import BaseAsyncToolPlugin
   
   class AsyncSecurityScannerPlugin(BaseAsyncToolPlugin):
       """异步安全扫描插件"""
       
       async def execute_async(self, project_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
           """异步执行安全扫描"""
           tasks = []
           
           # 并发执行多个扫描任务
           tasks.append(self._scan_dependencies(project_path))
           tasks.append(self._scan_source_code(project_path))
           tasks.append(self._scan_configuration(project_path))
           
           results = await asyncio.gather(*tasks, return_exceptions=True)
           
           # 合并结果
           combined_results = {
               "success": True,
               "issues_found": [],
               "score": 100
           }
           
           for result in results:
               if isinstance(result, dict) and result.get("issues_found"):
                   combined_results["issues_found"].extend(result["issues_found"])
           
           # 重新计算分数
           issue_count = len(combined_results["issues_found"])
           combined_results["score"] = max(0, 100 - issue_count * 3)
           
           return combined_results
       
       async def _scan_dependencies(self, project_path: str) -> Dict[str, Any]:
           """扫描依赖安全问题"""
           # 异步扫描逻辑
           await asyncio.sleep(1)  # 模拟扫描时间
           return {"issues_found": [{"type": "dependency", "severity": "medium"}]}
       
       async def _scan_source_code(self, project_path: str) -> Dict[str, Any]:
           """扫描源代码安全问题"""
           await asyncio.sleep(2)
           return {"issues_found": [{"type": "code", "severity": "high"}]}
       
       async def _scan_configuration(self, project_path: str) -> Dict[str, Any]:
           """扫描配置安全问题"""  
           await asyncio.sleep(0.5)
           return {"issues_found": []}

插件测试框架
~~~~~~~~~~~~

.. code-block:: python

   import unittest
   from oss_audit.plugins.testing import PluginTestCase
   
   class TestESLintPlugin(PluginTestCase):
       """ESLint插件测试用例"""
       
       def setUp(self):
           """设置测试环境"""
           super().setUp()
           self.plugin = ESLintPlugin()
           self.test_project = self.create_test_project({
               "package.json": '{"name": "test", "version": "1.0.0"}',
               "index.js": "console.log('hello world');"
           })
       
       def test_plugin_availability(self):
           """测试插件可用性"""
           # 模拟ESLint可用
           with self.mock_command_available("eslint"):
               self.assertTrue(self.plugin.is_available())
       
       def test_plugin_execution(self):
           """测试插件执行"""
           # 模拟ESLint输出
           mock_output = [
               {
                   "filePath": "index.js",
                   "messages": [
                       {
                           "ruleId": "semi",
                           "severity": 2,
                           "message": "Missing semicolon",
                           "line": 1,
                           "column": 26
                       }
                   ]
               }
           ]
           
           with self.mock_subprocess_output(mock_output):
               result = self.plugin.execute(self.test_project.path, {})
               
               self.assertTrue(result["success"])
               self.assertEqual(len(result["issues_found"]), 1)
               self.assertLess(result["score"], 100)
       
       def tearDown(self):
           """清理测试环境"""
           self.cleanup_test_project()
           super().tearDown()

if __name__ == "__main__":
    unittest.main()